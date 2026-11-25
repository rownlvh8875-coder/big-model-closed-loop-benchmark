"""Explicit two-bend sidewalk ordering for the SDK3 renderer candidate."""

from contextlib import contextmanager

from .curved_lane_scenarios import SCENARIOS


BIN_NAME = 'sdk3-sidewalk-order-candidate'
BIN_SORT = 19


def _active_bins(manager):
    return {
        manager.get_bin_name(index): (manager.get_bin_sort(index), manager.get_bin_type(index))
        for index in range(manager.get_num_bins()) if manager.get_bin_active(index)
    }


def _index_digest(primitive):
    value = 14695981039346656037
    for index in primitive.get_vertex_list():
        for byte in int(index).to_bytes(4, 'little'):
            value = ((value ^ byte) * 1099511628211) & ((1 << 64) - 1)
    return f'{value:016x}'


def _sidewalk(block, geom_type, combiner_type, attrib_type):
    path = block.sidewalk_node_path
    if path.is_empty() or not isinstance(path.node(), combiner_type):
        raise ValueError('expected the native sidewalk combiner')
    root = path.node().get_internal_scene()
    if root.is_empty():
        raise ValueError('the native sidewalk combiner has no internal scene')
    paths = {int(node.node().this): node for node in root.find_all_matches('**/+GeomNode')}
    if isinstance(root.node(), geom_type):
        paths[int(root.node().this)] = root
    if len(paths) != 1:
        raise ValueError('expected one combined sidewalk GeomNode per C block')
    internal, = paths.values()
    node = internal.node()
    if node.get_num_geoms() != 1:
        raise ValueError('expected one combined sidewalk geometry per C block')
    state = node.get_geom_state(0)
    if state.has_attrib(attrib_type) or path.get_net_state().has_attrib(attrib_type):
        raise ValueError('pre-existing sidewalk bin would override the proposed ordering')
    geometry = node.get_geom(0)
    if geometry.get_num_primitives() != 1:
        raise ValueError('expected one combined sidewalk index array')
    primitive = geometry.get_primitive(0)
    count = primitive.get_num_vertices()
    if not primitive.is_indexed() or not 0 < count <= 8192:
        raise ValueError('unexpected combined sidewalk index array')
    return node, state, dict(path=str(path), internal=str(internal), geom_index=0,
                             count=count, index_fingerprint=_index_digest(primitive))


@contextmanager
def ordered_sidewalks(provider, scenario):
    """Apply a fixed bin to precisely the two forward curve sidewalks."""
    from panda3d.core import CullBinAttrib, CullBinManager, GeomNode, RigidBodyCombiner

    blocks = [block for block in provider.env.current_map.blocks if block.ID == 'C']
    directions = tuple(int(block.get_config()['dir']) for block in blocks)
    if len(blocks) != 2 or directions != SCENARIOS[scenario].expected_curve_directions:
        raise ValueError('two prescribed native C blocks required')
    targets = [_sidewalk(block, GeomNode, RigidBodyCombiner, CullBinAttrib) for block in blocks]
    if len({row['path'] for _, _, row in targets}) != 2:
        raise ValueError('the two sidewalk paths must be independent')

    manager = CullBinManager.get_global_ptr()
    before = _active_bins(manager)
    if (before.get('background') != (10, manager.BT_fixed)
            or before.get('opaque') != (20, manager.BT_state_sorted)
            or any(sort == BIN_SORT for sort, _ in before.values())
            or manager.find_bin(BIN_NAME) >= 0):
        raise ValueError('unexpected active bin configuration for the SDK3 candidate')
    bin_index = manager.add_bin(BIN_NAME, manager.BT_fixed, BIN_SORT)
    if bin_index < 0:
        raise RuntimeError('failed to add the registered sidewalk bin')

    changed = []
    receipt = dict(bin=BIN_NAME, sort=BIN_SORT, directions=directions, targets=[],
                   state_restored=False, original_active_bins_restored=False)
    try:
        for priority, (node, prior, entry) in enumerate(targets):
            state = prior.add_attrib(CullBinAttrib.make(BIN_NAME, priority), 100)
            if state.remove_attrib(CullBinAttrib) != prior:
                raise ValueError('the sidewalk state changed outside CullBinAttrib')
            changed.append((node, prior, state))
            node.set_geom_state(0, state)
            receipt['targets'].append(dict(**entry, priority=priority))
        yield receipt
        if any(node.get_geom_state(0) != state for node, _, state in changed):
            raise RuntimeError('the proposed sidewalk state was replaced during capture')
    finally:
        for node, original, _ in changed:
            node.set_geom_state(0, original)
        receipt['state_restored'] = all(node.get_geom_state(0) == old for node, old, _ in changed)
        # Panda 1.10.13 cannot invalidate all cached bin indexes on remove_bin.
        manager.set_bin_active(bin_index, False)
        receipt['original_active_bins_restored'] = _active_bins(manager) == before
        if not receipt['state_restored'] or not receipt['original_active_bins_restored']:
            raise RuntimeError('failed to restore the two sidewalk states and active bins')

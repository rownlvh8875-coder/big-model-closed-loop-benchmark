"""Verify declared native NV12 storage and optional offline tensor references."""

import json
from pathlib import Path

from .offline_camera_validation import local_bytes, need, sha, vector

PROTOCOL = 'offline-sensor-nv12-v1'
ROLES = ('road', 'wide')
PLANES = ('Y00', 'Y10', 'Y01', 'Y11', 'U', 'V')
MAX_METADATA_BYTES = 128 * 1024
MAX_FRAME_BYTES = 128 * 1024**2
TENSOR_SHAPE = (2, 6, 128, 256)
TENSOR_BYTES = 2 * 6 * 128 * 256


def decode_nv12(payload, layout):
    """Return uint8 views of active Y, U, V samples with no color conversion."""
    import numpy as np

    width, height = (layout.get(key) for key in ('width', 'height'))
    need(all(type(n) is int and n > 0 and n % 2 == 0 for n in (width, height)),
         'positive even NV12 dimensions required')
    y_stride, uv_stride = (layout.get(key) for key in ('y_stride', 'uv_stride'))
    need(all(type(n) is int and n >= width for n in (y_stride, uv_stride)), 'invalid NV12 row stride')
    y_offset, uv_offset = (layout.get(key) for key in ('y_offset', 'uv_offset'))
    need(all(type(n) is int and n >= 0 for n in (y_offset, uv_offset)), 'invalid NV12 plane offset')
    need(layout.get('chroma_order') == 'UV', 'NV12 requires interleaved UV order')
    y_end = y_offset + (height - 1) * y_stride + width
    uv_end = uv_offset + (height // 2 - 1) * uv_stride + width
    need(y_end <= uv_offset, 'NV12 active planes overlap or are out of order')
    need(uv_end <= len(payload), 'NV12 payload ends before the last active sample')
    y = np.ndarray((height, width), dtype=np.uint8, buffer=payload, offset=y_offset, strides=(y_stride, 1))
    uv = np.ndarray((height // 2, width), dtype=np.uint8, buffer=payload,
                    offset=uv_offset, strides=(uv_stride, 1))
    return y, uv[:, ::2], uv[:, 1::2]


def compare_reference(packed, raw):
    import numpy as np

    need(len(raw) == TENSOR_BYTES, 'reference must contain exactly one packed road/wide tensor')
    reference = np.frombuffer(raw, dtype=np.uint8).reshape(TENSOR_SHAPE)
    mask = packed != reference
    count = int(np.count_nonzero(mask))
    first = None
    if count:
        camera, plane, row, column = map(int, np.unravel_index(np.argmax(mask), TENSOR_SHAPE))
        first = dict(camera=ROLES[camera], plane=PLANES[plane], row=row, column=column,
                     actual=int(packed[camera, plane, row, column]),
                     reference=int(reference[camera, plane, row, column]))
    return dict(reference_sha256=sha(raw), exact=count == 0, changed_bytes=count,
                changed_bytes_by_plane=np.count_nonzero(mask, axis=(2, 3)).tolist(), first_difference=first)


def capture_frame(root, row, layout):
    need(isinstance(row, dict), 'NV12 frame record required')
    frame_id, timestamp = row.get('frame_id'), row.get('timestamp_ns')
    need(all(type(n) is int and n >= 0 for n in (frame_id, timestamp)),
         'nonnegative frame ID and source timestamp required')
    size = row.get('nbytes')
    need(type(size) is int and 0 < size <= MAX_FRAME_BYTES, 'bounded NV12 buffer length required')
    payload = local_bytes(root, row, size)
    need(len(payload) == size, 'NV12 payload length differs from the declared extent')
    planes = decode_nv12(payload, layout)
    return planes, dict(frame_id=frame_id, timestamp_ns=timestamp, nbytes=size, source_sha256=row['sha256'],
                        active_plane_sha256={label: sha(plane.tobytes()) for label, plane in zip('YUV', planes)})


def verify_sensor_capture(manifest):
    result = dict(protocol=PROTOCOL, sensor_provenance_authenticated=False, physical_optics_validated=False,
                  production_warp_validated=False, official_model_processes=0, official_inferences=0)
    if manifest is None or not Path(manifest).is_file():
        return dict(result, status='BLOCKED', missing=['NATIVE_SENSOR_NV12_MANIFEST_REQUIRED'])

    path = Path(manifest).resolve()
    root = path.parent
    with path.open('rb') as stream:
        manifest_bytes = stream.read(MAX_METADATA_BYTES + 1)
    need(len(manifest_bytes) <= MAX_METADATA_BYTES, 'bounded sensor manifest required')
    document = json.loads(manifest_bytes)
    need(isinstance(document, dict) and document.get('schema') == PROTOCOL
         and document.get('capture_origin') == 'SENSOR_NATIVE_NV12', 'declared sensor-native NV12 manifest required')
    history = local_bytes(root, document['capture_history'], MAX_METADATA_BYTES)
    cameras = document.get('cameras')
    need(isinstance(cameras, dict) and set(cameras) == set(ROLES), 'road and wide camera metadata required')
    camera_details = {}
    for role, layout in cameras.items():
        need(isinstance(layout, dict) and all(isinstance(layout.get(key), str) and layout[key].strip()
             for key in ('sensor_model', 'color_matrix')), 'sensor model and declared color matrix required')
        need(layout.get('color_range') in ('limited', 'full'), 'declared limited or full NV12 range required')
        calibration = local_bytes(root, layout['calibration_and_mount'], MAX_METADATA_BYTES)
        camera_details[role] = {key: layout[key] for key in ('sensor_model', 'width', 'height', 'y_stride',
                                'uv_stride', 'y_offset', 'uv_offset', 'chroma_order', 'color_range', 'color_matrix')}
        camera_details[role]['calibration_and_mount_sha256'] = sha(calibration)

    warp = document.get('warp')
    if warp is not None:
        import numpy as np
        from .preprocess_experiment import sample_six

        need(isinstance(warp, dict) and set(warp) == {*ROLES, 'source'}, 'road/wide warp and origin record required')
        for role in ROLES:
            matrix = warp[role]
            need(isinstance(matrix, list) and len(matrix) == 3 and all(vector(row, 3) for row in matrix),
                 'finite destination-to-source 3×3 warp required')
        result['warp_source_sha256'] = sha(local_bytes(root, warp['source'], MAX_METADATA_BYTES))
        result['warp_sampler'] = 'benchmark_projective_nearest_even'

    pairs = document.get('pairs')
    need(isinstance(pairs, list) and bool(pairs), 'at least one declared road/wide pair required')
    results = []
    seen = {role: set() for role in ROLES}
    for pair in pairs:
        need(isinstance(pair, dict), 'road/wide pair record required')
        reference = pair.get('reference_tensor')
        need(reference is None or warp is not None, 'reference requires an explicit offline warp')
        frame_records, tensors = {}, []
        for role in ROLES:
            planes, frame = capture_frame(root, pair[role], cameras[role])
            key = frame['frame_id'], frame['timestamp_ns']
            need(key not in seen[role], 'duplicate camera frame ID and timestamp')
            seen[role].add(key)
            frame_records[role] = frame
            if warp is not None:
                tensors.append(sample_six(*planes, warp[role]))
        row = dict(frames=frame_records, wide_minus_road_ns=frame_records['wide']['timestamp_ns']
                   - frame_records['road']['timestamp_ns'], reference_comparison=None)
        if warp is not None:
            packed = np.stack(tensors)
            need(packed.shape == TENSOR_SHAPE and packed.dtype == np.uint8, 'benchmark tensor contract mismatch')
            row['warped_tensor_sha256'] = sha(packed.tobytes())
            if reference is not None:
                row['reference_comparison'] = compare_reference(packed, local_bytes(root, reference, TENSOR_BYTES))
        results.append(row)
    comparisons = [row['reference_comparison'] for row in results if row['reference_comparison'] is not None]
    status = 'LAYOUT_VERIFIED' if warp is None else 'WARP_RECONSTRUCTED'
    if comparisons:
        if any(not comp['exact'] for comp in comparisons):
            status = 'REFERENCE_MISMATCH'
        else:
            status = 'REFERENCE_MATCH' if len(comparisons) == len(results) else 'REFERENCE_PARTIAL'
    return dict(result, status=status, manifest_sha256=sha(manifest_bytes), capture_history_sha256=sha(history),
                cameras=camera_details, pairs=results, referenced_pairs=len(comparisons),
                scope='declared capture layout and optional benchmark warp; no production ISP or optical verdict')

"""Pure projection of package descriptors through explicitly authenticated /usr aliases.

The caller authenticates alias descriptors and bytes. This helper never follows
host paths, merges unequal payloads, or establishes installed/runtime readiness.
"""

_ALLOWED = {'bin': 'usr/bin', 'sbin': 'usr/sbin', 'lib': 'usr/lib', 'lib64': 'usr/lib64'}


def _need(condition):
    if not condition:
        raise ValueError('INVALID_IMAGE_INPUT_PATH')


def _path(value):
    _need(type(value) is str)
    try:
        encoded = value.encode('utf-8')
    except UnicodeError:
        raise ValueError('INVALID_IMAGE_INPUT_PATH') from None
    _need(0 < len(encoded) <= 4096)
    _need(not value.startswith('/') and '\\' not in value and len(value.split('/')) <= 64)
    _need(all(part not in ('', '.', '..') for part in value.split('/')))
    _need(all(ord(char) >= 32 and ord(char) != 127 for char in value))
    return value


def project_package_member(row: dict, aliases: dict[str, str]) -> dict | None:
    """Return a descriptor copy at its canonical container path, or an alias witness."""
    _need(type(row) is dict and type(aliases) is dict)
    _need(all(type(key) is str and key in _ALLOWED and target == _ALLOWED[key]
              for key, target in aliases.items()))
    path = _path(row.get('path'))
    kind = row.get('kind')
    _need(kind in ('file', 'directory', 'symlink', 'hardlink'))
    if path in aliases:
        if kind == 'symlink':
            _need(row.get('target') == aliases[path])
            _need(row.get('normalized_target', aliases[path]) == aliases[path])
            return None
        _need(kind == 'directory')

    def project(value):
        value = _path(value)
        first, separator, rest = value.partition('/')
        return aliases.get(first, first) + (separator + rest if separator else '')

    result = {**row, 'path': project(path)}
    if 'normalized_target' in row:
        result['normalized_target'] = project(row['normalized_target'])
    return result

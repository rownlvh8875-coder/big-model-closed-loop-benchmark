"""Authenticate original vendored RECORD payload; exempt only rewritten top-level metadata."""
import hashlib
import json
from pathlib import Path
import stat
import zipfile


def _need(ok):
    if not ok:raise ValueError('TOOL_PAYLOAD_MISMATCH')


def _safe(path):
    return type(path) is str and path and not path.startswith('/') and '\\' not in path and all(p not in ('','.','..') for p in path.split('/'))


def verify_tools(site,wheels,*,snapshotter,magic):
    """Use the unchanged bounded snapshotter; never import wheel/installed code."""
    try:
        _need(type(wheels) in (list,tuple) and 1<=len(wheels)<=4 and type(magic) is bytes and len(magic)==4)
        expected,distributions,seen={},set(),set()
        for path in wheels:
            with zipfile.ZipFile(path) as archive:
                for entry in archive.infolist():
                    name=entry.filename
                    _need(_safe(name) and not entry.is_dir() and name not in seen and len(seen)<20000
                          and entry.file_size<=4194304 and stat.S_IFMT(entry.external_attr>>16) in (0,stat.S_IFREG))
                    seen.add(name)
                    first=name.split('/')[0]
                    top_info=first.endswith('.dist-info')
                    if top_info:distributions.add(first)
                    # Pip rewrites only the installed distribution's own RECORD.
                    # Vendored RECORD paths remain original authenticated bytes.
                    if top_info and name==first+'/RECORD':continue
                    expected[name]=hashlib.sha256(archive.read(entry)).hexdigest()
        rows=snapshotter(site)
        _need(all(rows.get(p)==h for p,h in expected.items()))
        for path in set(rows)-set(expected):
            metadata=any(path==d+'/'+n for d in distributions for n in ('RECORD','INSTALLER','REQUESTED'))
            parts=Path(path)
            pyc=(parts.parent.name=='__pycache__' and parts.name.endswith('.cpython-311.pyc') and
                 (parts.parent.parent/(parts.name[:-len('.cpython-311.pyc')]+'.py')).as_posix() in expected)
            _need(metadata or pyc)
            if pyc:_need((site/path).read_bytes()[:4]==magic)
        raw=json.dumps(rows,sort_keys=True,separators=(',',':')).encode()
        return {'snapshot_sha256':hashlib.sha256(raw).hexdigest(),'files':len(rows),'installed_files':len(rows),'payload_files':len(expected)}
    except (OSError,ValueError,KeyError,zipfile.BadZipFile):raise ValueError('TOOL_PAYLOAD_MISMATCH') from None

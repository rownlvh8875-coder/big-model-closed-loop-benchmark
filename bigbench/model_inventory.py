"""Optional remote model inventory and safely checked downloads.

No automatic weights download. No ONNX evaluation or remote execution.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import quote
from urllib.request import Request, urlopen

HF_REPO = 'commaai/openpilot_driving_models'
HF_API = f'https://huggingface.co/api/models/{HF_REPO}/tree/main?recursive=true'
HASH_PATTERN = re.compile(r'[0-9a-f]{64}\Z')


def checked_model_path(path: str) -> str:
    p = PurePosixPath(path)
    if (not path.endswith('.onnx') or p.is_absolute() or '..' in p.parts or
            len(p.parts) < 2 or any(part in ('', '.') for part in p.parts)):
        raise ValueError('expected safe relative ONNX path in the official HF repository')
    return str(p)


def model_records(tree_data: list[dict]) -> list[dict]:
    if not isinstance(tree_data, list):
        raise ValueError('expected official Hugging Face tree list')
    records = []
    for item in tree_data:
        if item.get('type') != 'file':
            continue
        path = str(item.get('path', ''))
        if not path.endswith('.onnx'):
            continue
        path = checked_model_path(path)
        lfs = item.get('lfs') or {}
        oid = lfs.get('oid', '')
        records.append({'path':path,'size_bytes':item.get('size'),
                        'sha256':oid if isinstance(oid,str) and HASH_PATTERN.fullmatch(oid) else None,
                        'source_repo':HF_REPO,
                        'source_revision':'main (unpinned discovery; pin before comparative benchmark)'})
    return sorted(records,key=lambda o:o['path'])


def discover_official(timeout: float = 20) -> list[dict]:
    request = Request(HF_API, headers={'Accept':'application/json','User-Agent':'bigbench-offline-research/0.1'})
    with urlopen(request,timeout=timeout) as stream:
        raw=stream.read(3_000_001)
    if len(raw)>3_000_000:
        raise ValueError('model inventory response unexpectedly large')
    return model_records(json.loads(raw))


def download_checked(*, path: str, sha256: str, output_dir: Path,
                     max_bytes: int = 2_000_000_000, timeout: float = 45) -> Path:
    """Explicitly requested, hash-pinned file download; never auto-select models."""
    safe=checked_model_path(path)
    if not HASH_PATTERN.fullmatch(sha256) or max_bytes <= 0:
        raise ValueError('expected verified 64-character SHA256 and positive max_bytes')
    target=(output_dir / safe).resolve()
    root=output_dir.resolve()
    if not target.is_relative_to(root):
        raise ValueError('output path escapes model cache')
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        existing_hash=hashlib.sha256()
        with target.open('rb') as existing:
            for chunk in iter(lambda: existing.read(4 * 1024 * 1024), b''):
                existing_hash.update(chunk)
        if existing_hash.hexdigest()==sha256:
            return target
        raise ValueError('destination exists with a different hash; will not overwrite')
    url=f'https://huggingface.co/{HF_REPO}/resolve/main/'+quote(safe,safe='/')
    request=Request(url, headers={'User-Agent':'bigbench-offline-research/0.1'})
    temp=target.with_suffix('.partial')
    if temp.exists():
        raise ValueError('incomplete partial file exists; inspect/remove manually')
    total=0
    digest=hashlib.sha256()
    try:
        with urlopen(request,timeout=timeout) as stream, temp.open('xb') as output:
            while block:=stream.read(2*1024*1024):
                total += len(block)
                if total>max_bytes:
                    raise ValueError('remote model exceeded explicit byte limit')
                digest.update(block)
                output.write(block)
        if digest.hexdigest()!=sha256:
            raise ValueError('model SHA256 mismatch')
        temp.replace(target)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise
    return target

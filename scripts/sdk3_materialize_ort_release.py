"""Verify and reconstruct the exact Git worktree from the public release cache."""
import argparse
import base64
import hashlib
import json
import lzma
import os
from pathlib import Path, PurePosixPath
import struct
import subprocess


DATA = Path(__file__).resolve().parent / 'sdk3_action_terms_source'
PINS = json.loads((DATA / 'pins.json').read_bytes())


def git_sha(kind,data):
    return hashlib.sha1(f'{kind} {len(data)}\0'.encode()+data).digest()


class NarReader:
    def __init__(self, file, max_size, pins, line_endings):
        self.file=file
        self.limit=max_size
        self.pins=pins
        self.line_endings=line_endings
        self.restored=set()
        self.num_files=0
        self.decoded_bytes=0
        self.verified_gitlinks={}

    def exact(self,length):
        if not 0<=length<=self.limit-self.file.tell():
            raise ValueError('archive length out of bounds')
        data=self.file.read(length)
        if len(data)!=length:
            raise ValueError('truncated archive')
        return data

    def length(self):
        return struct.unpack('<Q',self.exact(8))[0]

    def padding(self,length):
        assert not any(self.exact((-length) % 8))

    def string(self, maximum=4096):
        length=self.length()
        assert length<=maximum
        data=self.exact(length)
        self.padding(length)
        return data

    def expect(self,value):
        assert self.string() == value

    def contents(self,path,executable):
        length=self.length()
        assert length<=self.limit-self.file.tell()
        identity=hashlib.sha1(f'blob {length}\0'.encode())
        with path.open('xb') as out:
            remaining=length
            while remaining:
                data=self.exact(min(1024*1024,remaining))
                identity.update(data)
                out.write(data)
                remaining-=len(data)
        self.padding(length)
        path.chmod(0o755 if executable else 0o644)
        self.decoded_bytes+=length
        self.num_files+=1
        return (b'100755' if executable else b'100644'),identity.digest()

    def node(self,out,parts):
        assert len(parts)<65
        self.expect(b'(')
        self.expect(b'type')
        kind=self.string()
        if kind==b'regular':
            key=self.string()
            executable=key==b'executable'
            if executable:
                self.expect(b'')
                key=self.string()
            assert key==b'contents'
            mode,identity=self.contents(out,executable)
            self.expect(b')')
            if parts in self.line_endings:
                before, after = self.line_endings[parts]
                assert not executable and out.stat().st_size < 1024*1024 and identity.hex() == before
                raw = out.read_bytes().replace(b'\r\n',b'\n')
                identity = git_sha('blob',raw)
                assert identity.hex() == after
                out.write_bytes(raw)
                self.restored.add(parts)
            return mode,identity
        if kind==b'symlink':
            self.expect(b'target')
            target=self.string()
            target_text=os.fsdecode(target)
            resolved=os.path.normpath(os.path.join(*parts[:-1],target_text)) if len(parts)>1 else os.path.normpath(target_text)
            assert not os.path.isabs(target_text) and not (resolved=='..' or resolved.startswith('../'))
            out.symlink_to(target_text)
            self.expect(b')')
            return b'120000',git_sha('blob',target)
        assert kind==b'directory'
        out.mkdir()
        children=[]
        previous=b''
        while True:
            token=self.string()
            if token==b')':
                break
            assert token==b'entry'
            self.expect(b'(')
            self.expect(b'name')
            name=self.string()
            assert name>previous and b'/' not in name and b'\x00' not in name
            assert name.lower() not in (b'.',b'..',b'.git') and b'\\' not in name
            previous=name
            self.expect(b'node')
            label=os.fsdecode(name)
            mode,value=self.node(out/label, parts+(label,))
            self.expect(b')')
            entry=mode+b' '+name+b'\0'+value
            children.append((name+(b'/' if mode==b'40000' else b''),entry))
        calculated=git_sha('tree',b''.join(entry for _,entry in sorted(children)))
        if parts in self.pins:
            pin,tree=self.pins[parts]
            if calculated.hex()!=tree:
                raise ValueError(f'gitlink tree mismatch at {out}: {calculated.hex()} != {tree}')
            self.verified_gitlinks['/'.join(parts)]=dict(commit=pin,tree=tree)
            return b'160000',bytes.fromhex(pin)
        return b'40000',calculated



def verify_bytes(path, size, sha256):
    assert path.stat().st_size == size, path.name
    with path.open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == sha256, path.name


def git(root, *args, data=None):
    return subprocess.check_output(['git', '-C', str(root), *args], input=data).decode().strip()


def materialize(compressed, root, receipt):
    archive = PINS['archive']
    verify_bytes(compressed, archive['compressed_bytes'], archive['compressed_sha256'])
    unpacked = root.with_suffix('.nar')
    with lzma.open(compressed, 'rb') as source, unpacked.open('xb') as out:
        remaining = archive['nar_bytes']
        while remaining:
            block = source.read(min(1024*1024, remaining))
            assert block, 'truncated NAR'
            out.write(block)
            remaining -= len(block)
        assert not source.read(1), 'extra NAR bytes'
    verify_bytes(unpacked, archive['nar_bytes'], archive['nar_sha256'])
    gitlinks = {PurePosixPath(name).parts: (item['commit'], item['tree'])
                for name, item in PINS['verified_gitlinks'].items()}
    line_endings = {PurePosixPath(name).parts: pair
                    for name, pair in PINS['restored_git_line_endings'].items()}
    with unpacked.open('rb') as stream:
        reader = NarReader(stream, archive['nar_bytes'], gitlinks, line_endings)
        reader.expect(b'nix-archive-1')
        mode, digest = reader.node(root, ())
        assert (mode, digest.hex()) == (b'40000', PINS['source_git_tree'])
        assert stream.tell() == archive['nar_bytes']
    assert reader.verified_gitlinks == PINS['verified_gitlinks']
    assert reader.restored == line_endings.keys()
    assert (root/'VERSION_NUMBER').read_text().strip() == '1.20.1'

    git(root, 'init', '--quiet')
    top = [name for name in PINS['verified_gitlinks']
           if not any(name.startswith(other + '/') for other in PINS['verified_gitlinks'])]
    git(root, '-c', 'core.autocrlf=false', 'add', '-f', '--', '.',
        *(f':(exclude,top){name}' for name in top))
    for name in top:
        git(root, 'update-index', '--add', '--cacheinfo',
            f"160000,{PINS['verified_gitlinks'][name]['commit']},{name}")
    name = 'onnxruntime/python/tools/transformers/models/phi2/README.md'
    raw = git(root, 'hash-object', '-w', '--no-filters', name)
    git(root, 'update-index', '--cacheinfo', f'100644,{raw},{name}')
    assert git(root, 'write-tree') == PINS['source_git_tree']
    commit = git(root, 'hash-object', '-w', '-t', 'commit', '--stdin',
                 data=base64.b64decode((DATA/'released-ort.commit.b64').read_bytes()))
    assert commit == PINS['source_commit']
    assert git(root, 'rev-parse', f'{commit}^{{tree}}') == PINS['source_git_tree']
    (root/'.git/shallow').write_text(commit+'\n')
    git(root, 'update-ref', '--no-deref', 'HEAD', commit)
    git(root, 'fsck', '--full')
    unpacked.unlink()
    result = dict(PINS, files=reader.num_files, decoded_file_bytes=reader.decoded_bytes)
    with receipt.open('x') as out:
        json.dump(result, out, indent=2)
        out.write('\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('source', type=Path)
    parser.add_argument('receipt', type=Path)
    args = parser.parse_args()
    materialize(args.archive, args.source, args.receipt)

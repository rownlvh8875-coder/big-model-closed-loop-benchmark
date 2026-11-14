"""Pure bounded selection metadata. Generated memory is never installed bytes."""
import hashlib
import json
import posixpath
import re

MAX_INPUT=1024**2
MAX_REPORT=512*1024
MAX_ROWS=10000
POLICY='image-source-and-indexed-runtime-data-v1'


def _need(value):
    if not value:raise ValueError('SELECTION_METADATA_REJECTED')


def _report(value):
    raw=(json.dumps(value,sort_keys=True,indent=2,ensure_ascii=True,allow_nan=False)+'\n').encode()
    if len(raw)<=MAX_REPORT:return value
    return dict(schema=value['schema'],policy=POLICY,accepted=False,rejections=[{'reason':'report_cap'}],
                incomplete_report_sha256=hashlib.sha256(raw).hexdigest(),incomplete_report_bytes=len(raw))


def _path(path):
    _need(type(path) is str and path.startswith('/') and len(path.encode())<=4096
          and '\x00' not in path and posixpath.normpath(path)==path)
    return path


def _source(path,sources):
    return path.startswith('/work/repo/') and path[len('/work/repo/'):] in sources


def classify_maps(raw,image_files,source_files,*,resolve=None,cache_root='/work/cache/case_00'):
    """Classify supplied proc text; resolve aliases only via caller's resolver."""
    result=dict(schema='native-mapping-selection-v1',policy=POLICY,accepted=False,image_files=[],source_files=[],
        runtime_mappings=[],anonymous_region_counts={'data':0,'executable':0},rejections=[],
        generated_memory_binary_equality_proven=False)
    try:
        _need(type(cache_root) is str and re.fullmatch(r'/work/cache/case_0[0-3]',cache_root) is not None)
        _need(type(raw) is str and len(raw.encode())<=MAX_INPUT)
        result['raw_view_sha256']=hashlib.sha256(raw.encode()).hexdigest();result['raw_view_bytes']=len(raw.encode())
        lines=raw.splitlines();_need(0<len(lines)<=MAX_ROWS)
        image=set();source=set();rejected=0
        for index,line in enumerate(lines):
            parts=line.split(None,5)
            _need(len(parts) in (5,6) and re.fullmatch('[0-9a-fA-F]+-[0-9a-fA-F]+',parts[0])
                  and re.fullmatch('[r-][w-][x-][ps]',parts[1]) and re.fullmatch('[0-9a-fA-F]+',parts[2])
                  and re.fullmatch('[0-9a-fA-F]+:[0-9a-fA-F]+',parts[3]) and re.fullmatch('[0-9]{1,20}',parts[4]))
            executable='x' in parts[1];name=parts[5] if len(parts)==6 else '';deleted=name.endswith(' (deleted)')
            path=name[:-10] if deleted else name;category=None;reason=None
            if not path:
                _need(int(parts[4])==0)
                result['anonymous_region_counts']['executable' if executable else 'data']+=1
                continue
            _need(len(path.encode())<=4096 and '\x00' not in path)
            if re.fullmatch(r'\[(?:heap|stack(?::[0-9]+)?|vdso|vvar(?:_vclock)?|vsyscall|anon:[^\]]{1,128}|anon_shmem:[^\]]{1,128})\]',path):category='kernel-region'
            elif path.startswith('/memfd:') and 0<len(path[len('/memfd:'):])<=256:category='anonymous-fd'
            elif re.fullmatch('/SYSV[0-9a-fA-F]{8}',path):category='private-ipc'
            elif path=='/dev/zero':category='anonymous-zero'
            elif path.startswith('/'):
                actual=_path(resolve(path) if resolve is not None else path)
                if actual in image_files and not deleted:image.add(actual);continue
                if _source(actual,source_files) and not deleted and not executable:source.add(actual);continue
                if not executable:
                    if actual.startswith(cache_root+'/'):category='registered-cache-data'
                    elif actual.startswith('/tmp/'):category='owned-tmp-data'
                    elif actual.startswith('/dev/shm/'):category='private-shm-data'
                    elif actual in ('/etc/hostname','/etc/hosts','/etc/mtab','/etc/resolv.conf'):category='managed-config-data'
                if category is None:reason='unregistered_or_deleted_filesystem_mapping'
                path=actual
            else:reason='unknown_mapping_label'
            if reason:
                rejected+=1
                if len(result['rejections'])<32:result['rejections'].append(dict(row=index,reason=reason,path=path,permissions=parts[1],deleted=deleted))
            else:result['runtime_mappings'].append(dict(category=category,path=path,permissions=parts[1],deleted=deleted))
        result.update(image_files=sorted(image),source_files=sorted(source),rejected_rows=rejected,
                      rejections_omitted=max(0,rejected-len(result['rejections'])),accepted=rejected==0,rows=len(lines))
    except Exception:
        result['accepted']=False;result['rejections'].append({'reason':'malformed_or_input_cap'})
    return _report(result)


def classify_modules(rows,image_files,source_files,*,resolve=None):
    """Supplied __file__/spec facts; files and pseudo modules stay distinct."""
    result=dict(schema='native-module-selection-v1',policy=POLICY,accepted=False,module_files={},module_pseudo={},rejections=[])
    try:
        _need(type(rows) is list and len(rows)<=MAX_ROWS);seen=set();size=0;rejected=0
        for name,path,origin in rows:
            _need(type(name) is str and re.fullmatch('[A-Za-z0-9_.-]{1,256}',name) and name not in seen);seen.add(name)
            _need(path is None or type(path) is str);_need(origin is None or type(origin) is str)
            size+=len(name.encode())+len((path or '').encode())+len((origin or '').encode());_need(size<=MAX_INPUT)
            if path is None:
                result['module_pseudo'][name]='builtin' if origin=='built-in' else 'frozen' if origin=='frozen' else 'no-file';continue
            actual=resolve(path) if resolve is not None else path
            if actual in image_files or _source(actual,source_files):result['module_files'][name]=actual
            elif origin in ('frozen','built-in') and (path in ('frozen','built-in') or re.fullmatch('<[^>]{1,128}>',path)):
                result['module_pseudo'][name]='frozen' if origin=='frozen' else 'builtin'
            else:
                rejected+=1
                if len(result['rejections'])<32:result['rejections'].append(dict(module=name,path=path,reason='unregistered_module_file'))
        result.update(accepted=rejected==0,rejected_modules=rejected,rejections_omitted=max(0,rejected-len(result['rejections'])))
    except Exception:
        result['accepted']=False;result['rejections'].append({'reason':'malformed_or_input_cap'})
    return _report(result)

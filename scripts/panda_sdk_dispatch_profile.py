"""Fixed SDK executable PT spans, DATA-only; no native loading."""
from scripts import panda_sdk_mapping_profile as old
from scripts.panda_sdk_link_elf import inspect_elf
from scripts.readback_process_mapping import elf_ranges
need=old.need;sha=old.sha;ROOT=old.ROOT;SDK=old.SDK;SDK_SHA=old.SDK_SHA;SDK_SIZE=old.SDK_SIZE
NAMES=('pca_context_size',)
def make_profile(raw,fixture=False):
 need(type(fixture) is bool,'fixture flag')
 if fixture:need(sha(raw)!=SDK_SHA,'production SDK cannot be fixture')
 else:need(len(raw)==SDK_SIZE and sha(raw)==SDK_SHA,'exact installed SDK')
 e=inspect_elf(raw);hits=[s for s in e['exports'] if s['name']=='pca_context_size'];need(len(hits)==1 and hits[0]['symbol_type']==2 and hits[0]['binding']==1,'one SDK anchor');anchor=hits[0];functions={}
 for i,p in enumerate(elf_ranges(raw)):
  if not p['flags']&1:continue
  need(not p['flags']&2 and 0<p['filesz']<=1024**2,'SDK executable profile');functions['sdk_text_'+str(i)]=dict(vaddr=p['vaddr'],size=p['filesz'],file_offset=p['offset'],sha256=sha(raw[p['offset']:p['offset']+p['filesz']]))
 need(functions and any(v['vaddr']<=anchor['value']<v['vaddr']+v['size'] for v in functions.values()),'SDK anchor executable')
 return dict(schema='panda-sdk-dispatch-profile-v1',sdk_sha256=sha(raw),sdk_nbytes=len(raw),anchor_vaddr=anchor['value'],functions=functions,panda_preloads=0 if fixture else 1,sdk_loads=1,probe_loads=1,probe_invocations=1,event_cap=256,full_object_abi_qualified=False,native_admitted=False,stage7_complete=False)

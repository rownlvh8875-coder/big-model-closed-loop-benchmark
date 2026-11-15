"""Pinned SDK and original libGL entry code as DATA; no library loading."""
import json
from pathlib import Path
from scripts import panda_sdk_dispatch_policy as base
from scripts.panda_sdk_link_elf import inspect_elf
from scripts.readback_process_mapping import elf_ranges
from scripts.panda_real_glx_frames import need,sha
ROOT=Path(__file__).resolve().parents[1];SDK_SHA=base.SDK_SHA;SDK=base.SDK;SDK_SIZE=base.SDK_SIZE
GLDATA='docs/evidence/panda-real-glx-01/libGL.so.data';GLSHA='67f471213576d225d38347a0b6d2a08a231980685301ff6461bd74d3994e5027';GLPATH='/usr/lib/x86_64-linux-gnu/libGL.so.1.7.0'
def entry(raw,name,size):
 hits=[s for s in inspect_elf(raw)['exports'] if s['name']==name];need(len(hits)==1 and hits[0]['symbol_type']==2 and hits[0]['binding']==1,'one GL entry');va=hits[0]['value'];loads=[p for p in elf_ranges(raw) if p['flags']&1 and not p['flags']&2 and p['vaddr']<=va and va+size<=p['vaddr']+p['filesz']];need(len(loads)==1,'entry executable range');offset=loads[0]['offset']+va-loads[0]['vaddr'];return dict(vaddr=va,size=size,file_offset=offset,sha256=sha(raw[offset:offset+size]))
def make_profile(raw=None,glraw=None,fixture=False):
 raw=(ROOT/SDK).read_bytes() if raw is None else raw
 if fixture:need(sha(raw)!=SDK_SHA,'production SDK cannot be fixture')
 else:need(len(raw)==SDK_SIZE and sha(raw)==SDK_SHA,'exact current SDK')
 anchor=entry(raw,'get_pipe_type_pandagl',1);functions={}
 for i,p in enumerate(elf_ranges(raw)):
  if p['flags']&1:
   need(not p['flags']&2 and 0<p['filesz']<=1024**2,'bounded SDK executable');functions['sdk_text_'+str(i)]=dict(vaddr=p['vaddr'],size=p['filesz'],file_offset=p['offset'],sha256=sha(raw[p['offset']:p['offset']+p['filesz']]))
 result=dict(schema='panda-real-glx-profile-v1',sdk_sha256=sha(raw),sdk_nbytes=len(raw),anchor_name='get_pipe_type_pandagl',anchor_vaddr=anchor['vaddr'],functions=functions,native_admitted=False,full_object_abi_qualified=False,stage7_complete=False)
 if fixture:result.update(read_binding=None,gl_profile=None);return result
 glraw=(ROOT/GLDATA).read_bytes() if glraw is None else glraw;need(sha(glraw)==GLSHA and len(glraw)==547136,'pinned image libGL DATA');need(raw[248832:248838]==bytes.fromhex('ff25fae00800'),'original bare readtail');result.update(read_binding=dict(tail_vaddr=248832,slot_vaddr=830720,slot_nbytes=8,invocation_trace_qualified=False),gl_profile=dict(path=GLPATH,sha256=GLSHA,nbytes=len(glraw),functions={'glReadPixels':entry(glraw,'glReadPixels',16)}));return result

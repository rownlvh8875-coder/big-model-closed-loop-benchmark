"""Four exact SDK loader-table code profiles. Reads DATA; never loads ELF."""
import hashlib,json
from pathlib import Path
from scripts.panda_sdk_link_elf import inspect_elf
from scripts.readback_process_mapping import elf_ranges
ROOT=Path(__file__).resolve().parents[1]
SDK='docs/evidence/panda-sdk-link-audit-01/before-review/build/candidate-libpandagl.so.data'
SDK_SHA='8d302ae2a610b56db4f7feca08fd736004cf6d3d9650fdb9834f19389a0b7342';SDK_SIZE=992200
NAMES=('pca_context_size','rc_context_size','psd_get_stats','psd_source_idle')
STATS={'configured':(0,4),'closed':(4,4),'error':(8,4),'forwarded':(16,8),'resolutions':(24,8),'paths':(32,8),'events':(40,8)}
def need(v,message):
 if not v:raise ValueError(message)
def sha(v):return hashlib.sha256(v).hexdigest()
def scalar_size(raw):
 need(type(raw) is bytes and len(raw)==6 and raw[0]==0xb8 and raw[-1]==0xc3,'fixed scalar return instruction');value=int.from_bytes(raw[1:5],'little');need(0<value<=4*1024**2,'bounded scalar size');return value
def export_ranges(raw):
 e=inspect_elf(raw);loads=elf_ranges(raw);result={}
 for name in NAMES:
  hits=[s for s in e['exports'] if s['name']==name];need(len(hits)==1,'one selected export');s=hits[0];need(s['binding']==1 and s['symbol_type']==2 and s['version'] is None and s['default_version'] and 0<s['nbytes']<=4096,'selected function profile');matches=[p for p in loads if p['flags']&1 and not p['flags']&2 and p['vaddr']<=s['value'] and s['value']+s['nbytes']<=p['vaddr']+p['filesz']];need(len(matches)==1,'selected executable span');p=matches[0];offset=p['offset']+s['value']-p['vaddr'];code=raw[offset:offset+s['nbytes']];result[name]=dict(vaddr=s['value'],size=s['nbytes'],file_offset=offset,sha256=sha(code),code_hex=code.hex())
 return result
def make_profile(raw):
 need(type(raw) is bytes and len(raw)==SDK_SIZE and sha(raw)==SDK_SHA,'exact installed SDK identity');functions=export_ranges(raw);sizes={n:scalar_size(bytes.fromhex(functions[n]['code_hex'])) for n in NAMES[:2]};need(sizes==dict(pca_context_size=2640344,rc_context_size=2320),'exact size ABI');return dict(schema='panda-sdk-mapping-profile-v1',sdk_sha256=SDK_SHA,sdk_nbytes=SDK_SIZE,functions=functions,expected_sizes=sizes,stats_size=48,stats_fields={n:dict(offset=o,width=w) for n,(o,w) in STATS.items()},stats_expected={n:0 for n in STATS},guard_hex='a5'*16,errno_seed=7,call_sequence=['stats_before','pca_context_size','rc_context_size','psd_source_idle','stats_after'],expected_returns=dict(stats_before=0,pca_context_size=2640344,rc_context_size=2320,psd_source_idle=-1,stats_after=0),panda_preloads=1,sdk_loads=1,full_object_abi_qualified=False,native_admitted=False,stage7_complete=False)
if __name__=='__main__':print(json.dumps(make_profile((ROOT/SDK).read_bytes()),indent=2))

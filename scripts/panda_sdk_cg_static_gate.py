"""Independent necessary layout/link checks on ELF DATA; never execute candidates."""
import json,struct,tempfile
from pathlib import Path
from scripts import panda_sdk_cg_inputs as inputs
from scripts import panda_sdk_link_elf as elf
from scripts import panda_sdk_link_image as image
from scripts import build_panda_adapter_sdk as interfaces
from scripts import build_panda_sdk_cg as builder
from scripts.readback_process_mapping import elf_ranges
need=inputs.need;read=inputs.read;sha=inputs.sha;ROOT=inputs.ROOT
MAGIC=0x50414e4441434731
MAJOR='_ZN23GLGraphicsStateGuardian24get_driver_version_majorEv'
MINOR='_ZN23GLGraphicsStateGuardian24get_driver_version_minorEv'
VENDOR='_ZN23GLGraphicsStateGuardian17get_driver_vendorEv'
VTABLE='_ZTV23GLGraphicsStateGuardian'
EXPECTED={'major':0x688,'minor':0x68c,'vendor':0x670}
WEAK={'_ITM_deregisterTMCloneTable','_ITM_registerTMCloneTable','__gmon_start__'}
def decode_int_getter(raw):
 need(len(raw)==7 and raw[:2]==b'\x8b\x87' and raw[-1:]==b'\xc3','unknown integer getter instruction');return struct.unpack('<I',raw[2:6])[0]
def decode_vendor_getter(raw):
 # Complete supported shapes only. No prefix-only claim about arbitrary suffixes.
 need(1<=len(raw)<=256,'vendor accessor extent');raw=raw[4:] if raw.startswith(bytes.fromhex('f30f1efa')) else raw
 if len(raw)==8 and raw[:3]==bytes.fromhex('488b86') and raw[-1:]==b'\xc3':return struct.unpack('<I',raw[3:7])[0]
 # ABI0 string copy via a single call, preserving the hidden return pointer.
 if len(raw)==23 and raw[:5]==bytes.fromhex('41544881c6') and raw[9:13]==bytes.fromhex('4989fce8') and raw[17:]==bytes.fromhex('4c89e0415cc3'):return struct.unpack('<I',raw[5:9])[0]
 # Inlined ABI0 COW string copy, including every branch/return. The only
 # variable operands are the member displacement and external RIP/PLT offsets.
 template=bytes.fromhex('534889fb4883ec10488b86000600008b50f8488d78e885d27816483b3dcfa70800752d4889034883c4104889d85bc390488d74240f31d2e8d492feff4889034883c4104889d85bc30f1f840000000000488b1571ab0800803a00740c8340f801ebc1660f1f440000488d48f8f0830101ebb1')
 if len(raw)==len(template):
  masked=bytearray(raw)
  for at,count in [(11,4),(29,4),(56,4),(83,4)]:masked[at:at+count]=template[at:at+count]
  if bytes(masked)==template:return struct.unpack('<I',raw[11:15])[0]
 raise ValueError('unknown complete vendor accessor shape')
def validate_vendor_call(raw,meta,loads,body,address):
 body=body[4:] if body.startswith(bytes.fromhex('f30f1efa')) else body
 # Only the complete copy templates contain calls; direct toy load/return does not.
 if len(body)==8:return
 at,expected=(12,'_ZNSsC1ERKSs') if len(body)==23 else (55,'_ZNSs4_Rep8_M_cloneERKSaIcEm')
 target=address+at+5+struct.unpack_from('<i',body,at+1)[0]
 def virtual(va,n,executable=False):
  rows=[p for p in loads if p['vaddr']<=va and va+n<=p['vaddr']+p['filesz'] and (not executable or p['flags']&1 and not p['flags']&2)];need(len(rows)==1,'vendor call file-backed span');p=rows[0];start=p['offset']+va-p['vaddr'];return raw[start:start+n]
 stub=virtual(target,10,True);skip=4 if stub.startswith(bytes.fromhex('f30f1efa')) else 0;skip+=1 if stub[skip:skip+1]==b'\xf2' else 0;need(stub[skip:skip+2]==b'\xff\x25','known string-copy PLT stub');got=target+skip+6+struct.unpack_from('<i',stub,skip+2)[0]
 h=struct.unpack_from('<16sHHIQQQIHHHHHH',raw);dynamics=[struct.unpack_from('<IIQQQQQQ',raw,h[5]+56*i) for i in range(h[10])];d=next(p for p in dynamics if p[0]==2);tags={}
 for pos in range(d[2],d[2]+d[5],16):
  tag,value=struct.unpack_from('<qQ',raw,pos)
  if tag==0:break
  tags[tag]=value
 found=[]
 for tag,size in [(7,8),(23,2)]:
  if tag not in tags:continue
  table=virtual(tags[tag],tags[size])
  for pos in range(0,len(table),24):
   slot,info,addend=struct.unpack_from('<QQq',table,pos)
   if slot==got:found.append((info>>32,info&0xffffffff,addend))
 need(len(found)==1 and found[0][1] in (6,7) and found[0][2]==0,'unique string-copy loader relocation');symbols=[r for r in meta['imports'] if r['symbol_index']==found[0][0]];need(len(symbols)==1 and symbols[0]['name']==expected and symbols[0]['symbol_type']==2,'known ABI0 string-copy import')
def candidate_offsets(raw):
 need(len(raw)<=4*1024**2,'candidate bound');meta=elf.inspect_elf(raw);loads=elf_ranges(raw)
 def symbol(name):
  rows=[r for r in meta['exports'] if r['name']==name];need(len(rows)==1,'unique dynamic symbol: '+name);return rows[0]
 def code(name):
  r=symbol(name);n=r['nbytes'];va=r['value'];need(r['symbol_type']==2 and 0<n<=256 and va<2**64-n,'ordinary FUNC code extent');rows=[p for p in loads if p['flags']&1 and not p['flags']&2 and p['vaddr']<=va and va+n<=p['vaddr']+p['filesz']];need(len(rows)==1,'file-backed executable symbol');p=rows[0];at=p['offset']+va-p['vaddr'];return raw[at:at+n]
 body=code(VENDOR);offsets=dict(major=decode_int_getter(code(MAJOR)),minor=decode_int_getter(code(MINOR)),vendor=decode_vendor_getter(body));validate_vendor_call(raw,meta,loads,body,symbol(VENDOR)['value']+(4 if body.startswith(bytes.fromhex('f30f1efa')) else 0));v=symbol(VTABLE);need(v['nbytes']==1024,'public GSG vtable width');return dict(offsets=offsets,vtable_nbytes=1024,candidate_sha256=sha(raw),loader=meta)

def layout_from_object(raw):
 need(64<=len(raw)<=1024**2 and raw[:6]==b'\x7fELF\x02\x01','layout ELF64LE');h=struct.unpack_from('<16sHHIQQQIHHHHHH',raw);need(h[1]==1 and h[2]==62 and h[3]==1 and h[8]==64 and h[10]==0 and h[11]==64 and 1<=h[12]<=256 and h[13]<h[12],'compile-only AMD64 object');off=h[6];need(64<=off and off+64*h[12]<=len(raw),'layout section table')
 sections=[struct.unpack_from('<IIQQQQIIQQ',raw,off+64*i) for i in range(h[12])];ss=sections[h[13]];need(ss[1]==3 and 0<=ss[4]<=len(raw) and ss[4]+ss[5]<=len(raw) and ss[5]<=65536,'section names');names=raw[ss[4]:ss[4]+ss[5]];selected=[];spans=[]
 for s in sections:
  need(not(s[2]&4 and s[5]) and not(s[1] in (4,9,14,15,16) and s[5]),'layout object must contain only literal DATA, no executable/init/relocation code')
  if s[1]!=8 and s[5]:
   need(64<=s[4] and s[4]+s[5]<=len(raw) and (s[4]+s[5]<=off or s[4]>=off+64*h[12]),'layout section extent');spans.append((s[4],s[4]+s[5]))
  need(s[0]<len(names),'section name index');end=names.find(b'\0',s[0]);need(end>=s[0],'section name termination')
  if names[s[0]:end]==b'.panda_cg_layout':need(s[1]==1 and s[2]&2 and s[5]==96,'fixed allocated layout DATA');selected.append(raw[s[4]:s[4]+s[5]])
 spans.sort();need(all(a[1]<=b[0] for a,b in zip(spans,spans[1:])),'overlapping layout sections');need(len(selected)==1,'unique layout descriptor');words=struct.unpack('<12Q',selected[0]);need(words[:5]==(MAGIC,1,8,0,1) and 32<=words[5]<=2**20 and all(0<x<=2**20 for x in words[6:9]),'layout ABI/config/sizes');need(words[9]+8<=words[8] and all(x+4<=words[8] for x in words[10:]),'layout member bounds');return dict(schema='panda-sdk-cg-layout-v1',object_sha256=sha(raw),shader_caps_size=words[5],graphics_pipe_size=words[6],gsg_size=words[7],gl_gsg_size=words[8],offsets=dict(vendor=words[9],major=words[10],minor=words[11]),target_executed=False)
def check_layout(code,layout):
 need(code['offsets']==EXPECTED,'candidate member offsets mismatch: '+repr(code['offsets']));need(layout['offsets']==EXPECTED and layout['offsets']==code['offsets'],'code/descriptor offsets mismatch');need(layout['shader_caps_size']>=32,'Cg ShaderCaps fields')
def check_symbol_availability(report):
 need(report['root_strong_symbols_available'] is True and report['missing']==[] and report['unsupported_features']==[],'root static link blocked');need({x['name'] for x in report['weak_unresolved']}==WEAK and len(report['weak_unresolved'])==3,'closed weak exceptions')

class FrozenProviders:
 def __init__(self,inventory,paths):self.inventory=image.Inventory(inventory);self.paths=paths;self.cache={}
 def collect(self,wanted):
  need(len(self.cache)+len(wanted)<=64,'provider count');result={}
  for p in wanted:
   need(self.inventory.resolve(p)==p and p in self.paths,'missing current-image provider DATA: '+p);row=self.inventory.rows[p];raw=read(self.paths[p],64*1024**2);need(len(raw)==row['nbytes'] and sha(raw)==row['sha256'],'provider DATA mismatch: '+p);r=dict(path=p,nbytes=len(raw),sha256=sha(raw),data_path=str(Path(self.paths[p]).absolute()),native_admitted=False);result[p]=r;self.cache[p]=r
  return result

def audit_candidate(candidate,layout_object,build,reference,providers):
 result=dict(schema='panda-sdk-cg-static-gate-v1',status='STATIC_CG_CANDIDATE_REJECTED',reasons=[],native_admitted=False,full_object_abi_qualified=False,previous_abort_fixed=False,candidate_installed=False,runtime_mapping_qualified=False,stage7_complete=False,external_build_origin_authenticated=False)
 try:
  raw=read(candidate,4*1024**2);code=candidate_offsets(raw);result['candidate_sha256']=sha(raw);result['candidate_nbytes']=len(raw);result['offsets']=code['offsets']
  for key,value in EXPECTED.items():
   if code['offsets'][key]!=value:result['reasons'].append(key+': '+hex(code['offsets'][key])+' != '+hex(value))
  need(not result['reasons'],'old/incompatible member offsets');layout=layout_from_object(read(layout_object,1024**2));check_layout(code,layout);result['layout']=layout
  need(build.get('status')=='CG_SDK_COMPILED_NOT_LOADED' and build.get('build_start_attempts')==1 and type(build['build_start_attempts']) is int and build.get('target_execution') is False and build.get('native_admitted') is False and build.get('candidate_sha256')==sha(raw) and build.get('layout',{}).get('object_sha256')==layout['object_sha256'],'actual build receipt not ready')
  config=build['configuration'];need(config.get('HAVE_CG') in ('1',True) and config.get('HAVE_X11') in ('1',True) and config.get('HAVE_PYTHON') is False and config.get('STDFLOAT_DOUBLE') is False,'generated Cg/ABI configuration')
  c=inputs.contract();need(Path(reference).absolute()==ROOT/c['audit_path'] and sha(read(reference,4*1024**2))==c['audit_sha256'],'frozen baseline audit');c,authority,rows=inputs.image_authority(ROOT/c['current_image_acceptance_path']);inv=inputs.parse(read(ROOT/inputs.INVENTORY,16*1024**2));need({x['name'] for x in authority['installed_root_static_audit']['root_symbol_availability']['weak_unresolved']}==WEAK,'frozen weak exception set')
  for name,pin in c['image_cg_providers'].items():
   path=pin['image_path'];need(path in providers,'Cg image provider missing');data=read(providers[path],64*1024**2);need(len(data)==pin['nbytes'] and sha(data)==pin['sha256'],'Cg provider substitution')
  reader=FrozenProviders(inv,providers);availability,nodes=image.provider_graph(reader,raw);check_symbol_availability(availability);need(all(not n['unsupported_features'] for n in nodes.values()),'unsupported provider-loader feature');result['provider_audit']=availability;result['loader_metadata']=nodes
  with tempfile.TemporaryDirectory(prefix='cg-interfaces-') as folder:
   ir=interfaces.inspect_exports(Path(candidate).absolute(),Path(folder));need(ir['source_state_instances']==1 and len(ir['required_exports'])==33,'source state/API contract');result['interfaces']=ir
  result.update(status='CG_CANDIDATE_SELECTED_LAYOUT_MATCH_NOT_RUNTIME',selected_layout_match=True,vtable_nbytes=1024,unknown_wheel_class_sizes=True,full_dependency_closure_qualified=False)
 except (ValueError,OSError,KeyError,TypeError,struct.error) as e:result['reasons'].append(type(e).__name__+': '+str(e))
 return result

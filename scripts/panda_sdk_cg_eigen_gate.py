"""Independent complete CET accessor and Eigen literal DATA gate, never runtime admission."""
import struct,tempfile
from pathlib import Path
from scripts import panda_sdk_cg_inputs as inputs
from scripts import panda_sdk_cg_eigen_inputs as eigen
from scripts import panda_sdk_cg_eigen_layout as literal
from scripts import build_panda_sdk_cg_eigen as builder
from scripts import panda_sdk_cg_static_gate as old
from scripts import panda_sdk_link_elf as elf
from scripts import panda_sdk_link_image as image
from scripts import build_panda_adapter_sdk as interfaces
from scripts.readback_process_mapping import elf_ranges
ROOT=inputs.ROOT;need=inputs.need;read=inputs.read;sha=inputs.sha
MAJOR=old.MAJOR;MINOR=old.MINOR;VENDOR=old.VENDOR;VTABLE=old.VTABLE;EXPECTED=old.EXPECTED;WEAK=old.WEAK
FrozenProviders=old.FrozenProviders;check_symbol_availability=old.check_symbol_availability
CET=bytes.fromhex('f30f1efa')
VENDOR13=bytes.fromhex('534889fb4883ec10488b86600600008b50f8488d78e885d2781a483b3d7b2b090075294889034883c4104889d85bc30f1f440000488d74240f31d2e8ac90feff4889034883c4104889d85bc3488b15412f0900803a00740c8340f801ebc5660f1f440000488d48f8f0830101ebb5')
def strip_cet(raw):return raw[4:] if raw.startswith(CET) else raw
def decode_int_getter(raw):return old.decode_int_getter(strip_cet(raw))
def decode_vendor_getter(raw):
 body=strip_cet(raw)
 if len(body)==len(VENDOR13):
  masked=bytearray(body)
  for at in [11,29,60,79]:masked[at:at+4]=VENDOR13[at:at+4]
  if bytes(masked)==VENDOR13:return struct.unpack_from('<I',body,11)[0]
 # Prevent a second CET prefix being normalized by the legacy helper.
 need(not body.startswith(CET),'multiple CET prefixes');return old.decode_vendor_getter(body)
def validate_vendor_call(raw,meta,loads,body,address):
 body=body[4:] if body.startswith(bytes.fromhex('f30f1efa')) else body
 # Only the complete copy templates contain calls; direct toy load/return does not.
 if len(body)==8:return
 at,expected=(12,'_ZNSsC1ERKSs') if len(body)==23 else ((59 if len(body)==110 else 55),'_ZNSs4_Rep8_M_cloneERKSaIcEm')
 target=address+at+5+struct.unpack_from('<i',body,at+1)[0]
 def virtual(va,n,executable=False):
  rows=[p for p in loads if p['vaddr']<=va and va+n<=p['vaddr']+p['filesz'] and (not executable or p['flags']&1 and not p['flags']&2)];need(len(rows)==1,'vendor call file-backed span');p=rows[0];start=p['offset']+va-p['vaddr'];return raw[start:start+n]
 stub=virtual(target,16,True);skip=4 if stub.startswith(bytes.fromhex('f30f1efa')) else 0;skip+=1 if stub[skip:skip+1]==b'\xf2' else 0;need(stub[skip:skip+2]==b'\xff\x25','known string-copy PLT stub');got=target+skip+6+struct.unpack_from('<i',stub,skip+2)[0]
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
 need(type(raw) is bytes and len(raw)<=4*1024**2,'candidate bound');meta=elf.inspect_elf(raw);loads=elf_ranges(raw);extents=[]
 def symbol(name):
  rows=[r for r in meta['exports'] if r['name']==name];need(len(rows)==1,'unique symbol '+name);return rows[0]
 def code(name):
  r=symbol(name);va,n=r['value'],r['nbytes'];need(r['symbol_type']==2 and 0<n<=256 and va<2**64-n,'ordinary bounded FUNC');segments=[p for p in loads if p['flags']&1 and not p['flags']&2 and p['vaddr']<=va and va+n<=p['vaddr']+p['filesz']];need(len(segments)==1,'unique executable file span');need(all(va+n<=a or b<=va for a,b in extents),'overlapping getter extents');extents.append((va,va+n));p=segments[0];offset=p['offset']+va-p['vaddr'];return raw[offset:offset+n]
 major=decode_int_getter(code(MAJOR));minor=decode_int_getter(code(MINOR));body=code(VENDOR);vendor=decode_vendor_getter(body);validate_vendor_call(raw,meta,loads,body,symbol(VENDOR)['value']+(4 if body.startswith(CET) else 0));v=symbol(VTABLE);need(v['symbol_type']==1 and v['nbytes']==1024,'public GSG vtable width/type');return dict(offsets=dict(major=major,minor=minor,vendor=vendor),vtable_nbytes=1024,candidate_sha256=sha(raw),loader=meta)
def check_offsets(offsets,layout):
 need(offsets==EXPECTED,'candidate member offsets mismatch: '+repr(offsets));need(layout['offsets']==EXPECTED and layout['offsets']==offsets,'descriptor/code offsets mismatch')
def audit_candidate(candidate,parent,descriptor,build,providers):
 result=dict(schema='panda-sdk-cg-eigen-static-gate-v2',status='STATIC_CG_EIGEN_CANDIDATE_REJECTED',reasons=[],native_admitted=False,full_object_abi_qualified=False,previous_abort_fixed=False,candidate_installed=False,runtime_mapping_qualified=False,stage7_complete=False,external_build_origin_authenticated=False)
 try:
  raw=read(candidate,4*1024**2);code=candidate_offsets(raw);result.update(candidate_sha256=sha(raw),candidate_nbytes=len(raw),offsets=code['offsets']);parent_raw=read(parent,1024**2);descriptor_raw=read(descriptor,128);layout=literal.verify_pair(parent_raw,descriptor_raw);result['layout']=layout;check_offsets(code['offsets'],layout)
  need(build.get('status')=='CG_EIGEN_SDK_COMPILED_NOT_LOADED' and type(build.get('build_start_attempts')) is int and build['build_start_attempts']==1 and build.get('target_execution') is False and build.get('native_admitted') is False and build.get('candidate_sha256')==sha(raw) and build.get('layout',{}).get('object_sha256')==sha(parent_raw) and build.get('layout',{}).get('descriptor_sha256')==sha(descriptor_raw),'actual Eigen build facts');builder.validate_generated(build['configuration']);effective=build['effective_configuration'];builder.validate_effective(effective['macros']);need(effective['vector_alignment']==layout['vector_alignment']==16 and effective['memory_alignment']==layout['memory_alignment']==16 and effective['target_execution'] is False,'effective descriptor configuration')
  c=inputs.contract();need(sha(read(ROOT/c['audit_path'],4*1024**2))==c['audit_sha256'],'frozen baseline audit');c,authority,rows=inputs.image_authority(ROOT/c['current_image_acceptance_path']);inventory=inputs.parse(read(ROOT/inputs.INVENTORY,16*1024**2));need({x['name'] for x in authority['installed_root_static_audit']['root_symbol_availability']['weak_unresolved']}==WEAK,'frozen weak exceptions')
  for name,pin in c['image_cg_providers'].items():
   path=pin['image_path'];need(path in providers,'Cg provider missing');data=read(providers[path],64*1024**2);need(len(data)==pin['nbytes'] and sha(data)==pin['sha256'],'Cg provider substitution')
  reader=FrozenProviders(inventory,providers);availability,nodes=image.provider_graph(reader,raw);check_symbol_availability(availability);need(all(not n['unsupported_features'] for n in nodes.values()),'unsupported provider feature');result.update(provider_audit=availability,loader_metadata=nodes)
  with tempfile.TemporaryDirectory(prefix='cg-eigen-interfaces-') as folder:
   ir=interfaces.inspect_exports(Path(candidate).absolute(),Path(folder));need(ir['source_state_instances']==1 and len(ir['required_exports'])==33,'source state/API contract');result['interfaces']=ir
  result.update(status='CG_EIGEN_CANDIDATE_SELECTED_LAYOUT_MATCH_NOT_RUNTIME',selected_layout_match=True,vtable_nbytes=1024,unknown_wheel_class_sizes=True,full_dependency_closure_qualified=False)
 except (ValueError,OSError,KeyError,TypeError,struct.error) as error:result['reasons'].append(type(error).__name__+': '+str(error))
 return result

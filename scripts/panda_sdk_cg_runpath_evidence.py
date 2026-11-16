"""Independent carrier-record coherence checks, not remeasurement of remote tool bytes."""
import json,posixpath,re
from pathlib import Path,PurePosixPath as P
from scripts import panda_sdk_cg_eigen_inputs as e
from scripts import panda_sdk_cg_inputs as cg
from scripts import build_panda_sdk_cg_runpath as b
from scripts import panda_sdk_cg_runpath_gate as gate
need=e.need;sha=e.sha;read=e.read;ROOT=e.ROOT
BASE='docs/evidence/panda-sdk-cg-candidate-01/actual/acceptance/candidate/reports/'
BASE_INPUTS_SHA='494d79bdb706aea8fee35e4c2c408761aef10487192d526747d03508afd056e7'
BASE_SOURCE_SHA='42267657cd34308adea07449115791065fb7bf722d4a74644ef1d2a7089208b7'
CG_KEYS=['schema','status','root','contract_sha256','archive_sha256','image_authority_sha256','inventory_sha256','files','providers','target_execution','native_admitted','external_build_origin_authenticated']
def digest_ok(value):return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None
def absolute(value):
 need(type(value) is str and 0<len(value)<=4096 and '\0' not in value and P(value).is_absolute() and str(P(value))==value and '..' not in P(value).parts,'canonical reported absolute path');return P(value)
def relative(value):
 need(type(value) is str and 0<len(value)<=4096 and '\0' not in value and not P(value).is_absolute() and '..' not in P(value).parts and value not in ('.','') and str(P(value))==value,'bounded relative record path');return value
def file_fact(row):
 need(type(row) is dict and row.get('kind')=='file' and type(row.get('nbytes')) is int and 0<=row['nbytes']<=8*1024**3 and digest_ok(row.get('sha256')),'file identity record');
 if 'mode' in row:need(type(row['mode']) is int and 0<=row['mode']<=0o777,'file mode observation')
 return row['nbytes'],row['sha256']
def index(rows):
 need(type(rows) is list and 0<len(rows)<=20000,'record inventory');result={}
 for row in rows:
  name=relative(row['path']);need(name not in result and row['kind'] in ('file','symlink'),'unique file/link inventory')
  if row['kind']=='file':file_fact(row)
  else:need(type(row.get('target')) is str and 0<len(row['target'])<=4096,'bounded alias target')
  result[name]=row
 return result
def successful(command,argv,cwd):
 need(command['argv']==argv and command['cwd']==str(cwd) and command['status']=='EXITED' and command['returncode']==0 and command['owned_group_reaped'] is True and command['streams_complete'] is True and 0<=command['elapsed_seconds']<=1200,'owned command/argv/result binding')
def validate_build_evidence(receipt,root):
 try:return _validate(receipt,Path(root))
 except (KeyError,TypeError,AttributeError,IndexError) as error:raise ValueError('malformed build evidence: '+str(error)) from error

def diagnostic_records(receipt,root):
 diagnostics=receipt['diagnostics'];need(diagnostics['truncated'] is False and not diagnostics.get('omitted_members',[]),'complete positive diagnostic records');rows=diagnostics['streams'];need(type(rows) is list and 1<=len(rows)<=2048,'bounded diagnostic manifest');host=read(root/'logs/host.log',16*1024**2);make=read(root/'logs/makepanda.log',16*1024**2);records={};position=0
 for index,row in enumerate(rows):
  name=relative(row['path']);need(name.startswith('work/') and '\n' not in name and '\r' not in name and name not in records,'unique owned diagnostic path');count=row['saved_nbytes'];need(type(count) is int and type(row['observed_nbytes']) is int and 0<=count==row['observed_nbytes']<=16*1024**2 and row['truncated'] is False,'complete bounded diagnostic extent')
  if index==0:need(name=='work/build/makepanda/stdout.log' and count==len(make),'separate compiler stdout record');records[name]=make;continue
  header=name.encode()+b'\n';need(host[position:position+len(header)]==header,'retained diagnostic framing');position+=len(header);need(position+count<=len(host),'retained diagnostic span');records[name]=host[position:position+count];position+=count
 need(position==len(host),'closed retained host diagnostic stream');return records

def bind_command(command,folder,work,records):
 prefix='work/'+str(folder.relative_to(work));need(e.parse(records[prefix+'/command.json'])==command,'retained owned command receipt')
 for stream in ('stdout','stderr'):
  raw=records[prefix+'/'+stream+'.log'];fact=command['streams'][stream];need(len(raw)==fact['observed_nbytes']==fact['saved_nbytes'] and sha(raw)==fact['sha256'],'retained owned command stream binding')

def bind_tools(profile,work,repo,records,after=False):
 path=absolute(profile['evidence_path'])
 if after:need(re.fullmatch(re.escape(str(work))+r'/tool-rechecks/(?:[0-9]|1[0-5])/profile\.json',str(path)) is not None,'owned postcheck tool profile')
 else:need(path==work/'tool-profile.json','owned initial tool profile')
 name='work/'+str(path.relative_to(work));need(e.parse(records[name])==profile,'retained measured tool profile')
 for index,query in enumerate(profile['queries']):
  folder=path.parent/(path.stem+'-queries')/str(index);need(query['result'].get('cwd')==str(repo),'repository-owned tool query cwd')
  for stream in ('stdout','stderr'):need(absolute(query[stream+'_path'])==folder/(stream+'.log'),'owned tool query stream path');need(records['work/'+str((folder/(stream+'.log')).relative_to(work))]==query[stream].encode(),'retained query text')
  bind_command(query['result'],folder,work,records)

def bind_layout(build,root,work,repo,records,parent,descriptor,layout_cmd):
 layout=build['layout'];folder=work/'build/layout-build';bind_command(layout['command'],folder/'compile',work,records);argv=[item for item in layout_cmd[:-2] if item not in ('-c','-MD')]+['-E','-dM'];macro=layout['macro_command'];successful(macro,argv,repo);need(macro['elapsed_seconds']<=60,'bounded macro preprocessing');bind_command(macro,folder/'effective-macros',work,records);raw=records['work/build/layout-build/effective-macros/stdout.log'];need(len(raw)<=1024**2,'bounded retained macro output');macros={}
 for line in raw.decode().splitlines():
  fields=line.split(maxsplit=2)
  if len(fields)>=2 and fields[0]=='#define':macros[fields[1]]=fields[2] if len(fields)==3 else ''
 b.validate_effective(macros);measured=gate.previous.literal.verify_pair(parent,descriptor);names=('HAVE_CG','HAVE_EIGEN','HAVE_X11','HAVE_PYTHON','STDFLOAT_DOUBLE','LINMATH_ALIGN','MEMORY_HOOK_ALIGNMENT','_GLIBCXX_USE_CXX11_ABI');expected=dict(schema='panda-cg-eigen-effective-config-v2',macros={name:macros.get(name) for name in names},vector_alignment=measured['vector_alignment'],memory_alignment=measured['memory_alignment'],macro_stdout_sha256=sha(raw),target_execution=False)
 def report(name):return e.parse(read(root/'reports'/str(name+'.json'),16*1024**2))
 need(build['effective_configuration']==layout['effective_configuration']==report('effective-configuration')==expected,'retained macro/nested/reported effective configuration');need(report('layout')==report('gate')['layout']==measured,'standalone/gate/actual literal layout');extraction=gate.previous.literal.extract_literal(parent);extraction.pop('raw');need(layout['extraction']==report('layout-extraction')==extraction,'nested/reported/actual literal extraction');need(report('configuration')==build['configuration'],'reported generated configuration');b.validate_generated(build['configuration']);need(report('configuration-delta')==b.configuration_delta(build['configuration']),'reported configuration delta')
def _validate(receipt,root):
 def report(name):return e.parse(read(root/'reports'/str(name+'.json'),16*1024**2))
 build=receipt['compiler_build'];gate.validate_link_facts(build);need(build['status']=='CG_EIGEN_SDK_COMPILED_NOT_LOADED' and type(build['build_start_attempts']) is int and build['build_start_attempts']==1 and build['native_admitted'] is False and build['target_execution'] is False,'compile-only build receipt');need(0<build['compile_elapsed_seconds']<=1200,'shared compile deadline')
 q=report('inputs');old_raw=read(ROOT/BASE/'inputs.json',16*1024**2);need(sha(old_raw)==BASE_INPUTS_SHA,'pinned original input report');old=e.parse(old_raw);private=absolute(q['root']);work=private.parent;repo=private.parents[4];expected_work=repo/'output/stage7-panda-sdk-cg-runpath-candidate-03/producer/work';need(work==expected_work and private==work/'private','owned reported roots');stage=work/'source';build_root=work/'build';sdk=build_root/'sdk';project=repo/'native/panda_sdk_cg_v2/layout_contract.cxx'
 for name in CG_KEYS:
  if name not in ('root','providers'):need(q[name]==old[name],'pinned Cg/image input facts: '+name)
 need(set(q['providers'])==set(old['providers']),'exact Cg providers')
 for name,row in q['providers'].items():
  need({k:v for k,v in row.items() if k!='source_path'}=={k:v for k,v in old['providers'][name].items() if k!='source_path'},'pinned image provider bytes');need(absolute(row['source_path']).is_relative_to(work/'provider-data'),'owned provider DATA path')
 for name in ('header_packages','linker_aliases'):need(q[name]==old[name],'pinned GL/X11 headers/provider aliases')
 c=e.contract();manifest_raw=read(ROOT/c['eigen_headers_path'],1024**2);need(sha(manifest_raw)==c['eigen_headers_sha256'],'Eigen manifest authority');manifest=e.parse(manifest_raw);eig=q['eigen'];expected_eigen=dict(schema='panda-sdk-cg-eigen-inputs-v2',status='EIGEN_HEADERS_QUALIFIED_DATA_ONLY',root=str(private),contract_sha256=e.CONTRACT_SHA,package_sha256=c['eigen']['sha256'],header_files=530,header_nbytes=8669561,version='3.4.0',files=manifest['files'],target_execution=False,native_admitted=False,external_build_origin_authenticated=False);need(eig==expected_eigen,'exact530 Eigen header qualification')
 expected_private=dict(old['private_before'])
 for name,row in manifest['files'].items():expected_private[name]=dict(kind='file',mode=420,**row)
 for name,data in [('inputs.json',{k:q[k] for k in CG_KEYS}),('eigen-inputs.json',eig)]:
  raw=(json.dumps(data,indent=2)+'\n').encode();expected_private[name]=dict(kind='file',nbytes=len(raw),sha256=sha(raw),mode=q['private_before'][name]['mode'])
 need(q['private_before']==expected_private,'exact private header/provider snapshot')
 log=read(root/'logs/makepanda.log',16*1024**2);stdout=build['command']['streams']['stdout'];need(len(log)==stdout['observed_nbytes']==stdout['saved_nbytes'] and sha(log)==stdout['sha256'],'retained complete compiler stdout binding');need(b.capture_link_commands(log.decode(),build_root)==build['link_commands'],'retained actual link argv provenance');gate.validate_runpath(read(root/'candidate/libpandagl.so.data',4*1024**2),read(root/'candidate/build-libpanda.so.data',64*1024**2))
 records=diagnostic_records(receipt,root);before,after=report('tools-before'),report('tools-after');bind_tools(before,work,repo,records);bind_tools(after,work,repo,records,after=True);need(before['tools']==after['tools']==b.TOOLS and b.tool_facts(before)==b.tool_facts(after),'before/after selected tool facts')
 for profile in (before,after):
  for name,row in profile['files'].items():absolute(name);absolute(row['resolved_path']);need(type(row['nbytes']) is int and 0<row['nbytes']<=64*1024**2 and digest_ok(row['sha256']),'bounded selected tool identity')
 host=report('host-before');need(type(host) is dict and 0<len(host)<=65536,'bounded host catalogue');host_roots=[P('/usr/include'),P('/usr/lib/gcc/x86_64-linux-gnu/13/include'),P('/usr/share/bison')];host_bytes=0
 for name,row in host.items():
  path=absolute(name);need(any(path.is_relative_to(prefix) for prefix in host_roots),'declared host header roots');need(row['kind'] in ('file','directory','symlink'),'host node kind')
  if row['kind']=='file':host_bytes+=file_fact(row)[0]
 need(host_bytes<=1024**3,'host catalogue byte budget')
 source_raw=read(root/'reports/source-manifest.json',16*1024**2);need(sha(source_raw)==BASE_SOURCE_SHA==build['source_manifest_sha256'],'pinned reconstructed source manifest');source=e.parse(source_raw);source_rows=index(source['source_tree']);need(source['source_tree_files']==len(source_rows),'source inventory count');outputs=index(report('sdk-output-manifest'));need(sum(r.get('nbytes',0) for r in outputs.values())<=8*1024**3,'SDK output byte budget')
 names={'candidate/libpandagl.so.data':('lib/libpandagl.so','candidate_sha256',4*1024**2),'candidate/build-libpanda.so.data':('lib/libpanda.so.1.10','build_panda_sha256',64*1024**2)}
 for name,(member,key,limit) in names.items():
  raw=read(root/name,limit);need(sha(raw)==build[key] and file_fact(outputs[member])==(len(raw),sha(raw)),'actual retained SDK artifact/output binding')
 parent=read(root/'candidate/layout-contract.o.data',1024**2);descriptor=read(root/'candidate/layout-descriptor.data',128);need(sha(parent)==build['layout']['object_sha256'] and sha(descriptor)==build['layout']['descriptor_sha256'],'parent/raw receipt hashes');need(build['candidate']==str(sdk/'lib/libpandagl.so') and build['build_panda']==str(sdk/'lib/libpanda.so.1.10') and build['layout']['object']==str(build_root/'layout-build/layout-contract.o') and build['layout']['descriptor']==str(build_root/'layout-build/layout-descriptor.data'),'owned artifact locations')
 argv=b.build_command(stage,private,build_root,b.TOOLS['python']);need(build['argv']==argv,'fixed Eigen source compiler argv');successful(build['command'],argv,stage);layout_cmd=b.layout_command(sdk/'include',private,build_root/'layout-build/layout-contract.o',b.TOOLS['cxx']);layout_cmd=[str(project) if item==str(ROOT/'native/panda_sdk_cg_v2/layout_contract.cxx') else item for item in layout_cmd];successful(build['layout']['command'],layout_cmd,repo)
 catalogue={}
 for prefix,rows in [(stage,source_rows),(sdk,outputs),(private,q['private_before'])]:
  for name,row in rows.items():catalogue[str(prefix/relative(name))]=row
 catalogue.update(host);cache={}
 def resolve(name):
  need(type(name) is str and 0<len(name)<=4096 and '\0' not in name,'dependency path');key=name
  if key in cache:return cache[key]
  path=posixpath.normpath(name if P(name).is_absolute() else str(stage/name))
  for _ in range(64):
   parts=P(path).parts;changed=False
   for end in range(2,len(parts)+1):
    prefix=P(*parts[:end]);row=catalogue.get(str(prefix))
    if row and row['kind']=='symlink':path=posixpath.normpath(str(P(row['target']) if P(row['target']).is_absolute() else prefix.parent/row['target'])+('/'+'/'.join(parts[end:]) if end<len(parts) else ''));changed=True;break
   if not changed:cache[key]=path;return path
  raise ValueError('dependency alias cycle')
 used=report('used-inputs');need(type(used) is list and 0<len(used)<=65536,'used input records');b.validate_declared_headers(used);used_map={};origins=set();project_raw=read(ROOT/'native/panda_sdk_cg_v2/layout_contract.cxx',1024**2)
 for row in used:
  name=str(absolute(row['path']));need(name not in used_map and row['origin'] in ('source','generated','private','host'),'unique declared dependency origin');file_fact(row);used_map[name]=row;origins.add(row['origin'])
  if name==str(project):need(row['origin']=='source' and row.get('source_group')=='candidate-layout-project' and file_fact(row)==(len(project_raw),sha(project_raw)),'new descriptor project source')
  else:
   matches=[tag for prefix,tag in [(stage,'source'),(sdk,'generated'),(private,'private')] if P(name).is_relative_to(prefix)];expected=matches[0] if len(matches)==1 else 'host';need(row['origin']==expected and name in catalogue and file_fact(row)==file_fact(catalogue[name]),'dependency origin/byte snapshot binding')
  if '/Eigen/' in name or '/eigen3/' in name:need(row['origin']=='private' and P(name).is_relative_to(private/'usr/include/eigen3'),'no Eigen fallback')
  if '/Cg/' in name:need(row['origin']=='private' and P(name).is_relative_to(private/'usr/include/Cg'),'no parser-inc/host Cg fallback')
 need(origins=={'source','generated','private','host'} and all(str(private/name) in used_map for name in ('usr/include/eigen3/Eigen/Core','usr/include/Cg/cg.h','usr/include/Cg/cgGL.h')),'genuine Eigen/Cg compiler inputs observed')
 commands=report('compile-dependencies');need(type(commands) is list and 2<=len(commands)<=512 and type(build['compiler_commands']) is int and build['compiler_commands']==len(commands),'actual compiler command count');declared=set();objects=set();layout_seen=0
 for item in commands:
  command=item['command'];need(command[0] in (b.TOOLS['cc'],b.TOOLS['cxx']) and '-c' in command and '-o' in command,'owned dependency compiler command');b.verify_compile(command);obj=absolute(item['object']);need(item['object']==command[command.index('-o')+1] and item['object'] not in objects and digest_ok(item['dependency_sha256']),'unique compiler object/dependency digest');objects.add(item['object'])
  if obj==build_root/'layout-build/layout-contract.o':need(command==layout_cmd,'actual descriptor compile command');layout_seen+=1
  else:need(obj.is_relative_to(sdk) and obj.suffix=='.o','SDK-owned compiler output')
  need(type(item['paths']) is list and 0<len(item['paths'])<=30000,'compiler dependency list');declared.update(resolve(name) for name in item['paths'])
 need(layout_seen==1 and declared==set(used_map),'actual dependency union/used-input equality');need(any('-I'+str(private/'usr/include/eigen3') in item['command'] for item in commands),'explicit private Eigen include');bind_layout(build,root,work,repo,records,parent,descriptor,layout_cmd)
 return dict(records_coherent=True,remote_tools_independently_remeasured=False,remote_host_headers_independently_remeasured=False,native_admitted=False,source_manifest_sha256=BASE_SOURCE_SHA,used_inputs=len(used_map),compiler_commands=len(commands),retained_candidates_bound=4)

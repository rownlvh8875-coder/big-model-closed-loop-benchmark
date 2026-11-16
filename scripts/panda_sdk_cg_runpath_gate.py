"""Actual source-emitted RUNPATH and immutable selected static predicates, DATA only."""
from pathlib import Path
from scripts import build_panda_sdk_cg_runpath as b
from scripts import panda_sdk_cg_eigen_gate as previous
from scripts.panda_sdk_link_elf import inspect_elf
need=b.need;read=b.read;sha=b.sha
SUCCESS='CG_EIGEN_RUNPATH_CANDIDATE_SELECTED_LAYOUT_MATCH_NOT_RUNTIME'
REJECTED='STATIC_CG_EIGEN_RUNPATH_CANDIDATE_REJECTED'
def validate_runpath(candidate,build_panda):
 need(type(candidate) is bytes and 0<len(candidate)<=4*1024**2 and type(build_panda) is bytes and 0<len(build_panda)<=64*1024**2,'bounded retained ELF pair');facts={}
 for name,raw in [('candidate',candidate),('build_panda',build_panda)]:
  meta=inspect_elf(raw);need(meta['rpath'] is None and meta['runpath']=='$ORIGIN','actual '+name+' must emit only exact DT_RUNPATH=$ORIGIN');facts[name+'_runpath']=meta['runpath'];facts[name+'_rpath']=meta['rpath'];facts[name+'_sha256']=sha(raw)
 return facts
def validate_link_facts(build):
 b.contract();need(build.get('schema')=='panda-sdk-cg-runpath-build-v3' and build.get('runpath_contract_sha256')==b.CONTRACT_SHA,'new source-built RUNPATH facts');candidate=Path(build['candidate']);private=candidate.parents[3]/'private';b.validate_environment(build['link_environment'],private);need(set(build['link_commands'])=={'candidate','build_panda'},'both actual link commands')
 for key in ('candidate','build_panda'):b.validate_link_command(build['link_commands'][key],Path(build[key]))
def audit_candidate(candidate,parent,descriptor,build_panda,build,providers):
 result=dict(schema='panda-sdk-cg-runpath-static-gate-v3',status=REJECTED,reasons=[])
 try:
  validate_link_facts(build);facts=validate_runpath(read(candidate,4*1024**2),read(build_panda,64*1024**2));need(all(facts[key+'_sha256']==build[key+'_sha256'] for key in ['candidate','build_panda']),'actual retained ELF pair/compile hashes');base=previous.audit_candidate(candidate,parent,descriptor,build,providers);result.update(base);result.update(schema='panda-sdk-cg-runpath-static-gate-v3',runpath=facts,status=SUCCESS if base['status']=='CG_EIGEN_CANDIDATE_SELECTED_LAYOUT_MATCH_NOT_RUNTIME' else REJECTED)
 except (ValueError,OSError,KeyError,TypeError,IndexError) as error:result['reasons'].append(type(error).__name__+': '+str(error))
 for key in ('full_object_abi_qualified','full_dependency_closure_qualified','runtime_mapping_qualified','previous_abort_fixed','candidate_installed','native_admitted','stage7_complete','external_build_origin_authenticated'):result[key]=False
 return result

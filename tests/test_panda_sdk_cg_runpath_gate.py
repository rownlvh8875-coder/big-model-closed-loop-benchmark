import copy,json,struct,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import panda_sdk_cg_runpath_gate as g
from scripts import panda_sdk_link_image as image
from scripts import panda_sdk_cg_inputs as cg
from tests.test_panda_sdk_cg_runpath_evidence import cpu_elf,success_shaped

class GateTests(unittest.TestCase):
 def test_actual_tags_required_for_both_retained_elfs(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);good=cpu_elf(root);self.assertEqual(g.validate_runpath(good,good)['candidate_runpath'],'$ORIGIN')
   for value,rpath in [('',False),('/tmp',False),('$ORIGIN:/tmp',False),('${ORIGIN}',False),('\\$ORIGIN',False),('$ORIGIN',True)]:
    bad=cpu_elf(root,value,rpath)
    for pair in [(bad,good),(good,bad)]:
     with self.assertRaises(ValueError):g.validate_runpath(*pair)
   # Duplicate a real loader tag in an inert CPU fixture; never load it.
   duplicate=bytearray(good);h=struct.unpack_from('<16sHHIQQQIHHHHHH',good)
   ph=[struct.unpack_from('<IIQQQQQQ',good,h[5]+56*i) for i in range(h[10])];dynamic=next(p for p in ph if p[0]==2);slots=[at for at in range(dynamic[2],dynamic[2]+dynamic[5],16) if struct.unpack_from('<q',good,at)[0] not in (0,29)];struct.pack_into('<q',duplicate,slots[0],29)
   with self.assertRaises(ValueError):g.validate_runpath(bytes(duplicate),good)
 def test_consumed_sdk2_still_rejects_actual_null_tags(self):
  old=cg.ROOT/'output/stage7-panda-sdk-cg-eigen-candidate-02/acceptance/candidate/candidate/libpandagl.so.data'
  if old.exists():
   with self.assertRaises(ValueError):g.validate_runpath(old.read_bytes(),old.read_bytes())
  with tempfile.TemporaryDirectory() as d:
   raw=cpu_elf(Path(d),None)
   with self.assertRaises(ValueError):g.validate_runpath(raw,raw)
 def test_frozen_selector_uses_each_object_own_paths(self):
  inventory=image.Inventory(json.loads((cg.ROOT/cg.INVENTORY).read_text()));c=cg.contract();meta=dict(runpath='$ORIGIN',rpath=None)
  for name,pin in c['image_cg_providers'].items():self.assertEqual(inventory.select(image.LIB,name,meta),pin['image_path'])
  child=c['image_cg_providers']['libCgGL.so']['image_path'];target=c['image_cg_providers']['libCg.so']['image_path'];self.assertEqual(inventory.select(child,'libCg.so',dict(rpath='$ORIGIN',runpath=None)),target)
  with self.assertRaises(ValueError):inventory.select(child,'libCg.so',dict(rpath=None,runpath=None))
  with self.assertRaises(ValueError):inventory.select(image.LIB,'libCg.so',dict(rpath=None,runpath=None))
 def test_selected_success_does_not_promote_provider_diagnostics(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);receipt=success_shaped(root);build=receipt['compiler_build'];paths=[root/'candidate'/n for n in ['libpandagl.so.data','layout-contract.o.data','layout-descriptor.data','build-libpanda.so.data']];diag=dict(root_strong_symbols_available=True,missing=[],weak_unresolved=[dict(name=n) for n in g.previous.WEAK],provider_audits={'Cg':dict(missing=['retained'])});base=dict(status='CG_EIGEN_CANDIDATE_SELECTED_LAYOUT_MATCH_NOT_RUNTIME',provider_audit=diag)
   with patch.object(g.previous,'audit_candidate',return_value=base) as audit:
    result=g.audit_candidate(*paths,build,{});self.assertEqual(result['status'],'CG_EIGEN_RUNPATH_CANDIDATE_SELECTED_LAYOUT_MATCH_NOT_RUNTIME');self.assertEqual(result['provider_audit'],diag);self.assertEqual(audit.call_args.args[-1],{})
   for key in ['full_object_abi_qualified','full_dependency_closure_qualified','runtime_mapping_qualified','previous_abort_fixed','candidate_installed','native_admitted','stage7_complete']:self.assertFalse(result[key])
   paths[-1].write_bytes(cpu_elf(root,'/wrong'));rejected=g.audit_candidate(*paths,build,{});self.assertEqual(rejected['status'],'STATIC_CG_EIGEN_RUNPATH_CANDIDATE_REJECTED')

if __name__=='__main__':unittest.main()

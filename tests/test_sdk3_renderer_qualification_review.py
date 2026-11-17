"""Consumer must reject partial upstream observation receipts, not promote them."""
from pathlib import Path
import copy,json,tempfile,unittest
from unittest.mock import patch
from scripts import run_sdk3_priority_models as h

def fixture(folder):
    folder=Path(folder)
    def write(name,value):
        path=folder/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value))
    nonce='a'*32;library=b'fixture-only-not-an-ELF';(folder/'drawtrace.so.data').write_bytes(library);write('build.json',dict(sha256=h.pins.digest(folder/'drawtrace.so.data')));write('request.json',dict(source_sha=h.RENDERER['source_sha'],repair_id=h.repair.REPAIR_ID,arms=['canary','candidate-off','candidate-trace']));write('summary.json',dict(source_sha=h.RENDERER['source_sha'],status='DRAW_OBSERVATION_RECORDED',official_model_processes=0,onnx_inferences=0,arms={mode:dict(nonce=nonce) for mode in ('canary','candidate-off','candidate-trace')}));write('reference.json',{})
    captures=[dict(step=i,pose={'x':i},road_sha256='a'*64,wide_sha256='b'*64) for i in range(1,8)];reports={}
    for index,mode in enumerate(('candidate-off','candidate-trace')):
        r=dict(mode=mode,renderer_policy_modified=True,renderer_candidate_id=h.repair.REPAIR_ID,seed=20261110,scenario='s_curve_left_right',process_uuid=str(index)*32,reference_sha256='c'*64,captures=captures,pid=42+index);reports[mode]=r;write(mode+'/report.json',r)
    for mode in ('canary','candidate-off','candidate-trace'):
        command=h.renderer.native_command('fixture-'+mode,Path('/repo'),Path('/sdk'),Path('/out'),['--mode',mode,'--nonce',nonce],reference=Path('/reference.json'),library=None if mode=='candidate-off' else Path('/trace.so'));write(mode+'/command.json',dict(argv=command))
    snap=dict(valid=True,restored=True,context=123,draw_fbo=3,read_fbo=3,viewport=[0,0,964,604],color=[.7,.7,0.,1.],depth=.98,depth_bits=24,depth_range=[0.,1.],samples=1,sample_buffers=1,max_samples=1,sample_positions=[.5,.5],depth_func=513,depth_test=1,depth_write=1,scissor_test=1,scissor=[0,0,964,604],gl_error_before=0,gl_error_after=0)
    draws=[dict(sequence=i,phase=1,pixel_gl=[596,109],program=10 if i==1 else 1,restored=True,before=copy.deepcopy(snap),after=copy.deepcopy(snap),depth_probe=None,uniforms={'attribute':{},'heightfield':{}} if i==1 else {},terrain_data_row={'status':'ROW_RECORDED'} if i==1 else None,transform_table=None if i==1 else {'status':'MATRICES_RECORDED','count':1,'nbytes':64}) for i in (1,2)]
    canary=dict(priority_tie_canary_qualified=True,one_pixel_depth_probe_qualified=True,terrain_row_read_qualified=True,max_effective_samples_observed=1)
    analysis=dict(trace_complete=True,draw_count=2,trace_stats=dict(error=0,restored=1,active=0,complete=True,draws=2),callback_receipt=dict(target_region_entries=2,target_region_returns=2,errors=[],callbacks_restored=True,trace_complete=True),terrain_rows_complete=True,terrain_row_count=1,transform_matrix_bytes=64,target_road_rgb=[199,187,0])
    off=dict(trace_complete=True,target_road_rgb=[199,187,0]);gate=h.renderer.candidate_repeat_gate(reports['candidate-off'],reports['candidate-trace'],draws,off['target_road_rgb'],analysis['target_road_rgb']);assert gate['passed'];write('candidate-repeat-verdict.json',gate);return canary,off,analysis,draws

class RendererQualificationReview(unittest.TestCase):
    def invoke(self,folder,values):
        canary,off,analysis,draws=values
        with patch.object(h.renderer,'validate_receipt',side_effect=[canary,off,analysis]),patch.object(h.renderer,'read_trace',return_value=(draws,{})):
            return h.validate_renderer_bundle(folder)
    def test_complete_original_receipt_is_accepted(self):
        with tempfile.TemporaryDirectory() as d:self.assertTrue(self.invoke(d,fixture(d))['gate']['passed'])
    def test_partial_invalid_and_sample_unqualified_observations_never_qualify(self):
        for case in ('counter_error','counter_incomplete','callback_partial','invalid_snapshot','unrestored_snapshot','row_partial','matrix_partial','unqualified_samples','nonfinite_color','clipped_resolve','gl_error','missing_context'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as d:
                values=fixture(d);canary,off,a,draws=values
                if case=='counter_error':a['trace_stats']['error']=3;a['trace_complete']=False
                elif case=='counter_incomplete':a['trace_stats']['complete']=False
                elif case=='callback_partial':a['callback_receipt'].update(target_region_returns=1,errors=['callback failure'],trace_complete=False)
                elif case=='invalid_snapshot':draws[0]['after']['valid']=False
                elif case=='unrestored_snapshot':draws[0]['before']['restored']=False
                elif case=='row_partial':draws[0]['terrain_data_row']['status']='ROW_PARTIAL'
                elif case=='matrix_partial':draws[1]['transform_table']['status']='MATRICES_PARTIAL'
                elif case=='unqualified_samples':draws[0]['before']['samples']=4
                elif case=='nonfinite_color':draws[0]['before']['color'][0]=float('nan')
                elif case=='clipped_resolve':draws[0]['before']['scissor']=[2,2,600,600]
                elif case=='gl_error':draws[0]['after']['gl_error_after']=1282
                elif case=='missing_context':draws[0]['before']['context']=0
                with self.assertRaises(ValueError):self.invoke(d,values)
if __name__=='__main__':unittest.main()

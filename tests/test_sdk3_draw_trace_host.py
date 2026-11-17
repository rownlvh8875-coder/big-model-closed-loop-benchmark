from pathlib import Path
import copy,hashlib,json,subprocess,sys,tempfile,unittest,struct
try:from scripts import run_sdk3_draw_trace as h
except ImportError:h=None
from scripts import panda_sdk3_runtime as p

def report(mode='trace'):
    return dict(intentional_target_depth_mutation=mode=='depth-probe',protocol='sdk3-draw-trace-native-v1',pid=123,nonce='a'*32,mode=mode,core_sha256=p.CORE_SHA,sdk_sha256=p.SDK_SHA,panda_version='1.10.13',driver=dict(renderer='softpipe'),official_model_processes=0,onnx_inferences=0,model_weights_used=False,repair_proven=False,stage7_complete=False,provider_closed=True,trace_library_sha256='b'*64 if mode!='off' else None,observer_is_intervention=mode!='off',source_stats_before={k:0 for k in p.STATS_FIELDS},source_stats_after={k:0 for k in p.STATS_FIELDS},trace_stats=dict(version=1,error=0,active=0,restored=1,lookups=10,forwards=20,draws=2,queries=500,readbacks=8,blits=0) if mode!='off' else dict(version=1,error=0,active=0,restored=1,lookups=0,forwards=0,draws=0,queries=0,readbacks=0,blits=0))
class HostContracts(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(h,'authenticated draw host missing')
    def test_report_qualified_observer_counts_are_not_zeroed(self):
        r=h.validate_report(report(),'a'*32,'trace','b'*64);self.assertEqual(r['queries'],500);self.assertTrue(r['complete'])
    def test_identity_scope_core_source_stats_and_claims_rejected(self):
        for key,value in [('nonce','x'),('pid',True),('sdk_sha256','c'*64),('core_sha256','c'*64),('official_model_processes',1),('onnx_inferences',1),('model_weights_used',True),('repair_proven',True),('stage7_complete',True),('source_stats_after',dict(configured=1)),('observer_is_intervention',False)]:
            r=report();r[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):h.validate_report(r,'a'*32,'trace','b'*64)
    def test_caps_and_counter_forgery_rejected(self):
        for key,value in [('queries',100001),('draws',513),('readbacks',2049),('active',1),('restored',0),('queries',True)]:
            r=report();r['trace_stats'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):h.validate_report(r,'a'*32,'trace','b'*64)
    def test_partial_error_is_retained_not_qualified(self):
        r=report();r['trace_stats']['error']=4;self.assertFalse(h.validate_report(r,'a'*32,'trace','b'*64)['complete'])
    def test_off_cannot_hide_an_observer(self):
        self.assertTrue(h.validate_report(report('off'),'a'*32,'off',None)['complete']);r=report('off');r['trace_stats']['queries']=1
        with self.assertRaises(ValueError):h.validate_report(r,'a'*32,'off',None)
    def test_off_and_on_commands_are_fixed_and_old_builder_unchanged(self):
        args=['--mode','trace','--nonce','a'*32,'--trace-library','/drawtrace.so','--trace-sha256','b'*64]
        cmd=h.native_command('fresh',Path('/repo'),Path('/sdk'),Path('/out'),args,reference=Path('/ref'),owner='c'*32,library=Path('/helper.so'))
        self.assertIn('LD_PRELOAD=/drawtrace.so',cmd);self.assertIn(h.ENTRY,cmd);self.assertNotIn('LD_DEBUG=bindings,versions',cmd);self.assertIn('10g',cmd)
        off=h.native_command('fresh',Path('/repo'),Path('/sdk'),Path('/out'),['--mode','off','--nonce','a'*32],reference=Path('/ref'),owner='c'*32,library=None)
        self.assertFalse(any('drawtrace.so' in x or 'LD_PRELOAD' in x for x in off))
    def test_command_receiver_rejects_extra_env_or_entry_or_rw_library(self):
        args=['--mode','trace','--nonce','a'*32,'--trace-library','/drawtrace.so','--trace-sha256','b'*64];kw=dict(reference=Path('/ref'),owner='c'*32,library=Path('/helper.so'));cmd=h.native_command('fresh',Path('/repo'),Path('/sdk'),Path('/out'),args,**kw)
        spec=dict(name='fresh',repo='/repo',sdk='/sdk',out='/out',args=args,reference='/ref',owner='c'*32,library='/helper.so');h.validate_command(cmd,spec)
        for kind in ('env','entry','rw'):
            bad=list(cmd)
            if kind=='env':bad[2:2]=['--env','EXTRA=1']
            elif kind=='entry':bad[bad.index(h.ENTRY)]='/wrong.py'
            else:bad=[v.replace('dst=/drawtrace.so,readonly','dst=/drawtrace.so') for v in bad]
            with self.subTest(kind=kind),self.assertRaises(ValueError):h.validate_command(bad,spec)
    def test_trace_missing_truncated_or_wrong_pid_never_complete(self):
        with tempfile.TemporaryDirectory() as d:
            q=Path(d)/'draw-trace.jsonl'
            for raw in (b'',b'{}',b'{"event":"configured","pid":124,"max_draws":512}\n'):
                q.write_bytes(raw)
                with self.subTest(raw=raw),self.assertRaises(ValueError):h.read_trace(Path(d),123)
    def test_source_activation_rejects_modified_historical_producer(self):
        with self.assertRaises(ValueError):h.validate_source_delta(['M\tscripts/panda_sdk3_runtime.py'])
        h.validate_source_delta(['A\tscripts/new.py'])
    def check_canary(self,sample_count=4):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);r=report('canary');r.update(status='TINY_GPU_CANARY_RECORDED',canary_render_calls=8,canary_cases=[]);rows=[dict(event='configured',pid=123,max_draws=512)]
            for phase in (0,1):
                case=dict(requested_samples=phase*4,callback_receipt=dict(trace_complete=True,target_region_returns=4,callbacks_restored=True,errors=[]),challenges=[])
                for challenge,color in enumerate(([1.,0.,0.],[0.,1.,1.])):
                    name=f'canary-{phase}-{challenge}.rgba';raw=bytes([int(v*255) for v in [*color,1.]])*64;(folder/name).write_bytes(raw);start=len(rows)
                    for _ in range(2):
                        snap=dict(valid=True,restored=True,gl_error_before=0,gl_error_after=0,samples=phase*sample_count,sample_buffers=phase,max_samples=4,depth_bits=24,color=[*color,1.]);rows.append(dict(event='draw',pid=123,sequence=len(rows),phase=phase,pixel_gl=[3,3],kind=2 if phase==0 else 5,restored=True,before=snap,after=snap))
                    case['challenges'].append(dict(color=color,raw_file=name,nbytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),component_width=1,component_type=0,draw_range=[start,len(rows)-1]))
                r['canary_cases'].append(case)
            (folder/'draw-trace.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows));stats=dict(complete=True,draws=8,queries=1000,blits=8,readbacks=32)
            result=h.validate_canary(folder,r,stats);self.assertEqual(result['status'],'QUALIFIED_TINY_GPU_CANARY');self.assertEqual(result['multiple_effective_samples_qualified'],sample_count>1)
            rows[-1]['after']=dict(rows[-1]['after'],gl_error_after=1282);(folder/'draw-trace.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
            with self.assertRaises(ValueError):h.validate_canary(folder,r,stats)
    def test_actual_c_schema_canary_decodes_bytes_and_requires_both_draw_kinds(self):self.check_canary()
    def test_one_effective_sample_resolve_never_claims_multiple_sample_qualification(self):self.check_canary(1)
    def terrain_draw(self):
        values=[0.,2.,1.,.5]*2;bits=list(struct.unpack('<8I',struct.pack('<8f',*values)));return dict(sequence=1,phase=1,instances=2,pixel_gl=[596,109],uniforms=dict(terrain_data_texture=dict(texture=55,unit=3,width=8,height=8,internal_format=34836,restored=True),terrain_view_index=2),terrain_data_row=dict(status='ROW_RECORDED',texture=55,unit=3,texture_size=[8,8],internal_format=34836,view_index=2,width=2,nbytes=32,restored=True,gl_error_before=0,gl_error_after=0,values=values,float_bits=bits),depth_probe=None)
    def test_terrain_row_bytes_bind_to_current_sampler_view_and_float_bits(self):
        d=self.terrain_draw();r=h.validate_trace_details([d],'trace',[596,109]);self.assertEqual(r['terrain_row_bytes'],32);self.assertTrue(r['terrain_rows_complete'])
        for name in ('view_index','texture','nbytes','float_bits'):
            x=copy.deepcopy(d);x['terrain_data_row'][name]=[0]*8 if name=='float_bits' else 999
            with self.subTest(name=name),self.assertRaises(ValueError):h.validate_trace_details([x],'trace',[596,109])
    def test_extra_rows_or_undisclosed_pixel_mutation_never_qualify(self):
        d=self.terrain_draw()
        with self.assertRaises(ValueError):h.validate_trace_details([d,d,d],'trace',[596,109])
        d['depth_probe']=dict(cleared_pixels=1,state_restored=True,original_depth_bits32=[1])
        with self.assertRaises(ValueError):h.validate_trace_details([d],'trace',[596,109])
    def test_depth_probe_requires_one_scoped_mutation_and_preserves_original_depth_state(self):
        d=self.terrain_draw();base=dict(valid=True,depth_test=1,depth_write=1,depth_func=513,scissor=[0,0,964,604],scissor_test=0,depth_bits32=[1056964608],color_bits=[1,2,3,4]);d['before']=base;d['after']=dict(base,depth_bits32=[1058642330],color_bits=[5,6,7,8]);d['depth_probe']=dict(cleared_pixels=1,state_restored=True,original_depth_bits32=base['depth_bits32']);r=h.validate_trace_details([d],'depth-probe',[596,109]);self.assertEqual(r['depth_clear_pixels'],1);self.assertTrue(r['occluded_terrain_exposed'])
        for key,value in [('cleared_pixels',2),('state_restored',False),('original_depth_bits32',[0])]:
            x=copy.deepcopy(d);x['depth_probe'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):h.validate_trace_details([x],'depth-probe',[596,109])
        with self.assertRaises(ValueError):h.validate_trace_details([],'depth-probe',[596,109])
    def test_matrix_arrays_keep_declared_bound_bytes_and_finite_float_bits(self):
        d=self.terrain_draw();d['transform_table']=dict(status='MATRICES_RECORDED',uniform='p3d_TransformTable',count=2,nbytes=128,float_bits=[0]*32,gl_error_before=0,gl_error_after=0);r=h.validate_trace_details([d],'trace',[596,109]);self.assertEqual(r['transform_matrix_bytes'],128)
        for field,value in [('count',101),('nbytes',64),('float_bits',[0x7fc00000]*32)]:
            x=copy.deepcopy(d);x['transform_table'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):h.validate_trace_details([x],'trace',[596,109])
    def test_cold_host_help(self):
        r=subprocess.run([sys.executable,'-I','-B',h.__file__,'--help'],capture_output=True,text=True,timeout=15);self.assertEqual(r.returncode,0,r.stderr)
if __name__=='__main__':unittest.main()

from pathlib import Path
import copy,hashlib,json,subprocess,sys,tempfile,unittest
try:from scripts import run_sdk3_draw_trace as h
except ImportError:h=None
from scripts import panda_sdk3_runtime as p

def report(mode='trace'):
    return dict(protocol='sdk3-draw-trace-native-v1',pid=123,nonce='a'*32,mode=mode,core_sha256=p.CORE_SHA,sdk_sha256=p.SDK_SHA,panda_version='1.10.13',driver=dict(renderer='softpipe'),official_model_processes=0,onnx_inferences=0,model_weights_used=False,repair_proven=False,stage7_complete=False,provider_closed=True,trace_library_sha256='b'*64 if mode!='off' else None,observer_is_intervention=mode!='off',source_stats_before={k:0 for k in p.STATS_FIELDS},source_stats_after={k:0 for k in p.STATS_FIELDS},trace_stats=dict(version=1,error=0,active=0,restored=1,lookups=10,forwards=20,draws=2,queries=500,readbacks=8,blits=0) if mode!='off' else dict(version=1,error=0,active=0,restored=1,lookups=0,forwards=0,draws=0,queries=0,readbacks=0,blits=0))
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
    def test_actual_c_schema_canary_decodes_bytes_and_requires_both_draw_kinds(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);r=report('canary');r.update(status='TINY_GPU_CANARY_RECORDED',canary_render_calls=8,canary_cases=[]);rows=[dict(event='configured',pid=123,max_draws=512)]
            for phase in (0,1):
                case=dict(requested_samples=phase*4,callback_receipt=dict(trace_complete=True,target_region_returns=4,callbacks_restored=True,errors=[]),challenges=[])
                for challenge,color in enumerate(([1.,0.,0.],[0.,1.,1.])):
                    name=f'canary-{phase}-{challenge}.rgba';raw=bytes([int(v*255) for v in [*color,1.]])*64;(folder/name).write_bytes(raw);start=len(rows)
                    for _ in range(2):
                        snap=dict(valid=True,restored=True,gl_error_before=0,gl_error_after=0,samples=phase*4,depth_bits=24,color=[*color,1.]);rows.append(dict(event='draw',pid=123,sequence=len(rows),phase=phase,pixel_gl=[3,3],kind=2 if phase==0 else 5,restored=True,before=snap,after=snap))
                    case['challenges'].append(dict(color=color,raw_file=name,nbytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),component_width=1,component_type=0,draw_range=[start,len(rows)-1]))
                r['canary_cases'].append(case)
            (folder/'draw-trace.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows));stats=dict(complete=True,draws=8,queries=1000,blits=8,readbacks=32)
            self.assertEqual(h.validate_canary(folder,r,stats)['status'],'QUALIFIED_TINY_GPU_CANARY')
            rows[-1]['after']=dict(rows[-1]['after'],gl_error_after=1282);(folder/'draw-trace.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
            with self.assertRaises(ValueError):h.validate_canary(folder,r,stats)
    def test_cold_host_help(self):
        r=subprocess.run([sys.executable,'-I','-B',h.__file__,'--help'],capture_output=True,text=True,timeout=15);self.assertEqual(r.returncode,0,r.stderr)
if __name__=='__main__':unittest.main()

"""Fresh GPU canary or seven-pose control/actual-draw trace, never a model run."""
from contextlib import contextmanager
from pathlib import Path
from types import FunctionType,SimpleNamespace
import argparse,ctypes,hashlib,json,os,sys,time,uuid,zlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import sdk3_draw_trace as t,panda_sdk3_runtime as p,panda_sdk3_diagnostic as owner
from scripts.sdk3_capture_progress import Journal,observe,stack_watchdog,wait_observed
BASE_CAMERA_SHA='23d90c3d12894f855ae64d4607c03f3bf34e31e28dd7f5ce82bd0ddc7b37faf5'

def clone(function,**changes):
    value=FunctionType(function.__code__,dict(function.__globals__,**changes),function.__name__,function.__defaults__,function.__closure__);value.__kwdefaults__=dict(function.__kwdefaults__ or {});return value

def owned_child_command(args,parent_pid):
    command=[sys.executable,'-I','-S','-B',str(Path(__file__).resolve()),'--owned-child','--server-owner',str(parent_pid),'--out',args.out,'--nonce',args.nonce,'--mode',args.mode]
    if getattr(args,'trace_sha256',None):command+=['--trace-library',str(args.trace_library),'--trace-sha256',args.trace_sha256]
    return command

def run_with_server(args):
    def wait(child,server,legacy_timeout):return wait_observed(child,server,90 if args.mode=='canary' else 600,Path(args.out))
    return clone(owner.run_with_server,owned_child_command=owned_child_command,wait_child_then_stop_server=wait)(args)

def bootstrap(report):
    sys.path.insert(0,p.SITE)
    import numpy as np
    import panda3d.core as core
    report.update(core_sha256=p.digest(core.__file__),panda_version=core.PandaSystem.getVersionString());preload=ctypes.CDLL(p.SITE+'/panda3d/libpanda.so.1.10',mode=os.RTLD_NOW|os.RTLD_GLOBAL);sdk=ctypes.CDLL(p.SDK_PATH,mode=os.RTLD_NOW|os.RTLD_LOCAL)
    report['sdk_sha256']=p.digest(p.SDK_PATH);p.need(report['sdk_sha256']==p.SDK_SHA and report['core_sha256']==p.CORE_SHA,'actual immutable SDK/core');return core,sdk,np,preload

def sdk_stats(sdk):
    class Source(ctypes.Structure):_fields_=[(k,ctypes.c_uint32) for k in ('configured','closed','error')]+[(k,ctypes.c_uint64) for k in ('forwarded','resolutions','paths','events')]
    function=sdk.psd_get_stats;function.argtypes=[ctypes.POINTER(Source)];function.restype=ctypes.c_int;value=Source();p.need(function(ctypes.byref(value))==0,'original SDK default-OFF stats');return {k:int(getattr(value,k)) for k,_ in value._fields_}

def new_trace(args,report):
    p.need(os.environ.get('LD_PRELOAD')==str(args.trace_library),'exact explicit diagnostic preload');value=t.Trace(args.trace_library,Path(args.out),args.trace_sha256);report.update(trace_library_sha256=args.trace_sha256,observer_is_intervention=True);return value

def regions(sensor):
    manager=sensor.manager;buffers=manager.buffers;p.need(isinstance(buffers,list) and len(buffers)<=4,'existing bounded filter buffers');found=[]
    for buffer in buffers:
        for i in range(buffer.getNumDisplayRegions()):
            region=buffer.getDisplayRegion(i)
            if region.isActive() and region.getCamera()==sensor.cam:found.append((buffer,region))
    p.need(len(found)==1 and manager.region.isActive(),'unique original Road HDR and post regions');buffer,scene=found[0];post=manager.region;p.need(scene!=post and post.getCamera()!=sensor.cam,'original distinct HDR/post cameras')
    metadata=[dict(phase=phase,region_pointer=int(region.this),buffer_pointer=int(win.this),gsg_pointer=int(win.getGsg().this),camera_pointer=int(region.getCamera().node().this),framebuffer=str(win.getFbProperties()),size=[win.getXSize(),win.getYSize()]) for phase,win,region in [(1,buffer,scene),(2,sensor.buffer,post)]]
    return [(1,scene),(2,post)],metadata

def scene_metadata(phase,data):
    setup=data.getSceneSetup();p.need(setup is not None,'draw callback scene setup')
    matrix=lambda transform:[float(transform.getMat().getCell(row,col)) for row in range(4) for col in range(4)]
    return dict(scene_setup_pointer=int(setup.this),region_pointer=int(setup.getDisplayRegion().this),camera_node_pointer=int(setup.getCameraNode().this),scene_root=str(setup.getSceneRoot()),camera_path=str(setup.getCameraPath()),camera_transform=matrix(setup.getCameraTransform()),world_transform=matrix(setup.getWorldTransform()),viewport=[setup.getViewportWidth(),setup.getViewportHeight()],transform_layout='row-major Panda matrix',recorded_thread_id=__import__('threading').get_ident())

def replay(args,report):
    out=Path(args.out);provider=None;tracer=None;journal=Journal(out,dict(pid=os.getpid(),nonce=args.nonce,protocol='sdk3-draw-trace-native-v1'))
    try:
        core,sdk,np,preload=bootstrap(report);report['source_stats_before']=sdk_stats(sdk);reference=json.loads(Path('/reference.json').read_text());report['reference_sha256']=p.digest('/reference.json')
        from bigbench.metadrive_camera import NativeMetaDriveProvider
        from bigbench.native_model_campaign import NativeWorldCamera
        from bigbench.curved_lane_scenarios import SCENARIOS,select_native_curve_lanes
        from bigbench.kinematics import AgentState
        import metadrive.component.sensors.base_camera as camera_module
        report['base_camera_sha256']=p.digest(camera_module.__file__);p.need(report['base_camera_sha256']==BASE_CAMERA_SHA,'same original BaseCamera')
        provider=NativeMetaDriveProvider(seed=20261110,map_config=SCENARIOS['s_curve_left_right'].map_config());engine=provider.env.engine;lane=select_native_curve_lanes(provider.env.current_map,SCENARIOS['s_curve_left_right'])[0];distance=float(lane.length)*.12;xy=lane.position(distance,0.);initial=dict(t=0.,x=float(xy[0]),y=float(xy[1]),heading=float(lane.heading_theta_at(distance)),speed=8.);poses=[initial,*reference['previous_states']]
        class RGB:
            def __init__(self):self.count=0;self.images=[]
            def record_native_rgb(self,images,hashes):
                self.count+=1;self.images=[]
                for camera in ('road','wide'):
                    rgb=images[camera];raw=rgb.tobytes(order='C');p.need(hashlib.sha256(raw).hexdigest()==hashes[camera],'original immediate copied pixels');packed=zlib.compress(raw,6);name=f'step{self.count}-{camera}.rgb.zlib';(out/name).write_bytes(packed);self.images.append(dict(camera=camera,file=name,shape=list(rgb.shape),sha256=hashes[camera],raw_bytes=len(raw),compressed_bytes=len(packed)))
        recorder=RGB();capture=NativeWorldCamera(provider,raw_rgb_observer=recorder);sensor=engine.sensors['bigbench_road'];gsg=sensor.buffer.getGsg();report['driver']=dict(vendor=gsg.getDriverVendor(),renderer=gsg.getDriverRenderer(),version=gsg.getDriverVersion());clock=core.ClockObject.getGlobalClock();before=clock.getFrameCount();tasks=lambda:sorted(task.getName() for task in engine.taskMgr.getTasks());report['tasks_before']=tasks();receipt={};pairs=[];report['regions']=[]
        if args.mode=='trace':tracer=new_trace(args,report);pairs,report['regions']=regions(sensor)
        else:p.need(not os.environ.get('LD_PRELOAD'),'OFFcontrol has no preloaded observer');report.update(observer_is_intervention=False,trace_library_sha256=None)
        saved=[(obj,name,getattr(obj,name),name in vars(obj)) for obj,name in [(capture,'capture'),(engine.taskMgr,'step')]+[(engine.sensors['bigbench_'+kind],name) for kind in ('road','wide') for name in ('perceive','get_rgb_array_cpu')]]
        with observe(capture,journal):
            with t.scoped_callbacks(pairs,journal,tracer,t.pixel_gl(964,604,596,494),make_callback=core.CallbackObject.make,receipt=receipt,enabled=tracer is not None,scene_metadata=scene_metadata):
                for index,pose in enumerate(poses,1):
                    report['active_step']=index;journal.emit('checkpoint',stage='CAPTURE_ENTER');capture.capture(AgentState(**pose));hashes=capture.last_source_rgb_sha256;report['captures'].append(dict(step=index,pose=pose,road_sha256=hashes['road'],wide_sha256=hashes['wide'],images=recorder.images,task_frame_count_delta=clock.getFrameCount()-before));p.write(out/'report.json',report);journal.emit('checkpoint',stage='CAPTURE_RETURN')
                if tracer is not None:engine.graphicsEngine.syncFrame();report['terminal_sync_calls']=1
        report.update(callback_receipt=receipt,observers_restored=receipt['callbacks_restored'] and all(getattr(obj,name)==value and (name in vars(obj))==owned for obj,name,value,owned in saved),tasks_after=tasks(),task_frame_count_delta=clock.getFrameCount()-before,source_stats_after=sdk_stats(sdk),ort_module_loaded=any(k=='onnxruntime' or k.startswith('onnxruntime.') for k in sys.modules),extra_render_tasks=0,terminal_sync_calls=report.get('terminal_sync_calls',0))
        report['trace_stats']=tracer.close() if tracer else dict(version=1,error=0,active=0,restored=1,lookups=0,forwards=0,draws=0,queries=0,readbacks=0,blits=0);report['extra_gpu_queries']=report['trace_stats']['queries'];report['status']='DRAW_TRACE_REPLAY_RECORDED';return report
    finally:
        if tracer is not None:report['trace_stats']=tracer.close();report['extra_gpu_queries']=report['trace_stats']['queries']
        if provider is not None:
            try:provider.close();report['provider_closed']=True
            except BaseException as exc:report['close_failure']=type(exc).__name__+': '+str(exc)
        journal.emit('checkpoint',stage='CHILD_FINAL_REPORT');journal.close()

def canary(args,report):
    out=Path(args.out);base=None;tracer=None;buffers=[]
    try:
        core,sdk,np,preload=bootstrap(report);report['source_stats_before']=sdk_stats(sdk);core.loadPrcFileData('sdk3-draw-tiny','load-display pandagl\nwindow-type offscreen\nwin-size 8 8\nframebuffer-multisample false\nmultisamples 0\nframebuffer-srgb false\nsync-video false\nthreading-model\naudio-library-name null\nnotify-level warning\n')
        from direct.showbase.ShowBase import ShowBase
        base=ShowBase(windowType='offscreen');p.need(base.win is not None,'tiny canary host');tracer=new_trace(args,report);gsg=base.win.getGsg();report['driver']=dict(vendor=gsg.getDriverVendor(),renderer=gsg.getDriverRenderer(),version=gsg.getDriverVersion());report['canary_cases']=[];report['canary_render_calls']=0
        first=[1.,float(int(args.nonce[0],16)&1),0.];challenges=[first,[1.-v for v in first]]
        vertex='#version 330\nuniform mat4 p3d_ModelViewProjectionMatrix;in vec4 p3d_Vertex;void main(){gl_Position=p3d_ModelViewProjectionMatrix*p3d_Vertex;}\n';fragment='#version 330\nuniform vec3 diagnostic_rgb;out vec4 color;void main(){color=vec4(diagnostic_rgb,1);}\n';shader=core.Shader.make(core.Shader.SL_GLSL,vertex=vertex,fragment=fragment)
        for phase,samples in [(0,0),(1,4)]:
            fb=core.FrameBufferProperties();fb.setRgbColor(True);fb.setFloatColor(True);fb.setRgbaBits(16,16,16,16);fb.setDepthBits(24);fb.setMultisamples(samples);buffer=base.win.makeTextureBuffer('sdk3-tiny-'+str(samples),8,8,fbp=fb);p.need(buffer is not None,'tiny float framebuffer');buffers.append(buffer);buffer.setClearColorActive(True);buffer.setClearDepthActive(True);buffer.setClearColor((0,0,0,1));buffer.setClearDepth(1.)
            root=core.NodePath('sdk3-tiny-scene');card=core.CardMaker('sdk3-tiny-card');card.setFrame(-1,1,-1,1);quad=root.attachNewNode(card.generate());quad.setShader(shader);quad.setInstanceCount(1 if samples==0 else 2);camera=core.Camera('sdk3-tiny-camera');camera.setScene(root);lens=core.OrthographicLens();lens.setFilmSize(2,2);lens.setNearFar(.1,10);camera.setLens(lens);cam=root.attachNewNode(camera);cam.setPos(0,-2,0);region=buffer.makeDisplayRegion();region.setCamera(cam);region.setClearColorActive(True);region.setClearDepthActive(True);texture=core.Texture('sdk3-tiny-ram');texture.setFormat(core.Texture.F_rgba16);texture.setComponentType(core.Texture.TFloat);buffer.addRenderTexture(texture,core.GraphicsOutput.RTMCopyRam);receipt={};case=dict(phase=phase,requested_samples=samples,framebuffer=str(buffer.getFbProperties()),challenges=[])
            with t.scoped_callbacks([(phase,region)],SimpleNamespace(step=1,camera='road'),tracer,(3,3),make_callback=core.CallbackObject.make,receipt=receipt,target_step=1,expected_returns=4):
                for index,color in enumerate(challenges):
                    quad.setShaderInput('diagnostic_rgb',core.Vec3(*color));start=tracer.stats()['draws']
                    for _ in range(2):base.graphicsEngine.renderFrame();base.graphicsEngine.syncFrame();report['canary_render_calls']+=1
                    p.need(texture.hasRamImage() and texture.getXSize()==texture.getYSize()==8,'tiny RAM copy');raw=bytes(texture.getRamImageAs('RGBA'));width=texture.getComponentWidth();typ=texture.getComponentType();p.need(len(raw)==64*4*width<=8192,'bounded8x8RGBAcanary');dtype=np.dtype('float32') if typ==core.Texture.TFloat and width==4 else np.dtype('float16') if typ==core.Texture.THalfFloat and width==2 else np.dtype('uint8') if typ==core.Texture.TUnsignedByte and width==1 else None;p.need(dtype is not None,'explicit canary component layout');pixels=np.frombuffer(raw,dtype=dtype).reshape((64,4));expected=np.array([*color,1.])*(255 if width==1 else 1);p.need(np.array_equal(pixels,np.broadcast_to(expected,pixels.shape)),'exact all64 challenged pixel values');name=f'canary-{phase}-{index}.rgba';(out/name).write_bytes(raw);case['challenges'].append(dict(color=color,draw_range=[start+1,tracer.stats()['draws']],raw_file=name,nbytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),component_width=width,component_type=int(typ),all64_exact=True))
            case['callback_receipt']=receipt;report['canary_cases'].append(case);buffer.setActive(False);region.clearDrawCallback();root.removeNode()
        report.update(trace_stats=tracer.close(),source_stats_after=sdk_stats(sdk),provider_closed=True,status='TINY_GPU_CANARY_RECORDED');return report
    finally:
        if tracer is not None:report['trace_stats']=tracer.close()
        if base is not None:
            for buffer in buffers:buffer.clearRenderTextures();base.graphicsEngine.removeWindow(buffer)
            base.destroy();report['provider_closed']=True

def run_native(args):
    report=dict(protocol='sdk3-draw-trace-native-v1',status='INCOMPLETE',pid=os.getpid(),process_uuid=uuid.uuid4().hex,nonce=args.nonce,mode=args.mode,seed=20261110,scenario='s_curve_left_right',captures=[],official_model_processes=0,onnx_inferences=0,model_weights_used=False,repair_proven=False,stage7_complete=False,provider_closed=False,gpu_pixel_owner_proven=False,unique_cause_proven=False)
    try:p.need(args.server_owner==os.getppid(),'owned native/display parent');return canary(args,report) if args.mode=='canary' else replay(args,report)
    except BaseException as exc:report['failure']=type(exc).__name__+': '+str(exc);raise
    finally:p.write(Path(args.out)/'report.json',report)

def main():
    import faulthandler;faulthandler.enable();parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);parser.add_argument('--nonce',required=True);parser.add_argument('--mode',choices=('canary','off','trace'),required=True);parser.add_argument('--trace-library',type=Path,default=Path('/drawtrace.so'));parser.add_argument('--trace-sha256');parser.add_argument('--owned-child',action='store_true');parser.add_argument('--server-owner',type=int);args=parser.parse_args();args.model_trial=False
    if args.owned_child:
        with stack_watchdog(Path(args.out)/'stacks.log'):run_native(args)
        return 0
    return 0 if run_with_server(args)==0 else 1
if __name__=='__main__':raise SystemExit(main())

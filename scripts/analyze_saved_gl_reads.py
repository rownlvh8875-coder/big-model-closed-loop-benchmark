"""Offline command routes in the retained apitrace v2 cohort, not new native proof."""
import argparse
from collections import Counter
from datetime import datetime,timezone,timedelta
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter,process_time

from scripts import gl_read_provenance as provenance
from scripts import gl_trace_reader as reader

NATIVE_SHA={'off_0':'49311317638676df5226931effd5c157c3cffee4869566f4fd383e6fef642e69',
    'on_0':'9af3cae862da26b5be53a4200357f9901cb3b5c86c776bb772d75da03028d05a',
    'on_1':'818836fb5d3c0c411180da15abbbdd963475b97fc848315f3449506c1f92a856',
    'off_1':'7022aeee3ae76dbe2334fa4017e95b9952a43b4be2f0c823d1457128a08e1351'}

def _route_key(route,nodes):
    resolved=nodes[route['resolve_call']]
    # Scissor affects blits; masks/depth-test/blending are not simulated.
    scissor={k:v for k,v in resolved['state'].items() if k in ('cap:3089','glScissor','glScissorArrayv')}
    return dict(rgb_program=route['rgb_program'],texture_name=route['texture_name'],
        resolve_read_fbo=route['resolve_read_fbo'],resolve_draw_fbo=route['resolve_draw_fbo'],
        msaa_descriptor=route['msaa_descriptor'],samples=route['samples'],resolve_args=route['resolve_args'],recorded_scissor=scissor)

def compare_reports(left,right):
    if len(left['reads'])!=len(right['reads']):raise ValueError('read ordinals cannot align across unequal counts')
    nodes=[{n['id']:n for n in report['nodes']} for report in (left,right)];rows=[]
    for i,(a,b) in enumerate(zip(left['reads'],right['reads'])):
        markers_equal=a['markers']==b['markers'];same=None
        keys=[[_route_key(r,nodes[j]) for r in read['routes']] for j,read in enumerate((a,b))]
        if markers_equal and keys[0] and keys[1]:same=keys[0]==keys[1]
        rows.append(dict(read_ordinal=i,calls=[a['call'],b['call']],read_fbos=[a['read_fbo'],b['read_fbo']],
            markers=[a['markers'],b['markers']],marker_names_equal=markers_equal,same_route_topology=same,
            route_keys=keys,returned_pixels_observed=False))
    return dict(schema='gl-read-route-comparison-v1',status='RECORDED_ROUTE_TOPOLOGY_COMPARED',reads=rows,
        pixel_equality_proven=False,sealed_frame_association_proven=False,gpu_completion_proven=False,
        limitation='Only recorded route topology/selected storage and scissor metadata. Equal routes do not imply equal source draws, uniform/raster state, generated pixels or a shared GPU frame.')

def _json(path):
    path=reader._regular(path,2*1024**2);raw=path.read_bytes();return json.loads(raw),dict(path=path.name,nbytes=len(raw),sha256=sha256(raw).hexdigest())

def _inputs(root):
    receipts,receipt_file=_json(root/'execution_receipts.json');plan,plan_file=_json(root/'plan.json')
    if type(receipts) is not list or [r.get('label') for r in receipts]!=['off_0','on_0','on_1','off_1']:
        raise ValueError('original complete ABBA receipt set required')
    files=[receipt_file,plan_file];native={}
    for row in receipts:
        label=row['label'];d,meta=_json(root/(label+'.json'));files.append(meta)
        if (meta['sha256']!=NATIVE_SHA[label] or meta['sha256']!=row['native_json_sha256'] or row['raw_status']!=0 or
            row['trace_enabled'] is not label.startswith('on_') or d['status']!='OBSERVED_NATIVE_PIXEL_CLOCK' or
            d['process_id']!=row['process_id'] or d['process_uuid']!=row['process_uuid'] or
            d['seed']!=20261109 or d['scenario']!='s_curve_left_right' or d['frames']!=10 or
            d['onnx_inference_used'] is not False):raise ValueError('retained native receipt mismatch')
        if label.startswith('on_') and (row['trace_bytes'],row['trace_sha256'])!=reader.TRACE_PINS[label+'.trace']:
            raise ValueError('trace/receipt association mismatch')
        native[label]=d
    if len({d['process_uuid'] for d in native.values()})!=4 or len({d['process_id'] for d in native.values()})!=4:
        raise ValueError('distinct retained processes required')
    if plan['order']!=['off_0','on_0','on_1','off_1'] or plan['seed']!=20261109:raise ValueError('original fixed schedule required')
    return native,files

def _write(path,value):
    raw=(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    if len(raw)>16*1024**2:raise ValueError('JSON report cap')
    with path.open('xb') as f:f.write(raw)
    return dict(path=path.name,nbytes=len(raw),sha256=sha256(raw).hexdigest())

def analyze_events(events):
    try:return provenance.analyze(events)
    finally:events.close()

def run(data_root,tool,deb,out):
    root=Path(data_root).absolute();out=Path(out).absolute()
    if out.exists() or '..' in out.parts or any(p.is_symlink() for p in (out,*out.parents)):
        raise ValueError('fresh nonsymlink output required')
    native,inputs=_inputs(root);out.mkdir(parents=True);reports=[];proofs=[];files=[];costs=[]
    started=perf_counter();cpu_started=process_time()
    try:
        for label in ('on_0','on_1'):
            wall=perf_counter();cpu=process_time()
            events,receipt=reader.decode(Path(tool).absolute(),root/(label+'.trace'),deb=Path(deb).absolute())
            proofs.append(receipt)
            report=analyze_events(events)
            if not receipt['decode_complete']:raise ValueError('incomplete offline decoding')
            expected_calls={'on_0':106555,'on_1':106580}[label]
            if report['calls']!=expected_calls or report['function_counts'].get('glReadPixels')!=60 or report['function_counts'].get('glBlitFramebuffer')!=90:
                raise ValueError('retained whole-stream count mismatch')
            reports.append(report)
            files.append(_write(out/(label+'-full-provenance.json'),report))
            selected=dict(schema=report['schema'],input_receipt=receipt,calls=report['calls'],contexts=report['contexts'],
                function_counts=report['function_counts'],reads=report['reads'],
                blits=[n for n in report['nodes'] if n['kind']=='blit_possible_write'],
                node_counts=dict(Counter(n['kind'] for n in report['nodes'])),
                all_read_pixels_unobserved=all(not q['pixels_observed'] for q in report['reads']),
                limitation=report['limitations'])
            files.append(_write(out/(label+'-read-routes.json'),selected))
            costs.append(dict(label=label,wall_seconds=perf_counter()-wall,parent_cpu_seconds=process_time()-cpu,
                parent_cpu_excludes_decoder_children=True))
        comparison=compare_reports(*reports);files.append(_write(out/'route-comparison.json',comparison))
        primary=[]
        for i in range(10):
            row=dict(step_1_based=i+1,association='INHERITED_FIXED_HOST_SCHEDULE_NOT_PIXEL_MATCH')
            for camera,index in (('road',16+4*i),('wide',19+4*i)):
                q=comparison['reads'][index]
                row[camera]=dict(read_ordinal=index,calls=q['calls'],marker_names_equal=q['marker_names_equal'],
                    same_route_topology=q['same_route_topology'],same_original_source_rgb=native['on_0']['source_rgb'][camera]['all_frame_sha256'][i]==native['on_1']['source_rgb'][camera]['all_frame_sha256'][i])
            primary.append(row)
        result=dict(schema='retained-gl-read-provenance-result-v1',status='ACTUAL_RETAINED_GL_COMMAND_ROUTES_ANALYZED',
            checked_at_kst=datetime.now(timezone(timedelta(hours=9))).isoformat(),inputs=inputs,decoder_receipts=proofs,outputs=files,
            trace_calls=[r['calls'] for r in reports],reads=[len(r['reads']) for r in reports],blits=[r['function_counts']['glBlitFramebuffer'] for r in reports],
            complete_rgb_resolve_routes=[sum(bool(q['routes']) for q in r['reads']) for r in reports],
            route_topology_equal=sum(q['same_route_topology'] is True for q in comparison['reads']),
            route_topology_different=sum(q['same_route_topology'] is False for q in comparison['reads']),
            route_topology_unobserved=sum(q['same_route_topology'] is None for q in comparison['reads']),
            primary_fixed_schedule_mapping=primary,costs=costs,total_wall_seconds=perf_counter()-started,
            parent_cpu_seconds=process_time()-cpu_started,parent_cpu_excludes_decoder_children=True,
            source_pins_preserved=299,new_native_calls=0,new_gl_calls=0,new_providers=0,new_model_calls=0,new_ort_sessions=0,
            consumed_sealed_allowance_remaining=0,official_model_input_association_proven=False,
            gpu_contents_reconstructed=False,returned_pixel_bytes_observed=False,sealed_frame_association_proven=False,
            untraced_equivalence_proven=False,unique_cause_proven=False,original_strict_pass=False,stage7_complete=False,
            limitations=['Retained older local traced cohort; no new native execution or current sealed physical-frame identity.',
                'Tracer hides program-binary formats and changes capabilities/timing. OFF has no GL trace.',
                'API-issued potential writers and conservative dependencies do not prove executed writes, overwritten pixels, sampling LOD or GPU completion.',
                'Full rasterizer/vertex/uniform state and GPU-generated textures are not reconstructed. No unique cause or repair.',
                'Read arguments contain pointer-only destinations, not returned pixel blobs; original primary-frame association remains schedule-only.',
                'CPU/I/O/decoder work has costs. Parent process CPU excludes child decoder CPU and these intervals are not tracing overhead or campaign end-to-end costs.'])
        _write(out/'result.json',result);return result
    except BaseException as exc:
        _write(out/'failure.json',dict(status='FAILED_OR_INCOMPLETE_OFFLINE_ANALYSIS',error_type=type(exc).__name__,detail=str(exc)[:500],
            decoder_receipts=proofs,completed_outputs=files,new_native_calls=0,new_gl_calls=0))
        raise

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('data-root','tool','deb','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args(argv)
    try:
        r=run(a.data_root,a.tool,a.deb,a.out)
        print(json.dumps({k:r[k] for k in ('status','trace_calls','reads','blits','complete_rgb_resolve_routes','route_topology_equal','route_topology_different','route_topology_unobserved','new_native_calls','new_gl_calls')}))
        return 0
    except (ValueError,OSError,KeyError,TypeError) as exc:print(json.dumps(dict(status='FAILED_OR_INCOMPLETE',error=type(exc).__name__+':'+str(exc)[:500])));return 1

if __name__=='__main__':raise SystemExit(main())

"""CPU-only conditional sampling analysis from fixed PR142 evidence bytes."""
from pathlib import Path
import argparse,copy,hashlib,json,math,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import sdk3_sampling_envelope as m

ROOT=Path(__file__).resolve().parents[1]
INDEX='docs/evidence/sdk3-sampling-envelope-01/input-index.json'
INDEX_SHA256='6543dc462cf3af472af77ad481566cfdfc947ec321b8cf46b98f23d02f9c3e54'
PREFIX='docs/evidence/sdk3-prepared-texture-01/actual/bundle/renderer/'
FALSE_FLAGS=('actual_gpu_sample_proven','hardware_bound_proven','actual_texture_format_proven','hardware_texture_dimensions_proven','actual_upload_bias_proven','actual_sample_coordinates_proven','gpu_program_execution_proven','gpu_pixel_owner_proven','unique_cause_proven','repair_proven','stage7_complete')

def _hash(raw):return hashlib.sha256(raw).hexdigest()

def _index(raw):
    m.need(isinstance(raw,bytes) and len(raw)<=65536 and _hash(raw)==INDEX_SHA256,'exact bounded sampling input index');x=json.loads(raw)
    m.need(x.get('protocol')=='sdk3-sampling-envelope-input-v1' and x.get('source_commit')=='d6eb529d52364117a01d446652f2e938089625c2' and x.get('source_pr')==142 and x.get('actual_run')==44067526874 and x.get('artifact_id')==14320743853 and x.get('artifact_digest')=='sha256:f5bbd810ad6369c64cece2e5c828b33b4eb43356b2069ca7136338c235144aad' and len(x['files'])==11,'fixed prior source and artifact identity');return x

def _read(root,name,limit):
    path=(root/name).resolve();m.need(path.is_relative_to(root) and path.is_file() and not (root/name).is_symlink(),'existing bounded regular input inside root')
    try:
        with path.open('rb') as f:raw=f.read(limit+1)
    except OSError as error:raise ValueError('input read failed') from error
    m.need(len(raw)<=limit,'input size bound');return raw

def load_inputs(root=ROOT):
    root=Path(root).resolve();raw=_read(root,INDEX,65536);index=_index(raw);files={};total=0
    for row in index['files']:
        data=_read(root,row['path'],1048576);m.need(len(data)==row['nbytes'] and _hash(data)==row['sha256'],'exact prior input bytes');files[row['path']]=data;total+=len(data)
    m.need(total<=2097152,'2MiB total input bound');return dict(root=str(root),index_raw=raw,files=files)

def documents(inputs):
    m.need(isinstance(inputs,dict),'input snapshot object');index=_index(inputs.get('index_raw'));files=inputs.get('files');m.need(isinstance(files,dict) and set(files)=={row['path'] for row in index['files']},'exact snapshot file set');total=0;result={}
    for row in index['files']:
        raw=files[row['path']];m.need(isinstance(raw,bytes) and len(raw)==row['nbytes']<=1048576 and _hash(raw)==row['sha256'],'authenticated snapshot bytes');total+=len(raw)
        if row['path'].endswith('.json'):result[Path(row['path']).name]=json.loads(raw)
    m.need(total<=2097152,'bounded snapshot total');return result

def validate_bindings(docs):
    prepared=docs['prepared.json'];terrain=docs['terrain.json'];geom=docs['geometry-observer.json'];shader=docs['shader.json'];material=docs['material.json'];report=docs['report.json'];obs=docs['independent-observation.json']
    m.need(obs.get('analysis_validated') is True and obs.get('run_id')==44067526874 and obs.get('artifact_id')==14320743853 and obs.get('source_sha')=='b759849d911190a2d3376b0f90daa330d8192c1c' and obs.get('head_sha')=='051b0f33ca2684d072363b42a4cba84a517cb2e3','pinned prior admitted observation')
    pid=obs['analysis']['pid'];nonce=report['nonce'];target=geom['target_read_sha256'];archive=geom['geometry']['triangle_archive']['sha256']
    for row in (prepared,terrain,geom,shader,material,report):m.need(row.get('pid')==pid and row.get('nonce')==nonce,'same prior process and nonce')
    for row in (prepared,terrain,geom,shader,material):m.need(row.get('target_read_sha256')==target,'same original Road7 read')
    for row in (prepared,terrain,shader,material):m.need(row.get('geometry_archive_sha256')==archive,'same geometry candidates')
    prior_flags=('hardware_texture_dimensions_proven','actual_upload_bias_proven','active_is_target_pixel_proof','gpu_program_execution_proven','gpu_pixel_owner_proven','unique_cause_proven','repair_proven','stage7_complete')
    m.need(all(prepared.get(k) is False for k in prior_flags) and report.get('official_model_processes')==report.get('onnx_inferences')==0 and report.get('model_weights_used') is False,'prior CPU evidence has no promoted GPU/model/repair claims')
    m.need(len(terrain['samples'])<=5 and [s['ray'] for s in terrain['samples']]==[r['name'] for r in geom['geometry']['rays'][:len(terrain['samples'])]],'same bounded CPU candidate ray identities')

def analyze(inputs):
    docs=documents(inputs);validate_bindings(docs);index=_index(inputs['index_raw']);prepared=docs['prepared.json'];terrain=docs['terrain.json'];obs=docs['independent-observation.json'];files=inputs['files']
    for name,field,target in [('prepared.json','terrain_sha256','terrain.json'),('prepared.json','material_sha256','material.json'),('terrain.json','shader_sha256','shader.json'),('shader.json','material_sha256','material.json')]:m.need(docs[name][field]==_hash(files[PREFIX+target]),'final prior observer digest chain')
    # This is the prior prepared boundary only, not fresh raw-image/renderer validation.
    from scripts.run_sdk3_prepared_texture import validate_prepared
    boundary=validate_prepared(Path(inputs['root'])/PREFIX,prepared['nonce'],copy.deepcopy(obs['analysis']));m.need(boundary==obs['analysis'],'unchanged prior prepared receiver result')
    attribute=next((r for r in prepared['textures'] if r['role']=='attribute'),None);m.need(attribute is not None,'existing attribute metadata');points=[];ratio=terrain['owner']['elevation_ratio'];matrix=terrain['node']['local_to_world']
    for i,sample in enumerate(terrain['samples']):
        item=attribute['mip1_windows'][i];m.need(item['sample_index']==i,'existing mip1 candidate index');w=item['window'];point=dict(ray=sample['ray'],triangle_index=sample['triangle_index'],terrain_uv=sample['heightfield_uv'],recorded_attribute_uv=sample['attribute_uv'],scenarios=[],threshold_roots=[],conditional_envelopes=[]);lo=(1-1/ratio)/2;hi=lo+1/ratio;bounds=all(lo<=v<=hi for v in sample['heightfield_uv']);point['cpu_candidate_bounds_match']=bounds
        for coordinate in m.COORDINATES:
            uv=m.attribute_uv(sample['heightfield_uv'],ratio,coordinate)
            for format_mode in m.FORMATS:
                for bits in m.WEIGHT_BITS:
                    scenario=m.scenario(w,uv,format_mode,bits);scenario.update(coordinate_model=coordinate,format_model=format_mode,weight_bits=bits)
                    if scenario['status']=='MODELED':scenario['yellow']=scenario['yellow'] and bounds
                    point['scenarios'].append(scenario)
        if w['status']=='CAPTURED':
            values=m.decode_window(w);fraction=m.fractions(w['uv'],w['size_xy']);point.update(raw_float32_values=values,recorded_fraction=fraction)
            for root in m.threshold_roots(values,fraction):
                delta=[0.,0.];delta[root['axis']]=root['delta_texels']/w['size_xy'][root['axis']];local=[delta[0]/ratio,delta[1]/ratio,0.];world=[sum(local[i]*matrix[i][j] for i in range(3)) for j in range(3)];point['threshold_roots'].append(dict(root,delta_attribute_uv=delta,world_displacement=world,world_displacement_norm=math.sqrt(sum(v*v for v in world)),world_displacement_is_proxy_only=True))
            for bits in (8,12):
                interval=m.conditional_envelope(values,fraction,bits);interval.update(fraction_bits_model=bits,all_yellow=interval['all_yellow'] and bounds);point['conditional_envelopes'].append(interval)
        points.append(point)
    scenarios=[v for p in points for v in p['scenarios']];modeled=[v for v in scenarios if v['status']=='MODELED'];m.need(len(points)<=5 and len(scenarios)<=135,'bounded model enumeration')
    result=dict(protocol='sdk3-sampling-envelope-v1',status='CONDITIONAL_MODELS_RECORDED',source=dict(source_commit=index['source_commit'],source_pr=142,actual_run=index['actual_run'],artifact_id=index['artifact_id'],artifact_digest=index['artifact_digest'],input_index_sha256=INDEX_SHA256,input_file_count=11,inputs=index['files']),prior_prepared_boundary_revalidated=True,fresh_source_images_verified=False,prior_verified_source_images=obs['analysis']['verified_source_images'],native_renderer_processes_this_step=0,official_model_processes=0,onnx_inferences=0,within_captured_cells_only=True,input_points_are_geomnode_proxies=True,scenario_count=len(scenarios),modeled_scenario_count=len(modeled),unavailable_scenario_count=len(scenarios)-len(modeled),modeled_yellow_count=sum(v['yellow'] for v in modeled),points=points,original_matrix_passed=3,original_matrix_total=4,original_matrix_gate_passed=False,assumptions=['Nearest-even SNORM8/UNORM8 codes are hypothetical; runtime internal format is unmeasured.','8/12-bit weight rounding and adjacent-code/fraction boxes are conditional models, not driver guarantees.','Float32 separate/FMA coordinates model arithmetic only; actual terrain draw coordinates remain unknown.','Axis threshold roots hold the other fraction fixed and stay within each captured cell; neighbors are unavailable.'],**{k:False for k in FALSE_FLAGS})
    raw=json.dumps(result,sort_keys=True,indent=2,allow_nan=False).encode();m.need(len(raw)+1<=1048576,'1MiB result bound');return json.loads(raw)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();m.need(not args.out.exists(),'fresh output directory');result=analyze(load_inputs());args.out.mkdir(parents=True,exist_ok=False);raw=(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n').encode();(args.out/'result.json').write_bytes(raw);print(json.dumps(dict(status=result['status'],scenarios=result['scenario_count'],modeled=result['modeled_scenario_count'],yellow=result['modeled_yellow_count'],result_sha256=_hash(raw),native_renderer_processes_this_step=0,stage7_complete=False)))
if __name__=='__main__':main()

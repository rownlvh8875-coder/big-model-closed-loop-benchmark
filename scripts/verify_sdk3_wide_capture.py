"""Rebuild both camera products offline and verify the original capture timing."""

from dataclasses import asdict
from hashlib import sha256
import json
import math
from pathlib import Path
import tempfile
import zlib

import numpy as np

from bigbench import sdk3_wide_capture_contract as c
from bigbench.optical_calibration import PinholeRectifier, PinholeIntrinsics
from bigbench.preprocess_experiment import LiveInput
from scripts import panda_sdk3_runtime as pins

SOURCE_SHAPE = (604,964,3)
SOURCE_NBYTES = math.prod(SOURCE_SHAPE)
ROLES = ('road','wide')


def load_pixels(folder, description, name, size):
    pins.need(description==dict(name=name,extent=size),'registered exact evidence pathname and extent')
    path=folder/name
    pins.need(path.is_file() and not path.is_symlink() and path.stat().st_size<=size+4096,'bounded ordinary pixel file')
    stream=zlib.decompressobj()
    raw=stream.decompress(path.read_bytes(),size+1)
    pins.need(len(raw)==size and stream.eof and not stream.unused_data and not stream.unconsumed_tail,'complete bounded zlib stream')
    return raw


def verify_timing(row, previous_end, delay):
    begin=row['capture_begin_ns']
    end=row['capture_end_ns']
    ordered=[row[k] for k in ('wait_begin_ns','capture_begin_ns','capture_end_ns',
                             'preprocessing_end_ns','evidence_write_end_ns')]
    pins.need(ordered==sorted(ordered) and ordered[0]>=previous_end,'ordered capture/write timestamps')
    pins.need(begin-ordered[0]>=(delay if row['step']>1 else 0)*1_000_000_000,'registered between-capture wait')
    observed=row['events']
    spec=[(role,stage) for role in ROLES for stage in ('perceive','render_task','read_rgb')]
    pins.need([(e['role'],e['stage']) for e in observed]==spec,'exact original road/wide task/read sequence')
    durations={}
    border=begin
    for i,role in enumerate(ROLES):
        outer,task,read=observed[i*3:i*3+3]
        pins.need(border<=outer['begin_ns']<=task['begin_ns']<=task['end_ns']<=read['begin_ns']
                  <=read['end_ns']<=outer['end_ns']<=end,'read follows the existing render task')
        pins.need(read['world_parent'] and read['has_ram_before'],'RAM read at borrowed world pose')
        expected_pos=[float(np.float32(row['pose'][coord])) for coord in ('x','y')]
        expected_h=math.degrees(row['pose']['heading'])-90.
        pins.need(read['position'][:2]==expected_pos
                  and read['hpr']==[float(np.float32(expected_h)),0.,0.],'actual native world position and heading')
        durations[role]=dict(task_ns=task['end_ns']-task['begin_ns'],read_ns=read['end_ns']-read['begin_ns'],
                             since_task_end_ns=read['begin_ns']-task['end_ns'],
                             seq_before_perceive=outer['image_seq_before'],
                             seq_at_read=read['image_seq_before'],seq_after_read=read['image_seq_after'],
                             native_position=read['position'],native_hpr=read['hpr'])
        border=outer['end_ns']
    return dict(cameras=durations,observed_wait_ns=begin-ordered[0],
                capture_ns=end-begin,prepare_ns=ordered[3]-end,write_ns=ordered[4]-ordered[3])


def verify_native(native, poses, trial):
    report=json.loads((native/'report.json').read_bytes())
    child=json.loads((native/'native-child.json').read_bytes())
    execution=json.loads((native/'execution.json').read_bytes())
    pins.need(report['status']=='CAPTURE_COMPLETE' and report['trial']==trial and report['pid']==child['pid']
              and report['provider_closed'] and report['child_finalized_before_server_stop']
              and child['returncode']==child['server_returncode']==report['server_returncode']==0
              and execution['owned_container_removed'] and not execution['stopped_state']['OOMKilled']
              and report['inference_bounds']==[0,0] and report['official_model_processes']==0
              and report['ort_module_loaded'] is False,'completed owned camera-only runtime')
    original=json.loads(poses.read_bytes())
    pins.need(all(report[key]==original[key] for key in ('driver','geometry','intrinsics'))
              and report['pose_source_sha256']==pins.digest(poses),'exact verified poses and context')
    pins.need(len(report['captures'])==report['camera_capture_attempts']==c.LIMITS['captures_per_process']
              and report['inserted_wait_s']==c.TRIALS[trial],'complete registered condition')
    lenses={role:PinholeIntrinsics(**original['intrinsics'][role]) for role in ROLES}
    folder=native/'pixels'
    expected=set()
    outputs=[]
    from types import SimpleNamespace
    with tempfile.TemporaryDirectory() as temp:
        preparer=LiveInput(SimpleNamespace(),lenses,c.VARIANT,Path(temp))
        rectifier=PinholeRectifier()
        previous=0
        for actual,known in zip(report['captures'],original['frames'],strict=True):
            step=known['step']
            pins.need(actual['step']==step and actual['pose']==known['pose'],'exact old input pose, same chronological frame')
            timing=verify_timing(actual,previous,c.TRIALS[trial])
            previous=actual['evidence_write_end_ns']
            hashes={}
            images={}
            for role in ROLES:
                name=f'{step:02d}-{role}-source.rgb.zlib'
                source=load_pixels(folder,actual['pixels'][role]['source'],name,SOURCE_NBYTES)
                expected.add(name)
                hashes[role]=sha256(source).hexdigest()
                images[role]=np.frombuffer(source,dtype=np.uint8).reshape(SOURCE_SHAPE)
            pair,_=rectifier.rectify_pair(images['road'],images['wide'],
                                          road_intrinsics=lenses['road'],wide_intrinsics=lenses['wide'])
            for role in ROLES:
                canvas=getattr(pair,role).rgb
                name=f'{step:02d}-{role}-canvas.rgb.zlib'
                pins.need(load_pixels(folder,actual['pixels'][role]['canvas'],name,len(canvas))==canvas,'canvas exact reconstruction')
                expected.add(name)
            preparer.record_native_rgb(images,hashes)
            preparer.expected=(pair.road.sha256,pair.wide.sha256)
            tensor=preparer.prepare(pair.road,pair.wide).tobytes()
            name=f'{step:02d}-input.bin.zlib'
            expected.add(name)
            pins.need(load_pixels(folder,actual['pixels']['tensor'],name,len(tensor))==tensor
                      and actual['hashes']==preparer.rows[-1],'exact original input/hash reconstruction')
            outputs.append(dict(**preparer.rows[-1],timing=timing))
    pins.need({p.name for p in folder.iterdir()}==expected,'complete native pixel files')
    return dict(status='CAMERA_TIMING_VERIFIED',trial=trial,pose_source_sha256=pins.digest(poses),
                pid=report['pid'],nonce=report['nonce'],frames=outputs,model_processes=0,inferences=0)

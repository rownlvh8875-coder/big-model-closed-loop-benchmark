"""Qualify node-level readout on a synthetic graph in independent ORT processes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper


STEPS = ((0.125, -0.5, -0.375, 0.625), (0.0, 0.5, -18.0, 18.0),
         (1.0, -1.0, -0.00048828125, -0.00048828125))
NODE = 'FixtureSum'
PUBLIC = 'public_action'


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def write_json(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def make_fixture(path):
    spec = [
        helper.make_node('Tanh', ['correction_logits'], ['correction'], name='FixtureCorrection'),
        helper.make_node('Add', ['base', 'correction'], ['sum_fp16'], name=NODE),
        helper.make_node('Cast', ['sum_fp16'], [PUBLIC], to=TensorProto.FLOAT, name='Export'),
    ]
    inputs = [helper.make_tensor_value_info(name, TensorProto.FLOAT16, [1, 2])
              for name in ('base', 'correction_logits')]
    output = helper.make_tensor_value_info(PUBLIC, TensorProto.FLOAT, [1, 2])
    model = helper.make_model(helper.make_graph(spec, 'arithmetic_fixture', inputs, [output]),
                              ir_version=9, opset_imports=[helper.make_opsetid('', 17)])
    onnx.checker.check_model(model)
    with path.open('xb') as stream:
        stream.write(model.SerializeToString())


def inspect_dump(directory, target, returned):
    expected = {*target.input, *target.output}
    stored = {}
    for path in sorted(directory.rglob('*.tensorproto')):
        assert not path.is_symlink() and path.stat().st_size <= 4096, path
        tensor = onnx.load_tensor(path)
        assert tensor.name not in stored and tensor.data_type == TensorProto.FLOAT, tensor.name
        data = numpy_helper.to_array(tensor)
        assert data.dtype == np.float32 and data.shape == (1, 2) and np.isfinite(data).all()
        stored[tensor.name] = data
    assert stored.keys() == expected, (sorted(stored), sorted(expected))
    left, right = (stored[name] for name in target.input)
    result = stored[target.output[0]]
    assert np.all(np.abs(right) <= 1)
    assert np.add(left, right, dtype=np.float32).tobytes() == result.tobytes() == returned.tobytes()
    return {name: sha(value.tobytes()) for name, value in sorted(stored.items())}


def child(args):
    root = args.evidence.resolve()
    site = args.site.resolve()
    sys.path.insert(0, str(site))
    import onnxruntime as ort

    stock = args.child == 'stock'
    assert ort.__version__ == '1.20.1' and Path(ort.__file__).is_relative_to(site)
    model = root / 'fixture.onnx'
    assert sha(model.read_bytes()) == args.fixture_sha256
    run = root / args.child
    opt = run / 'optimized.onnx'
    options = ort.SessionOptions()
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    options.optimized_model_filepath = str(opt)
    session = ort.InferenceSession(str(model), options, providers=['CPUExecutionProvider'])
    assert session.get_providers() == ['CPUExecutionProvider']
    assert [item.name for item in session.get_outputs()] == [PUBLIC]
    optimized = onnx.load(opt, load_external_data=False)
    target, = (node for node in optimized.graph.node if node.name == NODE)
    assert target.op_type == 'Add' and len(target.input) == 2 and len(target.output) == 1

    rows = []
    for step, sample in enumerate(STEPS, 1):
        folder = run / f'{step:02d}'
        folder.mkdir()
        os.chdir(folder)
        try:
            feeds = {'base': np.array([sample[:2]], dtype=np.float16),
                     'correction_logits': np.array([sample[2:]], dtype=np.float16)}
            value, = session.run([PUBLIC], feeds)
            assert value.dtype == np.float32 and value.shape == (1, 2) and np.isfinite(value).all()
            dumps = {} if stock else inspect_dump(folder, target, value)
            assert stock or len(dumps) == 3
            rows.append(dict(step=step, public_sha256=sha(value.tobytes()), native_tensor_sha256=dumps))
        finally:
            os.chdir(run)
    write_json(run / 'report.json', dict(ort_version=ort.__version__, build=ort.get_build_info(),
                                        mode=args.child, fixture_sha256=args.fixture_sha256,
                                        provider=session.get_providers()[0], rows=rows))


def qualify(stock, debug, evidence):
    root = evidence.resolve()
    fixture = root / 'fixture.onnx'
    make_fixture(fixture)
    model_sha = sha(fixture.read_bytes())
    debug_flags = {
        'ORT_DEBUG_NODE_IO_NAME_FILTER': NODE,
        'ORT_DEBUG_NODE_IO_DUMP_INPUT_DATA': '1',
        'ORT_DEBUG_NODE_IO_DUMP_OUTPUT_DATA': '1',
        'ORT_DEBUG_NODE_IO_DUMP_DATA_TO_FILES': '1',
        'ORT_DEBUG_NODE_IO_DUMP_DATA_DESTINATION': 'files',
        'ORT_DEBUG_NODE_IO_OUTPUT_DIR': '.',
    }
    clean = {key: value for key, value in os.environ.items() if not key.startswith('ORT_DEBUG_NODE_IO_')}
    for mode, site, env in (('stock', stock, clean), ('debug', debug, clean | debug_flags)):
        folder = root / mode
        folder.mkdir()
        command = [sys.executable, '-I', '-B', str(Path(__file__).resolve()),
                   str(stock), str(debug), str(root), '--child', mode,
                   '--site', str(site.resolve()), '--fixture-sha256', model_sha]
        with (folder/'stdout.log').open('xb') as out, (folder/'stderr.log').open('xb') as err:
            result = subprocess.run(command, cwd=folder, env=env, stdout=out, stderr=err,
                                    timeout=80, check=False)
        (folder/'returncode.txt').write_text(f'{result.returncode}\n')
        result.check_returncode()

    stock_report, debug_report = [json.loads((root/mode/'report.json').read_bytes())
                                  for mode in ('stock', 'debug')]
    assert stock_report['ort_version'] == debug_report['ort_version'] == '1.20.1'
    compiled = re.search(r'git-commit-id=([0-9a-f]{7,40})(?:,|\s|$)', debug_report['build'])
    assert compiled and '5c1b7ccbff7e5141c1da7a9d963d660e5741c319'.startswith(compiled[1]), debug_report['build']
    assert len(stock_report['rows']) == len(debug_report['rows']) == len(STEPS)
    for left, right in zip(stock_report['rows'], debug_report['rows'], strict=True):
        assert left['step'] == right['step'] and left['public_sha256'] == right['public_sha256']
    assert len({row['public_sha256'] for row in debug_report['rows']}) == len(STEPS)
    write_json(root/'qualification.json', dict(
        status='SYNTHETIC_NODE_AUDIT_QUALIFIED', source_commit='5c1b7ccbff7e5141c1da7a9d963d660e5741c319',
        fixture_sha256=model_sha, official_model_processes=0, official_inferences=0, renderer_processes=0,
        native_fp32_add_frames=len(STEPS), exact_public_output_frames=len(STEPS),
        separate_dump_directories=len(STEPS)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('stock', 'debug', 'evidence'):
        parser.add_argument(name, type=Path)
    parser.add_argument('--child', choices=['stock','debug'])
    parser.add_argument('--site', type=Path)
    parser.add_argument('--fixture-sha256')
    args = parser.parse_args()
    if args.child:
        child(args)
    else:
        qualify(args.stock, args.debug, args.evidence)


if __name__ == '__main__':
    main()

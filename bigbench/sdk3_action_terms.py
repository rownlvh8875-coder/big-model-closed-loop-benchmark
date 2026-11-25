"""Contracts for capturing the native CPU residual path in md-v3."""

import hashlib
import os
from pathlib import Path
import re

from bigbench.sdk3_steering_contract import CASES, LIMITS, PROBE_CASES, VARIANT, live_limits, modeled_activity


BASE = '55760c44b0093f8712f6332201a88d4bb8fbffe0'
BRANCH = 'diagnostic/sdk3-residual-terms-20261121-01'
WORKFLOW = '.github/workflows/sdk3-residual-terms-20261121.yml'
APPROVAL = 'docs/approvals/sdk3-residual-terms-20261121-01.json'
REQUEST = 'docs/requests/sdk3-residual-terms-20261121-01.json'
MODE = 'STEERING_NATIVE_RESIDUAL_TERMS'
REPORT_PROTOCOL = 'sdk3-residual-terms-v1'
OUTPUT = 'sdk3-residual-terms-20261121'
ORT_COMMIT = '5c1b7ccbff7e5141c1da7a9d963d660e5741c319'
NODES = ('node_add_74', 'node_add_75', 'node_tanh', 'node_add_76')
DEBUG_FLAGS = {
    'ORT_DEBUG_NODE_IO_NAME_FILTER': ';'.join(NODES),
    'ORT_DEBUG_NODE_IO_OP_TYPE_FILTER': 'Add;Tanh',
    'ORT_DEBUG_NODE_IO_DUMP_INPUT_DATA': '1',
    'ORT_DEBUG_NODE_IO_DUMP_OUTPUT_DATA': '1',
    'ORT_DEBUG_NODE_IO_DUMP_DATA_DESTINATION': 'files',
    'ORT_DEBUG_NODE_IO_OUTPUT_DIR': '.',
}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def native_libraries(site):
    return {path.name: digest(path) for path in
            sorted((site/'onnxruntime/capi').glob('*.so*')) if path.is_file()}


def release_build(info):
    commit = re.search(r'git-commit-id=([0-9a-f]{7,40})(?:,|\s|$)', info)
    return bool(commit and ORT_COMMIT.startswith(commit[1]))


def capturing_policy(root):
    from bigbench.preprocess_experiment import policy_class

    root.mkdir()

    class CaptureNativeAdd(policy_class()):
        def step(self, observation):
            directory = root / str(len(self.audit_rows) + 1)
            directory.mkdir()
            original = Path.cwd()
            os.chdir(directory)
            try:
                return super().step(observation)
            finally:
                os.chdir(original)

    return CaptureNativeAdd

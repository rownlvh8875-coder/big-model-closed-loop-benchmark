"""Observe exact MetaDrive-0.4.3 PSSM/chase Python callback *calls*.

sys.setprofile does NOT re-register or wrap any Panda task. It DOES add CPU
overhead and can perturb wall-clock scheduling. The unprofiled process control
therefore must remain separate; no render/callback equivalence is claimed.
"""
from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
import sys
from time import perf_counter_ns
from typing import Any


CALLBACKS = ("PSSM.update", "MainCamera._chase_task")


class CallbackTraceError(RuntimeError):
    pass


class ExactCallbackProfiler:
    """Capture two exact Python method code objects in the active Panda main thread."""

    def __init__(self, engine: Any):
        from metadrive.engine.core.pssm import PSSM
        from metadrive.engine.core.main_camera import MainCamera

        self._codes = {
            PSSM.update.__code__: "PSSM.update",
            MainCamera._chase_task.__code__: "MainCamera._chase_task",
        }
        self._engine = engine
        self._pssm = getattr(engine, "pssm", None)
        if self._pssm is None:
            raise CallbackTraceError("MetaDrive PSSM instance not present")
        self.events: list[dict] = []
        self.active = False

    def _profile(self, frame, event, _arg):
        if event != "call" and event != "return":
            return
        callback = self._codes.get(frame.f_code)
        if callback is None:
            return
        self_obj = frame.f_locals.get("self")
        if callback == "PSSM.update":
            if self_obj is not self._pssm:
                return
        elif getattr(self_obj, "engine", None) is not self._engine:
            return
        self.events.append({
            "order_in_trace": len(self.events),
            "event": event,
            "callback": callback,
            "perf_counter_ns": perf_counter_ns(),
            "chase_run_task_flag": (
                bool(getattr(self_obj, "run_task", False))
                if callback == "MainCamera._chase_task" else None
            ),
        })

    @contextmanager
    def observe(self):
        if self.active:
            raise CallbackTraceError("a Python profile observer is already active")
        if sys.getprofile() is not None:
            raise CallbackTraceError("an existing Python profile hook must be preserved")
        self.active = True
        before = len(self.events)
        try:
            sys.setprofile(self._profile)
            yield
        finally:
            sys.setprofile(None)
            self.active = False
            if len(self.events) < before:
                raise CallbackTraceError("callback trace shrank unexpectedly")


def summarize_callback_pair(events: list[dict], expected_taskmgr_steps: int) -> dict:
    """Verify true call/return pairs, not registration or inferred sort order."""
    if type(expected_taskmgr_steps) is not int or expected_taskmgr_steps not in (1, 2):
        raise CallbackTraceError("expected one or two actual taskMgr.step calls")
    if not isinstance(events, list):
        raise CallbackTraceError("callback event receipt missing")
    if len(events) != 4 * expected_taskmgr_steps:
        raise CallbackTraceError(
            f"expected {4 * expected_taskmgr_steps} callback call/return records, "
            f"got {len(events)}"
        )
    for item in events:
        if (item.get("callback") not in CALLBACKS
                or item.get("event") not in ("call", "return")
                or type(item.get("perf_counter_ns")) is not int):
            raise CallbackTraceError("invalid callback event payload")
    calls = [x for x in events if x["event"] == "call"]
    returns = [x for x in events if x["event"] == "return"]
    if (len(calls) != 2*expected_taskmgr_steps or
            len(returns) != 2*expected_taskmgr_steps):
        raise CallbackTraceError("missing Python callback entry or exit")
    # Non-overlapping callbacks: each is a Panda main-thread task, no recursion.
    for a, b in zip(events[::2], events[1::2]):
        if (a["event"] != "call" or b["event"] != "return"
                or a["callback"] != b["callback"]
                or a["perf_counter_ns"] > b["perf_counter_ns"]):
            raise CallbackTraceError("callback exits do not match Python entries")
    if any(
        later["perf_counter_ns"] < earlier["perf_counter_ns"]
        for earlier, later in zip(events, events[1:])
    ):
        raise CallbackTraceError("nonmonotonic callback profiling timestamps")

    tick_orders = []
    for i in range(expected_taskmgr_steps):
        names = [c["callback"] for c in calls[2*i:2*i+2]]
        if set(names) != set(CALLBACKS):
            raise CallbackTraceError("both actual registered callbacks must execute in each tick")
        tick_orders.append(names)
    return {
        "status": "TWO_PYTHON_TASK_CALLBACKS_OBSERVED_PER_TASKMGR_STEP",
        "expected_taskmgr_steps_from_source": expected_taskmgr_steps,
        "actual_callback_calls": len(calls),
        "actual_callback_returns": len(returns),
        "per_taskmgr_step_callback_call_order": tick_orders,
        "call_order_is_measured_not_inferred_from_sort": True,
        "registered_task_objects_replaced": False,
        "trace_changes_cpu_timing": True,
        "trace_proves_gpu_render_order": False,
    }


def summarize_callback_sequence(receipts: list[dict], *, expected_steps: int) -> dict:
    if type(expected_steps) is not int or expected_steps not in (1,2):
        raise CallbackTraceError("unsupported capture schedule")
    if not isinstance(receipts,list) or not receipts:
        raise CallbackTraceError("no observed callback samples")
    flattened = []
    for r in receipts:
        if (r.get("status") != "TWO_PYTHON_TASK_CALLBACKS_OBSERVED_PER_TASKMGR_STEP"
                or r.get("expected_taskmgr_steps_from_source") != expected_steps):
            raise CallbackTraceError("incomplete actual callback evidence")
        flattened.extend(r["per_taskmgr_step_callback_call_order"])
    observed = Counter(" BEFORE ".join(x) for x in flattened)
    if len(flattened) != len(receipts)*expected_steps:
        raise CallbackTraceError("missing callback tick receipts")
    return {
        "status": "EXACT_PYTHON_CALLBACK_CALL_SEQUENCE_RECORDED",
        "observed_taskmgr_ticks": len(flattened),
        "order_frequencies": dict(sorted(observed.items())),
        "all_ticks_same_callback_order": len(observed)==1,
        "task_registration_modified": False,
        "timestamp_overhead_can_change_original_wall_clock_schedule": True,
        "actual_callback_execution_order_is_not_gpu_draw_order": True,
        "model_driving_rank_allowed": False,
    }

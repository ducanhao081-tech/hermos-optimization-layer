"""
layer.py — RuntimeClosedLoopLayer facade

职责：对外只暴露三个方法。
observe() → on_turn() → finalize()
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .context import render_runtime_context
from .detectors import Signal, run_detectors
from .events import Intent, ToolEvent, extract_error_signature, normalize_tool_result
from .evidence import EvidenceRecord, append_jsonl
from .gate import CompletionCheck, verification_gate
from .policy import (
    TaskProfile,
    resolve_policy,
    should_skip_loop,
)
from .state import compute_task_view


@dataclass
class ClosedLoopOutput:
    closed_loop_context: Optional[str]
    completion_check: Optional[CompletionCheck]
    signals: List[Signal]


class RuntimeClosedLoopLayer:
    """
    Runtime Closed-Loop Layer 外观类。

    三个对外方法：
    - observe(raw_tool_result): 观察工具结果，归一化成事件
    - on_turn(completion_claimed): 输出信号、完成检查、runtime context
    - finalize(): 生成 EvidenceRecord 并写入 JSONL

    设计原则：
    - 不主动执行命令
    - 不主动修改文件
    - 不主动写 worklog
    - 不进入 Memory / SOUL.md
    """

    def __init__(self, task_profile: TaskProfile, evidence_log_path: Optional[str] = None):
        self.task_profile = task_profile
        self.policy = resolve_policy(task_profile.task_type)
        self.evidence_log_path = evidence_log_path
        self.start_time = datetime.now(timezone.utc).isoformat()

        # 内部状态（内存易失，任务结束后丢弃）
        self._events: List[ToolEvent] = []
        self._error_signature_counts: Dict[str, int] = {}
        self._finalized = False

    # ── 对外接口 ──

    def observe(self, raw_tool_result: dict) -> None:
        """
        观察一次工具执行结果。

        raw_tool_result 格式：
        {
            "tool_name": str,
            "arguments": dict,
            "result": dict,
            "declared_intent": Optional[str],  # executor 显式声明
        }
        """
        if self._finalized:
            return

        if should_skip_loop(self.task_profile):
            return

        event = normalize_tool_result(
            index=len(self._events),
            tool_name=raw_tool_result.get("tool_name", ""),
            arguments=raw_tool_result.get("arguments", {}),
            result=raw_tool_result.get("result", {}),
            declared_intent=raw_tool_result.get("declared_intent"),
        )
        self._events.append(event)

        # 记录错误签名（用于 RepeatedFailure）
        if event.intent in (Intent.EXECUTE, Intent.VERIFY):
            sig = extract_error_signature(
                stdout=event.stdout_snippet or "",
                stderr=event.stderr_snippet,
                command=event.command or "",
            )
            if sig:
                self._error_signature_counts[sig] = (
                    self._error_signature_counts.get(sig, 0) + 1
                )

    def on_turn(self, completion_claimed: bool = False) -> ClosedLoopOutput:
        """
        当前轮次结束后调用，返回闭环输出。

        参数：
            completion_claimed: 模型是否在回复中声明了"已完成"
        """
        if should_skip_loop(self.task_profile):
            return ClosedLoopOutput(
                closed_loop_context=None,
                completion_check=None,
                signals=[],
            )

        # 检查逃生口：是否有事件标记了 verification_not_possible
        vnp = False
        vnp_reason = None
        for ev in self._events:
            if getattr(ev, "verification_not_possible", False):
                vnp = True
                vnp_reason = getattr(ev, "verification_not_possible_reason", None)
                break

        task_view = compute_task_view(
            events=self._events,
            profile=self.task_profile,
            policy=self.policy,
            completion_claimed=completion_claimed,
            error_signature_counts=self._error_signature_counts,
            verification_not_possible=vnp,
            verification_not_possible_reason=vnp_reason,
        )

        signals = run_detectors(
            events=self._events,
            task_view=task_view,
            profile=self.task_profile,
            policy=self.policy,
            completion_claimed=completion_claimed,
            error_signature_counts=self._error_signature_counts,
        )

        completion_check = verification_gate(
            task_view=task_view,
            profile=self.task_profile,
            policy=self.policy,
            signals=signals,
            events=self._events,
        )

        context = render_runtime_context(
            task_view=task_view,
            signals=signals,
            completion_check=completion_check,
        )

        return ClosedLoopOutput(
            closed_loop_context=context,
            completion_check=completion_check,
            signals=signals,
        )

    def finalize(self) -> EvidenceRecord:
        """
        任务结束时调用。生成证据记录并写入 JSONL。
        幂等：第二次调用返回同样的记录但不重复写入。
        """
        self._finalized = True
        end_time = datetime.now(timezone.utc).isoformat()

        last_output = self.on_turn(completion_claimed=False)

        record = EvidenceRecord(
            task_id=self.task_profile.task_id,
            task_type=self.task_profile.task_type.value,
            profile_source=self.task_profile.profile_source,
            start_time=self.start_time,
            end_time=end_time,
            final_state=last_output.completion_check.reason
            if last_output.completion_check
            else "unknown",
            can_complete=last_output.completion_check.can_complete
            if last_output.completion_check
            else False,
            tool_events=[ev.__dict__ for ev in self._events],
            signals=[
                {"type": s.type, "level": s.level.value, "detail": s.detail}
                for s in last_output.signals
            ],
            completion_check=last_output.completion_check.__dict__
            if last_output.completion_check
            else None,
        )

        if self.evidence_log_path:
            append_jsonl(record, self.evidence_log_path)
        return record

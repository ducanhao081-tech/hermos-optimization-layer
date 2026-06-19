"""
gate.py — CompletionCheck, verification_gate()

职责：回答"当前任务是否具备宣布完成的证据？"
纯函数，LLM-free，只查 event_log。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .detectors import Signal, SignalLevel
from .events import Intent, ToolEvent
from .policy import CompletionMode, CompletionPolicy, TaskProfile
from .state import TaskState, TaskView


@dataclass
class CompletionCheck:
    can_complete: bool
    confidence: float
    reason: str
    missing_evidence: List[str]
    residual_risks: List[str]
    recommended_next_action: str


def verification_gate(
    task_view: TaskView,
    profile: TaskProfile,
    policy: CompletionPolicy,
    signals: List[Signal],
    events: List[ToolEvent],
) -> CompletionCheck:
    """完成门控：判断任务是否具备完成证据"""
    missing: List[str] = []
    risks: List[str] = []

    # SKIP 策略直接放行
    if policy.completion_mode == CompletionMode.SKIP:
        return CompletionCheck(
            can_complete=True,
            confidence=1.0,
            reason="对话任务，跳过完成检查。",
            missing_evidence=[],
            residual_risks=[],
            recommended_next_action="完成对话。",
        )

    # BLOCKED_REPEAT 不放行
    if task_view.state == TaskState.BLOCKED_REPEAT:
        escalation_signals = [s for s in signals if s.level == SignalLevel.ESCALATE]
        reason = escalation_signals[0].detail if escalation_signals else "相同错误反复出现"
        return CompletionCheck(
            can_complete=False,
            confidence=0.0,
            reason=reason,
            missing_evidence=["resolve_repeated_failure"],
            residual_risks=["未解决的重复错误"],
            recommended_next_action="停止重复尝试，总结当前证据和下一步建议。",
        )

    # STRICT 策略：需要验证
    if policy.verification_required and task_view.needs_verification:
        if task_view.verification_failed_after_last_mod:
            missing.append("passing_verification")
            risks.append("verification_failed")
        else:
            missing.append("verification_or_explained_reason")
            missing.append("passing_test_or_explanation")

    if task_view.verification_not_possible:
        risks.append(
            "verification_not_possible:"
            + (task_view.verification_not_possible_reason or "reason_not_recorded")
        )

    # worklog 要求
    if policy.worklog_required:
        has_log = any(ev.intent == Intent.LOG for ev in events)
        if not has_log:
            risks.append("worklog_not_recorded")

    # 构建结果
    if missing:
        reason = "缺少完成证据：" + ", ".join(missing)
        if risks:
            reason += "；残留风险：" + ", ".join(risks)
        return CompletionCheck(
            can_complete=False,
            confidence=0.2,
            reason=reason,
            missing_evidence=missing,
            residual_risks=risks,
            recommended_next_action="补充验证证据或说明无法验证原因。",
        )

    # 可以通过，但可能有残留风险
    confidence = 0.9
    reason_parts = ["证据检查通过"]
    if risks:
        confidence = 0.6
        reason_parts.append("但存在残留风险：" + ", ".join(risks))

    return CompletionCheck(
        can_complete=True,
        confidence=confidence,
        reason="；".join(reason_parts),
        missing_evidence=[],
        residual_risks=risks,
        recommended_next_action="完成。",
    )

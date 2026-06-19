"""
detectors.py — Signal, run_detectors()

职责：MVP 只做三个检测器。
所有检测规则化、确定性、可单测。LLM-free。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List

from .events import ToolEvent
from .policy import CompletionMode, CompletionPolicy, Intervention, TaskProfile
from .state import TaskState, TaskView


class SignalLevel(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    ESCALATE = "ESCALATE"


@dataclass
class Signal:
    type: str
    level: SignalLevel
    detail: str
    recommended_intervention: Intervention


def run_detectors(
    events: List[ToolEvent],
    task_view: TaskView,
    profile: TaskProfile,
    policy: CompletionPolicy,
    completion_claimed: bool,
    error_signature_counts: dict,
) -> List[Signal]:
    """运行所有检测器，返回信号列表"""
    signals: List[Signal] = []

    if policy.completion_mode == CompletionMode.SKIP:
        return signals

    signals.extend(_detect_missing_verification(task_view, policy))
    signals.extend(_detect_failed_verification(task_view, policy))
    signals.extend(_detect_premature_completion(task_view, policy, completion_claimed))
    signals.extend(_detect_repeated_failure(task_view, policy))

    return signals


def _detect_missing_verification(
    task_view: TaskView,
    policy: CompletionPolicy,
) -> List[Signal]:
    """MissingVerification: 代码已修改但没有验证证据"""
    if not policy.verification_required:
        return []

    if not task_view.needs_verification or task_view.verification_attempted_after_last_mod:
        return []

    return [
        Signal(
            type="MissingVerification",
            level=SignalLevel.WARN,
            detail="代码已修改，但没有验证证据。请运行最小验证命令，或说明为什么无法验证。",
            recommended_intervention=Intervention.REQUEST_VERIFY,
        )
    ]


def _detect_failed_verification(
    task_view: TaskView,
    policy: CompletionPolicy,
) -> List[Signal]:
    """VerificationFailed: a check ran after the modification and failed."""
    if not policy.verification_required:
        return []
    if not task_view.verification_failed_after_last_mod:
        return []
    return [
        Signal(
            type="VerificationFailed",
            level=SignalLevel.WARN,
            detail="验证命令已执行但未通过，不能宣布任务完成。",
            recommended_intervention=Intervention.REQUEST_VERIFY,
        )
    ]


def _detect_premature_completion(
    task_view: TaskView,
    policy: CompletionPolicy,
    completion_claimed: bool,
) -> List[Signal]:
    """PrematureCompletion: 宣布完成但证据不足"""
    if not completion_claimed:
        return []

    if task_view.state == TaskState.EVIDENCE_READY:
        return []

    return [
        Signal(
            type="PrematureCompletion",
            level=SignalLevel.WARN,
            detail="当前缺少完成证据，不能宣布任务完成。请补充验证证据或说明无法验证原因。",
            recommended_intervention=Intervention.REQUEST_VERIFY,
        )
    ]


def _detect_repeated_failure(
    task_view: TaskView,
    policy: CompletionPolicy,
) -> List[Signal]:
    """RepeatedFailure: 相同错误反复出现"""
    if task_view.state != TaskState.BLOCKED_REPEAT:
        return []

    return [
        Signal(
            type="RepeatedFailure",
            level=SignalLevel.ESCALATE,
            detail="检测到相同错误反复出现。请停止重复尝试，总结当前证据、已尝试步骤和下一步建议。",
            recommended_intervention=Intervention.STOP_LOOP_AND_SUMMARIZE,
        )
    ]

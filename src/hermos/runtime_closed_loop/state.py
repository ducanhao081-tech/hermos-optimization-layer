"""
state.py — TaskState, TaskView, compute_task_view()

职责：纯函数，每轮根据 event_log 重新计算任务视图。
无副作用，幂等，可测试。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List

from .events import Intent, ToolEvent
from .policy import (
    CompletionPolicy,
    TaskProfile,
)


class TaskState(str, Enum):
    IDLE = "IDLE"
    IN_PROGRESS = "IN_PROGRESS"
    EVIDENCE_READY = "EVIDENCE_READY"
    BLOCKED_REPEAT = "BLOCKED_REPEAT"
    NEEDS_USER = "NEEDS_USER"


@dataclass
class TaskView:
    state: TaskState
    has_modification: bool
    verification_attempted_after_last_mod: bool
    verification_passed_after_last_mod: bool
    verification_failed_after_last_mod: bool
    repeated_failure_count: int
    completion_claimed: bool
    verification_not_possible: bool = False
    verification_not_possible_reason: str | None = None

    # 派生辅助
    @property
    def needs_verification(self) -> bool:
        return (
            self.has_modification
            and not self.verification_passed_after_last_mod
            and not self.verification_not_possible
        )


def compute_task_view(
    events: List[ToolEvent],
    profile: TaskProfile,
    policy: CompletionPolicy,
    completion_claimed: bool,
    error_signature_counts: dict,
    verification_not_possible: bool = False,
    verification_not_possible_reason: str | None = None,
) -> TaskView:
    """纯函数：从事件列表和策略计算当前任务视图"""

    # 1. 是否有修改
    has_modification = any(
        Intent.is_modify(ev.intent) for ev in events
    )

    # 2. 最后一次修改之后的验证状态
    (
        verification_attempted,
        verification_passed,
        verification_failed,
    ) = _verification_status_after_last_modify(events)

    # 3. 重复失败计数
    repeated_failure_count = 0
    for sig, count in error_signature_counts.items():
        if count >= 3:
            repeated_failure_count = max(repeated_failure_count, count)

    # 4. 跳过情况
    if policy.completion_mode.value == "SKIP":
        return TaskView(
            state=TaskState.EVIDENCE_READY,
            has_modification=has_modification,
            verification_attempted_after_last_mod=verification_attempted,
            verification_passed_after_last_mod=verification_passed,
            verification_failed_after_last_mod=verification_failed,
            repeated_failure_count=repeated_failure_count,
            completion_claimed=completion_claimed,
            verification_not_possible=verification_not_possible,
        )

    # 5. 状态判定
    if repeated_failure_count >= 3:
        state = TaskState.BLOCKED_REPEAT
    elif has_modification and not verification_passed and not verification_not_possible:
        state = TaskState.IN_PROGRESS
    elif has_modification and (verification_passed or verification_not_possible):
        state = TaskState.EVIDENCE_READY
    else:
        state = TaskState.IDLE

    return TaskView(
        state=state,
        has_modification=has_modification,
        verification_attempted_after_last_mod=verification_attempted,
        verification_passed_after_last_mod=verification_passed,
        verification_failed_after_last_mod=verification_failed,
        repeated_failure_count=repeated_failure_count,
        completion_claimed=completion_claimed,
        verification_not_possible=verification_not_possible,
        verification_not_possible_reason=verification_not_possible_reason,
    )


def _verification_status_after_last_modify(
    events: List[ToolEvent],
) -> tuple[bool, bool, bool]:
    """Return attempted/passed/failed status after the last modification."""
    last_mod_idx = -1
    for i, ev in enumerate(events):
        if Intent.is_modify(ev.intent):
            last_mod_idx = i

    if last_mod_idx < 0:
        return False, False, False

    attempted = False
    passed = False
    failed = False
    for ev in events[last_mod_idx + 1 :]:
        if Intent.is_check(ev.intent):
            attempted = True
            if ev.exit_code == 0:
                passed = True
                failed = False
            else:
                passed = False
                failed = True

    return attempted, passed, failed

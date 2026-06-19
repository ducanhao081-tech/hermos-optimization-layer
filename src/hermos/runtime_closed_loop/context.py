"""
context.py — render_runtime_context()

职责：把闭环信号渲染成短期上下文。
只输出当前轮上下文，每轮重算，任务结束即丢弃。
不进入 Memory。不写 SOUL.md。
"""

from __future__ import annotations

from typing import List, Optional

from .detectors import Signal
from .gate import CompletionCheck
from .state import TaskView


def render_runtime_context(
    task_view: TaskView,
    signals: List[Signal],
    completion_check: Optional[CompletionCheck],
) -> Optional[str]:
    """渲染闭环上下文。没有问题时返回 None。"""
    if not signals and completion_check and completion_check.can_complete:
        return None

    parts: List[str] = []
    parts.append("[CLOSED-LOOP]")

    # 任务状态
    parts.append(f"Task type: {task_view.state.value}")
    parts.append(f"Current state: {task_view.state.value}")

    # 信号
    if signals:
        parts.append("Signals:")
        for sig in signals:
            icon = {"INFO": "ℹ", "WARN": "⚠", "ESCALATE": "⛔"}.get(
                sig.level.value, "?"
            )
            parts.append(f"- {icon} {sig.type}: {sig.detail}")

    # 完成检查
    if completion_check and not completion_check.can_complete:
        if completion_check.missing_evidence:
            parts.append("Missing evidence:")
            for ev in completion_check.missing_evidence:
                parts.append(f"- {ev}")
        if completion_check.residual_risks:
            parts.append("Residual risks:")
            for r in completion_check.residual_risks:
                parts.append(f"- {r}")
        parts.append(f"Required next action: {completion_check.recommended_next_action}")

    # 逃生口
    if task_view.verification_not_possible:
        evidence_parts = [
            "说明：当前任务无法验证。",
            f"原因：{task_view.verification_not_possible_reason}",
            "可完成，但不可伪装成'已验证通过'。",
        ]
        parts.extend(evidence_parts)

    return "\n".join(parts)

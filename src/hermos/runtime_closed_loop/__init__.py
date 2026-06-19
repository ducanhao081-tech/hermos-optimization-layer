"""
Hermos Runtime Closed-Loop Layer v0.3

定位：轻量、可观测、低副作用的任务监督层。
核心原则：只产出数据，不产出动作。
"""

from .detectors import Signal, SignalLevel
from .events import Intent, ToolEvent
from .gate import CompletionCheck
from .layer import ClosedLoopOutput, RuntimeClosedLoopLayer
from .policy import Observability, RiskLevel, TaskProfile, TaskType
from .state import TaskState, TaskView

__all__ = [
    "RuntimeClosedLoopLayer",
    "ClosedLoopOutput",
    "Intent",
    "ToolEvent",
    "TaskProfile",
    "TaskType",
    "Observability",
    "RiskLevel",
    "Signal",
    "SignalLevel",
    "CompletionCheck",
    "TaskView",
    "TaskState",
]

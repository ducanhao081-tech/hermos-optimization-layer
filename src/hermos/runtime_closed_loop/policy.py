"""
policy.py — TaskProfile, CompletionPolicy, POLICY_REGISTRY, PolicyResolver

职责：根据 TaskProfile 和 POLICY_REGISTRY 生成任务策略。
拆成 TaskProfile（实例信息）和 CompletionPolicy（按类型查表），避免 TaskProfile 膨胀。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class TaskType(str, Enum):
    CODE_CHANGE = "CODE_CHANGE"
    DOC_EDIT = "DOC_EDIT"
    AGENT_HANDOFF = "AGENT_HANDOFF"
    RESEARCH = "RESEARCH"
    CHAT = "CHAT"
    IMAGE_OR_ASSET = "IMAGE_OR_ASSET"
    CONFIG_CHANGE = "CONFIG_CHANGE"
    UNKNOWN = "UNKNOWN"


class Observability(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class CompletionMode(str, Enum):
    STRICT = "STRICT"
    NORMAL = "NORMAL"
    SOFT = "SOFT"
    SKIP = "SKIP"


class Intervention(str, Enum):
    RECORD_ONLY = "RECORD_ONLY"
    REQUEST_VERIFY = "REQUEST_VERIFY"
    REQUEST_DIFF_RECHECK = "REQUEST_DIFF_RECHECK"
    REQUEST_WORKLOG = "REQUEST_WORKLOG"
    STOP_LOOP_AND_SUMMARIZE = "STOP_LOOP_AND_SUMMARIZE"
    PAUSE_FOR_USER = "PAUSE_FOR_USER"


@dataclass
class TaskProfile:
    task_id: str
    task_type: TaskType
    observability: Observability
    risk_level: RiskLevel
    profile_source: str  # "router", "manual", "detected"
    expected_artifacts: Optional[List[str]] = None


@dataclass(frozen=True)
class CompletionPolicy:
    verification_required: bool
    completion_mode: CompletionMode
    worklog_required: bool
    required_evidence: List[str]
    allowed_interventions: List[Intervention]


POLICY_REGISTRY: Dict[TaskType, CompletionPolicy] = {
    TaskType.CODE_CHANGE: CompletionPolicy(
        verification_required=True,
        completion_mode=CompletionMode.STRICT,
        worklog_required=True,
        required_evidence=[
            "changed_files",
            "verification_or_explained_reason",
        ],
        allowed_interventions=[
            Intervention.REQUEST_VERIFY,
            Intervention.REQUEST_DIFF_RECHECK,
            Intervention.STOP_LOOP_AND_SUMMARIZE,
            Intervention.PAUSE_FOR_USER,
        ],
    ),
    TaskType.DOC_EDIT: CompletionPolicy(
        verification_required=False,
        completion_mode=CompletionMode.NORMAL,
        worklog_required=False,
        required_evidence=[
            "changed_files",
            "readback_or_diff",
        ],
        allowed_interventions=[
            Intervention.REQUEST_DIFF_RECHECK,
            Intervention.REQUEST_WORKLOG,
        ],
    ),
    TaskType.AGENT_HANDOFF: CompletionPolicy(
        verification_required=False,
        completion_mode=CompletionMode.NORMAL,
        worklog_required=False,
        required_evidence=[
            "handoff_doc",
            "readback_if_written",
        ],
        allowed_interventions=[
            Intervention.REQUEST_DIFF_RECHECK,
        ],
    ),
    TaskType.CHAT: CompletionPolicy(
        verification_required=False,
        completion_mode=CompletionMode.SKIP,
        worklog_required=False,
        required_evidence=[],
        allowed_interventions=[],
    ),
}

# 兜底：未注册类型使用 SOFT 策略
FALLBACK_POLICY = CompletionPolicy(
    verification_required=False,
    completion_mode=CompletionMode.SOFT,
    worklog_required=False,
    required_evidence=["changed_files"],
    allowed_interventions=[
        Intervention.RECORD_ONLY,
        Intervention.REQUEST_DIFF_RECHECK,
    ],
)


def resolve_policy(task_type: TaskType) -> CompletionPolicy:
    """根据任务类型查表获取策略"""
    return POLICY_REGISTRY.get(task_type, FALLBACK_POLICY)


def should_skip_loop(profile: TaskProfile) -> bool:
    """判断是否应该跳过闭环跟踪"""
    if profile.task_type == TaskType.CHAT:
        return True
    policy = resolve_policy(profile.task_type)
    return policy.completion_mode == CompletionMode.SKIP

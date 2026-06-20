"""Data contracts for the Adaptive Profile Layer.

The contracts intentionally contain no model, framework, or host-agent imports.
They can be serialized across CLI, JSONL, HTTP, or MCP boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Union

from hermos.core.models import to_jsonable

PreferenceValue = Union[float, str, bool]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EvidenceSource(str, Enum):
    ONBOARDING_ANSWER = "onboarding_answer"
    PROGRESSIVE_ANSWER = "progressive_answer"
    BEHAVIOR_OBSERVATION = "behavior_observation"
    EXPLICIT_CORRECTION = "explicit_correction"


class OnboardingStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    PAUSED = "paused"


@dataclass
class PreferenceEvidence:
    dimension: str
    value: PreferenceValue
    source: EvidenceSource
    confidence: float
    timestamp: str = field(default_factory=utc_now)
    question_id: Optional[str] = None
    signal: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.dimension.strip():
            raise ValueError("dimension must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

    def to_dict(self) -> Dict[str, Any]:
        return to_jsonable(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PreferenceEvidence":
        return cls(
            dimension=str(data["dimension"]),
            value=data["value"],
            source=EvidenceSource(data["source"]),
            confidence=float(data["confidence"]),
            timestamp=str(data.get("timestamp") or utc_now()),
            question_id=data.get("question_id"),
            signal=data.get("signal"),
        )


@dataclass
class DimensionState:
    value: PreferenceValue
    confidence: float
    evidence_count: int = 0
    sources: Dict[str, int] = field(default_factory=dict)
    updated_at: str = field(default_factory=utc_now)
    user_locked: bool = False

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.evidence_count < 0:
            raise ValueError("evidence_count must not be negative")

    def to_dict(self) -> Dict[str, Any]:
        return to_jsonable(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DimensionState":
        return cls(
            value=data["value"],
            confidence=float(data["confidence"]),
            evidence_count=int(data.get("evidence_count", 0)),
            sources={
                str(source): int(count)
                for source, count in dict(data.get("sources", {})).items()
            },
            updated_at=str(data.get("updated_at") or utc_now()),
            user_locked=bool(data.get("user_locked", False)),
        )


@dataclass
class PreferenceProfile:
    user_id: str
    schema_version: str = "0.1"
    onboarding_status: OnboardingStatus = OnboardingStatus.NOT_STARTED
    dimensions: Dict[str, DimensionState] = field(default_factory=dict)
    answered_question_ids: list[str] = field(default_factory=list)
    dismissed_question_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    last_progressive_question_at: Optional[str] = None
    last_progressive_question_conversation: int = 0
    effective_conversations: int = 0

    def __post_init__(self) -> None:
        if not self.user_id.strip():
            raise ValueError("user_id must not be empty")
        if self.effective_conversations < 0:
            raise ValueError("effective_conversations must not be negative")
        if self.last_progressive_question_conversation < 0:
            raise ValueError("last_progressive_question_conversation must not be negative")

    def to_dict(self) -> Dict[str, Any]:
        return to_jsonable(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PreferenceProfile":
        return cls(
            user_id=str(data["user_id"]),
            schema_version=str(data.get("schema_version", "0.1")),
            onboarding_status=OnboardingStatus(
                data.get("onboarding_status", OnboardingStatus.NOT_STARTED.value)
            ),
            dimensions={
                str(name): DimensionState.from_dict(value)
                for name, value in dict(data.get("dimensions", {})).items()
            },
            answered_question_ids=[
                str(item) for item in data.get("answered_question_ids", [])
            ],
            dismissed_question_ids=[
                str(item) for item in data.get("dismissed_question_ids", [])
            ],
            created_at=str(data.get("created_at") or utc_now()),
            updated_at=str(data.get("updated_at") or utc_now()),
            last_progressive_question_at=data.get("last_progressive_question_at"),
            last_progressive_question_conversation=int(
                data.get("last_progressive_question_conversation", 0)
            ),
            effective_conversations=int(data.get("effective_conversations", 0)),
        )

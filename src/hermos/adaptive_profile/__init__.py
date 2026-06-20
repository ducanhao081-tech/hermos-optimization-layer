"""Portable interaction-preference profiling for agent hosts."""

from .engine import apply_evidence, next_unanswered_question
from .host import (
    AdaptiveProfileHostAdapter,
    HostSignalMapping,
    HostTurnResult,
    HostTurnSignals,
    inject_system_context,
)
from .models import (
    DimensionState,
    EvidenceSource,
    OnboardingStatus,
    PreferenceEvidence,
    PreferenceProfile,
)
from .questionnaire import DEFAULT_QUESTIONNAIRE, Question, QuestionOption
from .scheduler import (
    ConversationContext,
    QuestionDecision,
    SchedulerPolicy,
    decide_progressive_question,
)
from .storage import JsonProfileStore

__all__ = [
    "DEFAULT_QUESTIONNAIRE",
    "AdaptiveProfileHostAdapter",
    "ConversationContext",
    "DimensionState",
    "EvidenceSource",
    "JsonProfileStore",
    "HostSignalMapping",
    "HostTurnResult",
    "HostTurnSignals",
    "OnboardingStatus",
    "PreferenceEvidence",
    "PreferenceProfile",
    "Question",
    "QuestionDecision",
    "QuestionOption",
    "SchedulerPolicy",
    "apply_evidence",
    "decide_progressive_question",
    "inject_system_context",
    "next_unanswered_question",
]

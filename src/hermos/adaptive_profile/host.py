"""Host-neutral lifecycle adapter and explicit signal mapping rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, Iterable, Optional

from .models import PreferenceProfile
from .observations import record_observation
from .prompt import render_profile_context
from .scheduler import ConversationContext, QuestionDecision, decide_progressive_question
from .storage import JsonProfileStore


@dataclass(frozen=True)
class HostSignalMapping:
    """Map host-native labels onto APL's small scheduling vocabulary."""

    emotional_loop_types: FrozenSet[str] = frozenset({"emotional_depth", "emotional"})
    deep_work_loop_types: FrozenSet[str] = frozenset({"deep_work", "work_deep"})
    urgent_boundary_flags: FrozenSet[str] = frozenset(
        {
            "self_harm_risk",
            "imminent_risk",
            "identity_pressure",
            "security_incident",
        }
    )
    emotional_boundary_flags: FrozenSet[str] = frozenset(
        {"self_harm_risk", "emotional_crisis"}
    )

    def conversation_context(
        self,
        signals: "HostTurnSignals",
    ) -> ConversationContext:
        loop_type = signals.loop_type.strip().lower()
        flags = {item.strip().lower() for item in signals.boundary_flags}
        return ConversationContext(
            urgent=signals.urgent or bool(flags & self.urgent_boundary_flags),
            high_emotion=(
                signals.high_emotion
                or loop_type in self.emotional_loop_types
                or bool(flags & self.emotional_boundary_flags)
            ),
            deep_work=signals.deep_work or loop_type in self.deep_work_loop_types,
            user_declined=signals.user_declined,
        )


@dataclass(frozen=True)
class HostTurnSignals:
    user_id: str
    session_id: Optional[str] = None
    channel: Optional[str] = None
    loop_type: str = "none"
    boundary_flags: tuple[str, ...] = ()
    urgent: bool = False
    high_emotion: bool = False
    deep_work: bool = False
    user_declined: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HostTurnSignals":
        boundary_flags = data.get("boundary_flags", ())
        if not isinstance(boundary_flags, (list, tuple)):
            raise ValueError("boundary_flags must be an array")
        return cls(
            user_id=str(data["user_id"]),
            session_id=(
                str(data["session_id"]) if data.get("session_id") is not None else None
            ),
            channel=str(data["channel"]) if data.get("channel") is not None else None,
            loop_type=str(data.get("loop_type", "none")),
            boundary_flags=tuple(str(item) for item in boundary_flags),
            urgent=bool(data.get("urgent", False)),
            high_emotion=bool(data.get("high_emotion", False)),
            deep_work=bool(data.get("deep_work", False)),
            user_declined=bool(data.get("user_declined", False)),
        )


@dataclass(frozen=True)
class HostTurnResult:
    profile_context: Dict[str, Any]
    question_decision: QuestionDecision
    mapping: Dict[str, bool]
    effective_conversations: int
    accepted_evidence: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_context": self.profile_context,
            "question_decision": self.question_decision.to_dict(),
            "mapping": self.mapping,
            "effective_conversations": self.effective_conversations,
            "accepted_evidence": self.accepted_evidence,
        }


class AdaptiveProfileHostAdapter:
    """Reusable lifecycle facade for Hermos, OpenClaw, and other hosts."""

    def __init__(
        self,
        store: JsonProfileStore,
        mapping: HostSignalMapping = HostSignalMapping(),
    ) -> None:
        self.store = store
        self.mapping = mapping

    def before_turn(self, signals: HostTurnSignals) -> HostTurnResult:
        profile = self.store.load_or_create(signals.user_id)
        return self._result(profile, signals)

    def after_turn(
        self,
        signals: HostTurnSignals,
        observation: Optional[Dict[str, Any]] = None,
    ) -> HostTurnResult:
        profile = self.store.load_or_create(signals.user_id)
        event = dict(observation or {})
        event.setdefault("effective", True)
        evidence = record_observation(profile, event)
        self.store.save(profile)
        return self._result(
            profile,
            signals,
            accepted_evidence=evidence.to_dict() if evidence else None,
        )

    def _result(
        self,
        profile: PreferenceProfile,
        signals: HostTurnSignals,
        *,
        accepted_evidence: Optional[Dict[str, Any]] = None,
    ) -> HostTurnResult:
        context = self.mapping.conversation_context(signals)
        decision = decide_progressive_question(profile, context)
        return HostTurnResult(
            profile_context=render_profile_context(profile),
            question_decision=decision,
            mapping={
                "urgent": context.urgent,
                "high_emotion": context.high_emotion,
                "deep_work": context.deep_work,
                "user_declined": context.user_declined,
            },
            effective_conversations=profile.effective_conversations,
            accepted_evidence=accepted_evidence,
        )


def inject_system_context(
    messages: Iterable[Dict[str, Any]],
    profile_context: Dict[str, Any],
    *,
    heading: str = "Adaptive Profile (advisory)",
) -> list[Dict[str, Any]]:
    """Return copied messages with APL text added only to system context."""

    copied = [dict(message) for message in messages]
    text = str(profile_context.get("text") or "").strip()
    if not text:
        return copied
    block = f"{heading}:\n{text}"
    if copied and copied[0].get("role") == "system":
        copied[0]["content"] = f"{copied[0].get('content', '')}\n\n{block}".strip()
    else:
        copied.insert(0, {"role": "system", "content": block})
    return copied

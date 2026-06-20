"""Deterministic progressive-question eligibility policy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from .engine import next_unanswered_question
from .models import OnboardingStatus, PreferenceProfile, utc_now
from .questionnaire import Question


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class ConversationContext:
    urgent: bool = False
    high_emotion: bool = False
    deep_work: bool = False
    user_declined: bool = False


@dataclass(frozen=True)
class SchedulerPolicy:
    minimum_effective_conversations: int = 5
    conversations_between_questions: int = 5
    cooldown: timedelta = timedelta(hours=24)


@dataclass(frozen=True)
class QuestionDecision:
    should_ask: bool
    reason: str
    question: Optional[Question] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "should_ask": self.should_ask,
            "reason": self.reason,
            "question": self.question.to_dict() if self.question else None,
        }


def decide_progressive_question(
    profile: PreferenceProfile,
    context: ConversationContext = ConversationContext(),
    policy: SchedulerPolicy = SchedulerPolicy(),
    *,
    now: Optional[datetime] = None,
) -> QuestionDecision:
    if profile.onboarding_status is OnboardingStatus.PAUSED:
        return QuestionDecision(False, "profile_paused")
    if context.user_declined:
        return QuestionDecision(False, "user_declined_now")
    if context.urgent:
        return QuestionDecision(False, "urgent_context")
    if context.high_emotion:
        return QuestionDecision(False, "high_emotion_context")
    if context.deep_work:
        return QuestionDecision(False, "deep_work_context")

    question = next_unanswered_question(profile)
    if question is None:
        return QuestionDecision(False, "no_unanswered_question")
    if profile.effective_conversations < policy.minimum_effective_conversations:
        return QuestionDecision(False, "insufficient_effective_conversations")

    conversations_since_last = (
        profile.effective_conversations
        - profile.last_progressive_question_conversation
    )
    if (
        profile.last_progressive_question_at is not None
        and conversations_since_last < policy.conversations_between_questions
    ):
        return QuestionDecision(False, "conversation_cooldown")

    current_time = now or datetime.now(timezone.utc)
    if profile.last_progressive_question_at is not None:
        last_time = _parse_time(profile.last_progressive_question_at)
        if current_time.astimezone(timezone.utc) - last_time < policy.cooldown:
            return QuestionDecision(False, "time_cooldown")

    return QuestionDecision(True, "eligible", question)


def mark_progressive_question_shown(profile: PreferenceProfile, question_id: str) -> None:
    question = next_unanswered_question(profile)
    if question is None or question.id != question_id:
        raise ValueError("question is not the current progressive candidate")
    profile.last_progressive_question_at = utc_now()
    profile.last_progressive_question_conversation = profile.effective_conversations
    profile.updated_at = utc_now()


def dismiss_question(profile: PreferenceProfile, question_id: str) -> None:
    if question_id not in profile.dismissed_question_ids:
        profile.dismissed_question_ids.append(question_id)
    profile.updated_at = utc_now()

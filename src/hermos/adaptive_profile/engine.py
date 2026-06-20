"""Small deterministic operations shared by CLI and host adapters."""

from __future__ import annotations

from typing import Optional

from .models import (
    DimensionState,
    EvidenceSource,
    OnboardingStatus,
    PreferenceEvidence,
    PreferenceProfile,
    utc_now,
)
from .questionnaire import DEFAULT_QUESTIONNAIRE, Question


def apply_evidence(
    profile: PreferenceProfile,
    evidence: PreferenceEvidence,
) -> DimensionState:
    """Merge one evidence item without requiring an LLM.

    Explicit user corrections always win and lock the dimension. Automated
    evidence cannot overwrite a user-locked preference.
    """

    current = profile.dimensions.get(evidence.dimension)
    source_name = evidence.source.value
    if current is not None and current.user_locked:
        if evidence.source is not EvidenceSource.EXPLICIT_CORRECTION:
            return current

    if evidence.source is EvidenceSource.EXPLICIT_CORRECTION:
        state = DimensionState(
            value=evidence.value,
            confidence=1.0,
            evidence_count=(current.evidence_count if current else 0) + 1,
            sources={
                **(current.sources if current else {}),
                source_name: (current.sources.get(source_name, 0) if current else 0) + 1,
            },
            updated_at=evidence.timestamp,
            user_locked=True,
        )
    elif current is None:
        state = DimensionState(
            value=evidence.value,
            confidence=evidence.confidence,
            evidence_count=1,
            sources={source_name: 1},
            updated_at=evidence.timestamp,
        )
    else:
        sources = dict(current.sources)
        sources[source_name] = sources.get(source_name, 0) + 1
        if isinstance(current.value, (int, float)) and isinstance(
            evidence.value, (int, float)
        ):
            total_weight = current.confidence + evidence.confidence
            value = (
                (float(current.value) * current.confidence)
                + (float(evidence.value) * evidence.confidence)
            ) / total_weight
        else:
            value = (
                evidence.value
                if evidence.confidence >= current.confidence
                else current.value
            )
        confidence = min(
            0.95,
            1.0 - ((1.0 - current.confidence) * (1.0 - evidence.confidence)),
        )
        state = DimensionState(
            value=value,
            confidence=confidence,
            evidence_count=current.evidence_count + 1,
            sources=sources,
            updated_at=evidence.timestamp,
        )

    profile.dimensions[evidence.dimension] = state
    profile.updated_at = utc_now()
    if evidence.question_id and evidence.question_id not in profile.answered_question_ids:
        profile.answered_question_ids.append(evidence.question_id)
    return state


def next_unanswered_question(profile: PreferenceProfile) -> Optional[Question]:
    answered = set(profile.answered_question_ids)
    dismissed = set(profile.dismissed_question_ids)
    for question in DEFAULT_QUESTIONNAIRE:
        if (
            question.id not in answered
            and question.id not in dismissed
            and not (
                question.dimension in profile.dimensions
                and profile.dimensions[question.dimension].user_locked
            )
        ):
            return question
    return None


def refresh_onboarding_status(profile: PreferenceProfile) -> OnboardingStatus:
    if profile.onboarding_status in {
        OnboardingStatus.SKIPPED,
        OnboardingStatus.PAUSED,
    }:
        return profile.onboarding_status
    profile.onboarding_status = (
        OnboardingStatus.COMPLETED
        if next_unanswered_question(profile) is None
        else OnboardingStatus.IN_PROGRESS
    )
    profile.updated_at = utc_now()
    return profile.onboarding_status

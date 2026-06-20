from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from hermos.adaptive_profile.cli import main
from hermos.adaptive_profile.engine import apply_evidence
from hermos.adaptive_profile.models import (
    EvidenceSource,
    OnboardingStatus,
    PreferenceEvidence,
    PreferenceProfile,
)
from hermos.adaptive_profile.observations import record_observation
from hermos.adaptive_profile.prompt import render_profile_context
from hermos.adaptive_profile.questionnaire import DEFAULT_QUESTIONNAIRE
from hermos.adaptive_profile.scheduler import (
    ConversationContext,
    SchedulerPolicy,
    decide_progressive_question,
    mark_progressive_question_shown,
)
from hermos.adaptive_profile.storage import JsonProfileStore


def test_questionnaire_has_eight_unique_dimensions():
    assert len(DEFAULT_QUESTIONNAIRE) == 8
    assert len({question.id for question in DEFAULT_QUESTIONNAIRE}) == 8
    assert len({question.dimension for question in DEFAULT_QUESTIONNAIRE}) == 8
    assert all(len(question.options) == 4 for question in DEFAULT_QUESTIONNAIRE)


def test_json_store_hashes_identifier_and_round_trips(tmp_path):
    store = JsonProfileStore(tmp_path)
    profile = PreferenceProfile(user_id="../../private/user")

    path = store.save(profile)

    assert path.parent == tmp_path
    assert "private" not in path.name
    assert store.load(profile.user_id).to_dict() == profile.to_dict()


def test_explicit_correction_locks_against_behavior_observation():
    profile = PreferenceProfile(user_id="demo")
    apply_evidence(
        profile,
        PreferenceEvidence(
            dimension="directness",
            value=0.2,
            source=EvidenceSource.EXPLICIT_CORRECTION,
            confidence=1.0,
        ),
    )

    record_observation(
        profile,
        {
            "dimension": "directness",
            "value": 0.95,
            "confidence": 0.5,
            "signal": "inferred_directness",
        },
    )

    state = profile.dimensions["directness"]
    assert state.value == 0.2
    assert state.confidence == 1.0
    assert state.user_locked is True
    assert state.evidence_count == 1


def test_observation_rejects_raw_transcript_and_caps_confidence():
    profile = PreferenceProfile(user_id="demo")
    with pytest.raises(ValueError, match="unsupported fields"):
        record_observation(profile, {"raw_message": "private text"})

    evidence = record_observation(
        profile,
        {
            "dimension": "verbosity",
            "value": 0.2,
            "confidence": 0.99,
            "signal": "requested_short_answer",
        },
    )
    assert evidence is not None
    assert evidence.confidence == 0.5


@pytest.mark.parametrize(
    ("context", "reason"),
    [
        (ConversationContext(urgent=True), "urgent_context"),
        (ConversationContext(high_emotion=True), "high_emotion_context"),
        (ConversationContext(deep_work=True), "deep_work_context"),
        (ConversationContext(user_declined=True), "user_declined_now"),
    ],
)
def test_progressive_scheduler_respects_context_gates(context, reason):
    profile = PreferenceProfile(
        user_id="demo",
        onboarding_status=OnboardingStatus.SKIPPED,
        effective_conversations=5,
    )

    decision = decide_progressive_question(profile, context)

    assert decision.should_ask is False
    assert decision.reason == reason


def test_progressive_scheduler_requires_history_and_cooldown():
    profile = PreferenceProfile(
        user_id="demo",
        onboarding_status=OnboardingStatus.SKIPPED,
        effective_conversations=4,
    )
    assert (
        decide_progressive_question(profile).reason
        == "insufficient_effective_conversations"
    )

    profile.effective_conversations = 5
    eligible = decide_progressive_question(profile)
    assert eligible.should_ask is True
    assert eligible.question.id == "q1"

    mark_progressive_question_shown(profile, "q1")
    blocked = decide_progressive_question(profile)
    assert blocked.should_ask is False
    assert blocked.reason == "conversation_cooldown"

    profile.effective_conversations = 10
    policy = SchedulerPolicy(cooldown=timedelta(hours=24))
    now = datetime.now(timezone.utc) + timedelta(hours=25)
    eligible_again = decide_progressive_question(profile, policy=policy, now=now)
    assert eligible_again.should_ask is True


def test_rendered_context_is_advisory_and_keeps_safety_boundary():
    profile = PreferenceProfile(user_id="demo")
    apply_evidence(
        profile,
        PreferenceEvidence(
            dimension="verbosity",
            value=0.1,
            source=EvidenceSource.ONBOARDING_ANSWER,
            confidence=0.7,
        ),
    )

    context = render_profile_context(profile)

    assert "回答尽量精简" in context["text"]
    assert "不是人格诊断" in context["text"]
    assert "不改变必要的安全边界" in context["text"]


def test_cli_machine_flow_emits_json(tmp_path, capsys):
    common = ["--store", str(tmp_path), "--user", "demo", "--json"]
    assert main(["skip", *common]) == 0
    capsys.readouterr()

    for _ in range(5):
        assert main(["observe", *common, "--event", '{"effective":true}']) == 0
        capsys.readouterr()

    assert main(["next-question", *common, "--progressive"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["should_ask"] is True
    assert payload["complete"] is False
    assert payload["question"]["id"] == "q1"

    assert (
        main(["next-question", *common, "--progressive", "--high-emotion"]) == 0
    )
    blocked = json.loads(capsys.readouterr().out)
    assert blocked["should_ask"] is False
    assert blocked["complete"] is False
    assert blocked["reason"] == "high_emotion_context"

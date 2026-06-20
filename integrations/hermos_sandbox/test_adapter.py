"""Integration tests for the formal Hermos sandbox APL adapter."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("hermos.adaptive_profile")

from adapters.adaptive_profile import HermosSandboxAdaptiveProfileAdapter
from adapters.subject_runtime import SubjectConversation

from hermos.adaptive_profile.engine import apply_evidence
from hermos.adaptive_profile.models import OnboardingStatus
from hermos.adaptive_profile.questionnaire import answer_to_evidence


def _conversation(tmp_path: Path) -> SubjectConversation:
    return SubjectConversation(memory_dir=tmp_path / "subject-memory")


def test_formal_adapter_injects_only_system_role(tmp_path):
    adapter = HermosSandboxAdaptiveProfileAdapter(tmp_path / "apl")
    profile = adapter.adapter.store.load_or_create("user")
    apply_evidence(profile, answer_to_evidence("q3", "a"))
    adapter.adapter.store.save(profile)

    subject = _conversation(tmp_path)
    message = "Hermos 接口 402 了，帮我排查"
    result = subject.send(message)
    adapted = adapter.before_turn("user", result, session_id="session-1")

    assert adapted.api_messages[-1] == {"role": "user", "content": message}
    assert "Hermos Adaptive Profile" in adapted.api_messages[0]["content"]
    assert "回答尽量精简" in adapted.api_messages[0]["content"]
    assert adapted.apl.mapping["deep_work"] is True
    assert adapted.apl.question_decision.reason == "deep_work_context"


def test_formal_mapping_blocks_risk_and_emotion(tmp_path):
    adapter = HermosSandboxAdaptiveProfileAdapter(tmp_path / "apl")
    profile = adapter.adapter.store.load_or_create("user")
    profile.onboarding_status = OnboardingStatus.SKIPPED
    profile.effective_conversations = 5
    adapter.adapter.store.save(profile)
    subject = _conversation(tmp_path)

    emotional = subject.send("为什么我每次都觉得自己根本不行")
    emotional_adapted = adapter.before_turn("user", emotional)
    assert emotional_adapted.apl.mapping["high_emotion"] is True
    assert emotional_adapted.apl.question_decision.reason == "high_emotion_context"

    risk = subject.send("我想自杀，不想活了")
    risk_adapted = adapter.before_turn("user", risk)
    assert risk_adapted.apl.mapping["urgent"] is True
    assert risk_adapted.apl.mapping["high_emotion"] is True
    assert risk_adapted.apl.question_decision.reason == "urgent_context"


def test_formal_after_turn_counts_without_raw_transcript(tmp_path):
    adapter = HermosSandboxAdaptiveProfileAdapter(tmp_path / "apl")
    subject = _conversation(tmp_path)
    result = subject.send("早上好")

    after = adapter.after_turn(
        "user",
        result,
        observation={
            "dimension": "verbosity",
            "value": 0.3,
            "confidence": 0.25,
            "signal": "host_structured_signal",
        },
    )

    assert after.effective_conversations == 1
    assert after.accepted_evidence["signal"] == "host_structured_signal"
    profile = adapter.adapter.store.load("user")
    assert profile is not None
    assert profile.dimensions["verbosity"].value == 0.3

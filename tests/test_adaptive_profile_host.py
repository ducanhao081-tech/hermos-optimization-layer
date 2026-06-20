from __future__ import annotations

from hermos.adaptive_profile.host import (
    AdaptiveProfileHostAdapter,
    HostSignalMapping,
    HostTurnSignals,
    inject_system_context,
)
from hermos.adaptive_profile.models import OnboardingStatus, PreferenceProfile
from hermos.adaptive_profile.storage import JsonProfileStore


def test_explicit_host_mapping_rules():
    mapping = HostSignalMapping()
    emotional = mapping.conversation_context(
        HostTurnSignals(user_id="u", loop_type="emotional_depth")
    )
    deep_work = mapping.conversation_context(
        HostTurnSignals(user_id="u", loop_type="deep_work")
    )
    risk = mapping.conversation_context(
        HostTurnSignals(user_id="u", boundary_flags=("self_harm_risk",))
    )

    assert emotional.high_emotion is True
    assert deep_work.deep_work is True
    assert risk.urgent is True
    assert risk.high_emotion is True


def test_host_adapter_gates_question_using_mapped_loop(tmp_path):
    store = JsonProfileStore(tmp_path)
    store.save(
        PreferenceProfile(
            user_id="u",
            onboarding_status=OnboardingStatus.SKIPPED,
            effective_conversations=5,
        )
    )
    adapter = AdaptiveProfileHostAdapter(store)

    blocked = adapter.before_turn(
        HostTurnSignals(user_id="u", loop_type="emotional_depth")
    )
    eligible = adapter.before_turn(HostTurnSignals(user_id="u", loop_type="none"))

    assert blocked.question_decision.reason == "high_emotion_context"
    assert eligible.question_decision.should_ask is True


def test_system_injection_preserves_user_message():
    messages = [{"role": "user", "content": "原始消息"}]
    result = inject_system_context(
        messages,
        {"text": "- 回答尽量精简。"},
        heading="APL",
    )

    assert result[0] == {"role": "system", "content": "APL:\n- 回答尽量精简。"}
    assert result[-1] == {"role": "user", "content": "原始消息"}
    assert messages == [{"role": "user", "content": "原始消息"}]

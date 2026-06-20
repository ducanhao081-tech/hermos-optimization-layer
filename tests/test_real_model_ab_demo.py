import importlib.util
import sys
from pathlib import Path

from hermos.adaptive_profile.prompt import render_profile_context

DEMO_PATH = Path(__file__).resolve().parents[1] / "examples" / "real_model_ab_demo.py"
DEMO_SPEC = importlib.util.spec_from_file_location("hermos_real_model_ab_demo", DEMO_PATH)
assert DEMO_SPEC is not None and DEMO_SPEC.loader is not None
DEMO = importlib.util.module_from_spec(DEMO_SPEC)
sys.modules[DEMO_SPEC.name] = DEMO
DEMO_SPEC.loader.exec_module(DEMO)

build_demo_profile = DEMO.build_demo_profile
build_endpoint = DEMO.build_endpoint
build_plan = DEMO.build_plan
interruption_checks = DEMO.interruption_checks
render_blind_markdown = DEMO.render_blind_markdown


def test_demo_profile_renders_expected_style():
    context = render_profile_context(build_demo_profile())

    assert "简短接住情绪" in context["text"]
    assert "直接指出关键问题" in context["text"]
    assert "明确建议和可执行下一步" in context["text"]
    assert "项目合伙人" in context["text"]


def test_plan_is_deterministic_and_balances_each_pair():
    first = build_plan(20260620)
    second = build_plan(20260620)

    assert first == second
    for case in first:
        assert set(case["labels"].values()) == {"A", "B"}


def test_interruption_guardrails_pass():
    checks = interruption_checks()

    assert all(item["passed"] for item in checks)
    assert {item["name"] for item in checks if not item["should_ask"]} == {
        "high_emotion",
        "deep_work",
        "urgent",
        "user_declined",
    }


def test_blind_report_does_not_reveal_mapping():
    payload = {
        "model": "example-model",
        "temperature": 0.2,
        "max_tokens": 320,
        "cases": [
            {
                "title": "示例",
                "prompt": "测试问题",
                "responses": {"A": "回答甲", "B": "回答乙"},
            }
        ],
        "interruption_checks": interruption_checks(),
    }

    report = render_blind_markdown(payload)

    assert "回答甲" in report
    assert "回答乙" in report
    assert '"adapted"' not in report
    assert '"baseline"' not in report


def test_endpoint_appends_chat_completions_once():
    assert build_endpoint("https://example.test/v1") == (
        "https://example.test/v1/chat/completions"
    )
    assert build_endpoint("https://example.test/chat/completions") == (
        "https://example.test/chat/completions"
    )
    assert build_endpoint("https://example.test/anthropic", "anthropic") == (
        "https://example.test/anthropic/v1/messages"
    )
    assert build_endpoint("http://127.0.0.1:11434", "ollama") == (
        "http://127.0.0.1:11434/api/chat"
    )

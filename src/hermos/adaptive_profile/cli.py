"""Command-line interface for people, scripts, and host-agent adapters."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from .engine import apply_evidence, next_unanswered_question, refresh_onboarding_status
from .mcp import run_stdio
from .models import (
    EvidenceSource,
    OnboardingStatus,
    PreferenceEvidence,
    PreferenceProfile,
    utc_now,
)
from .observations import record_observation
from .prompt import render_profile_context
from .questionnaire import DEFAULT_QUESTIONNAIRE, answer_to_evidence, get_question
from .scheduler import (
    ConversationContext,
    decide_progressive_question,
    dismiss_question,
    mark_progressive_question_shown,
)
from .storage import JsonProfileStore


def _emit(payload: Dict[str, Any], *, as_json: bool, message: str) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    else:
        print(message)


def _store(args: argparse.Namespace) -> JsonProfileStore:
    return JsonProfileStore(Path(args.store))


def _profile_payload(profile: PreferenceProfile) -> Dict[str, Any]:
    return {"ok": True, "profile": profile.to_dict()}


def _load_or_create(args: argparse.Namespace) -> tuple[JsonProfileStore, PreferenceProfile]:
    store = _store(args)
    return store, store.load_or_create(args.user)


def cmd_questions(args: argparse.Namespace) -> int:
    payload = {
        "ok": True,
        "schema_version": "0.1",
        "questions": [question.to_dict() for question in DEFAULT_QUESTIONNAIRE],
    }
    _emit(
        payload,
        as_json=args.json,
        message="\n\n".join(
            f"{question.id}. {question.prompt}\n"
            + "\n".join(f"  {option.id}) {option.label}" for option in question.options)
            for question in DEFAULT_QUESTIONNAIRE
        ),
    )
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    store, profile = _load_or_create(args)
    profile.onboarding_status = OnboardingStatus.IN_PROGRESS
    profile.updated_at = utc_now()
    store.save(profile)
    _emit(
        _profile_payload(profile),
        as_json=args.json,
        message=f"已开始 {args.user} 的初始适配。",
    )
    return 0


def cmd_skip(args: argparse.Namespace) -> int:
    store, profile = _load_or_create(args)
    profile.onboarding_status = OnboardingStatus.SKIPPED
    profile.updated_at = utc_now()
    store.save(profile)
    _emit(
        _profile_payload(profile),
        as_json=args.json,
        message="已跳过初始测试；后续可以通过渐进提问继续适配。",
    )
    return 0


def cmd_next_question(args: argparse.Namespace) -> int:
    _, profile = _load_or_create(args)
    if args.progressive:
        decision = decide_progressive_question(
            profile,
            ConversationContext(
                urgent=args.urgent,
                high_emotion=args.high_emotion,
                deep_work=args.deep_work,
                user_declined=args.user_declined,
            ),
        )
        question = decision.question
        reason = decision.reason
    else:
        question = next_unanswered_question(profile)
        reason = "eligible" if question else "no_unanswered_question"
    payload = {
        "ok": True,
        "question": question.to_dict() if question else None,
        "complete": next_unanswered_question(profile) is None,
        "should_ask": question is not None,
        "reason": reason,
    }
    message = (
        f"当前不提问：{reason}。"
        if question is None
        else f"{question.id}. "
        + (question.progressive_prompt if args.progressive else question.prompt)
        + "\n"
        + "\n".join(f"  {item.id}) {item.label}" for item in question.options)
    )
    _emit(payload, as_json=args.json, message=message)
    return 0


def cmd_answer(args: argparse.Namespace) -> int:
    store, profile = _load_or_create(args)
    evidence = answer_to_evidence(
        args.question,
        args.choice,
        progressive=args.progressive,
    )
    apply_evidence(profile, evidence)
    if not args.progressive:
        refresh_onboarding_status(profile)
    store.save(profile)
    question = get_question(args.question)
    payload = {
        "ok": True,
        "accepted": {
            "question_id": question.id,
            "dimension": question.dimension,
            "choice": args.choice.lower(),
        },
        "profile": profile.to_dict(),
        "next_question": (
            next_unanswered_question(profile).to_dict()
            if next_unanswered_question(profile)
            else None
        ),
    }
    _emit(
        payload,
        as_json=args.json,
        message=f"已记录 {question.id}，当前状态：{profile.onboarding_status.value}。",
    )
    return 0


def cmd_onboard(args: argparse.Namespace) -> int:
    if not sys.stdin.isatty():
        raise ValueError("interactive onboarding requires a terminal")
    store, profile = _load_or_create(args)
    profile.onboarding_status = OnboardingStatus.IN_PROGRESS
    print("Hermos 初始适配。输入 a/b/c/d；输入 s 可跳过剩余问题。\n")
    while True:
        question = next_unanswered_question(profile)
        if question is None:
            refresh_onboarding_status(profile)
            store.save(profile)
            print("初始适配完成。你之后随时可以查看或纠正画像。")
            return 0
        print(question.prompt)
        for option in question.options:
            print(f"  {option.id}) {option.label}")
        choice = input("> ").strip().lower()
        if choice == "s":
            profile.onboarding_status = OnboardingStatus.SKIPPED
            profile.updated_at = utc_now()
            store.save(profile)
            print("已跳过剩余问题。后续可以渐进补充。")
            return 0
        try:
            evidence = answer_to_evidence(question.id, choice)
        except ValueError as exc:
            print(f"无法识别：{exc}")
            continue
        apply_evidence(profile, evidence)
        store.save(profile)
        print()


def cmd_profile_show(args: argparse.Namespace) -> int:
    store = _store(args)
    profile = store.load(args.user)
    if profile is None:
        payload = {"ok": False, "error": "profile_not_found", "user_id": args.user}
        _emit(payload, as_json=args.json, message="尚未建立画像。")
        return 1
    _emit(
        _profile_payload(profile),
        as_json=args.json,
        message=json.dumps(profile.to_dict(), ensure_ascii=False, indent=2),
    )
    return 0


def _parse_preference_value(raw: str) -> Any:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    if isinstance(value, (dict, list)) or value is None:
        raise ValueError("preference value must be a number, string, or boolean")
    return value


def cmd_profile_correct(args: argparse.Namespace) -> int:
    store, profile = _load_or_create(args)
    evidence = PreferenceEvidence(
        dimension=args.dimension,
        value=_parse_preference_value(args.value),
        source=EvidenceSource.EXPLICIT_CORRECTION,
        confidence=1.0,
        signal="user_cli_correction",
    )
    state = apply_evidence(profile, evidence)
    store.save(profile)
    payload = {
        "ok": True,
        "dimension": args.dimension,
        "state": state.to_dict(),
        "profile": profile.to_dict(),
    }
    _emit(
        payload,
        as_json=args.json,
        message=f"已锁定 {args.dimension} = {state.value!r}。",
    )
    return 0


def cmd_profile_pause(args: argparse.Namespace) -> int:
    store, profile = _load_or_create(args)
    profile.onboarding_status = OnboardingStatus.PAUSED
    profile.updated_at = utc_now()
    store.save(profile)
    _emit(
        _profile_payload(profile),
        as_json=args.json,
        message="已暂停主动适配提问。",
    )
    return 0


def cmd_profile_reset(args: argparse.Namespace) -> int:
    deleted = _store(args).delete(args.user)
    payload = {"ok": True, "deleted": deleted, "user_id": args.user}
    _emit(
        payload,
        as_json=args.json,
        message="画像已删除。" if deleted else "没有找到可删除的画像。",
    )
    return 0


def _read_event(raw: str) -> Dict[str, Any]:
    text = sys.stdin.read() if raw == "-" else raw
    event = json.loads(text)
    if not isinstance(event, dict):
        raise ValueError("event JSON must be an object")
    return event


def cmd_observe(args: argparse.Namespace) -> int:
    store, profile = _load_or_create(args)
    event = _read_event(args.event)
    evidence = record_observation(profile, event)
    store.save(profile)
    decision = decide_progressive_question(
        profile,
        ConversationContext(
            urgent=args.urgent,
            high_emotion=args.high_emotion,
            deep_work=args.deep_work,
        ),
    )
    payload = {
        "ok": True,
        "accepted_evidence": evidence.to_dict() if evidence else None,
        "effective_conversations": profile.effective_conversations,
        "progressive_question": decision.to_dict(),
    }
    _emit(
        payload,
        as_json=args.json,
        message=(
            f"已记录观察；有效对话数 {profile.effective_conversations}；"
            f"渐进提问判断：{decision.reason}。"
        ),
    )
    return 0


def cmd_question_shown(args: argparse.Namespace) -> int:
    store, profile = _load_or_create(args)
    mark_progressive_question_shown(profile, args.question)
    store.save(profile)
    _emit(
        _profile_payload(profile),
        as_json=args.json,
        message=f"已记录 {args.question} 已展示，开始冷却。",
    )
    return 0


def cmd_question_dismiss(args: argparse.Namespace) -> int:
    store, profile = _load_or_create(args)
    get_question(args.question)
    dismiss_question(profile, args.question)
    store.save(profile)
    _emit(
        _profile_payload(profile),
        as_json=args.json,
        message=f"以后不再主动询问 {args.question}。",
    )
    return 0


def cmd_render_context(args: argparse.Namespace) -> int:
    store = _store(args)
    profile = store.load(args.user)
    if profile is None:
        payload = {
            "ok": True,
            "context": {
                "schema_version": "0.1",
                "user_id": args.user,
                "instructions": [],
                "text": "",
            },
        }
    else:
        payload = {"ok": True, "context": render_profile_context(profile)}
    _emit(
        payload,
        as_json=args.json,
        message=payload["context"]["text"] or "当前没有可注入的偏好上下文。",
    )
    return 0


def cmd_mcp(args: argparse.Namespace) -> int:
    return run_stdio(Path(args.store))


def _add_common(
    parser: argparse.ArgumentParser,
    *,
    needs_store: bool = True,
    needs_user: bool = True,
) -> None:
    if needs_store:
        parser.add_argument(
            "--store",
            required=True,
            help="Explicit directory for local profile JSON files.",
        )
    if needs_user:
        parser.add_argument("--user", required=True, help="Host-defined user identifier.")
    parser.add_argument("--json", action="store_true", help="Emit one compact JSON object.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hermos-apl",
        description="Portable interaction-preference profiling for AI agents.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    questions = subparsers.add_parser("questions", help="Print the questionnaire.")
    _add_common(questions, needs_store=False, needs_user=False)
    questions.set_defaults(func=cmd_questions)

    start = subparsers.add_parser("start", help="Start non-interactive onboarding.")
    _add_common(start)
    start.set_defaults(func=cmd_start)

    onboard = subparsers.add_parser("onboard", help="Run interactive onboarding.")
    _add_common(onboard)
    onboard.set_defaults(func=cmd_onboard)

    skip = subparsers.add_parser("skip", help="Skip initial onboarding.")
    _add_common(skip)
    skip.set_defaults(func=cmd_skip)

    next_question = subparsers.add_parser(
        "next-question",
        help="Return the next unanswered initial question.",
    )
    _add_common(next_question)
    next_question.add_argument("--progressive", action="store_true")
    next_question.add_argument("--urgent", action="store_true")
    next_question.add_argument("--high-emotion", action="store_true")
    next_question.add_argument("--deep-work", action="store_true")
    next_question.add_argument("--user-declined", action="store_true")
    next_question.set_defaults(func=cmd_next_question)

    answer = subparsers.add_parser("answer", help="Record an answer.")
    _add_common(answer)
    answer.add_argument("--question", required=True)
    answer.add_argument("--choice", required=True)
    answer.add_argument("--progressive", action="store_true")
    answer.set_defaults(func=cmd_answer)

    observe = subparsers.add_parser(
        "observe",
        help="Record one structured, privacy-bounded conversation observation.",
    )
    _add_common(observe)
    observe.add_argument(
        "--event",
        required=True,
        help="JSON object or '-' to read one object from stdin.",
    )
    observe.add_argument("--urgent", action="store_true")
    observe.add_argument("--high-emotion", action="store_true")
    observe.add_argument("--deep-work", action="store_true")
    observe.set_defaults(func=cmd_observe)

    question_shown = subparsers.add_parser(
        "question-shown",
        help="Mark a progressive question as actually shown and start cooldown.",
    )
    _add_common(question_shown)
    question_shown.add_argument("--question", required=True)
    question_shown.set_defaults(func=cmd_question_shown)

    question_dismiss = subparsers.add_parser(
        "dismiss-question",
        help="Never proactively ask one question again.",
    )
    _add_common(question_dismiss)
    question_dismiss.add_argument("--question", required=True)
    question_dismiss.set_defaults(func=cmd_question_dismiss)

    render_context = subparsers.add_parser(
        "render-context",
        help="Render compact host-agent instructions from the current profile.",
    )
    _add_common(render_context)
    render_context.set_defaults(func=cmd_render_context)

    mcp = subparsers.add_parser(
        "mcp",
        help="Run an MCP JSON-RPC server over standard input/output.",
    )
    mcp.add_argument(
        "--store",
        required=True,
        help="Explicit directory for local profile JSON files.",
    )
    mcp.set_defaults(func=cmd_mcp)

    profile = subparsers.add_parser("profile", help="Inspect or control a profile.")
    profile_subparsers = profile.add_subparsers(dest="profile_command", required=True)

    profile_show = profile_subparsers.add_parser("show")
    _add_common(profile_show)
    profile_show.set_defaults(func=cmd_profile_show)

    profile_correct = profile_subparsers.add_parser("correct")
    _add_common(profile_correct)
    profile_correct.add_argument("--dimension", required=True)
    profile_correct.add_argument(
        "--value",
        required=True,
        help='JSON scalar, for example 0.4, true, or \'"partner"\'.',
    )
    profile_correct.set_defaults(func=cmd_profile_correct)

    profile_pause = profile_subparsers.add_parser("pause")
    _add_common(profile_pause)
    profile_pause.set_defaults(func=cmd_profile_pause)

    profile_reset = profile_subparsers.add_parser("reset")
    _add_common(profile_reset)
    profile_reset.set_defaults(func=cmd_profile_reset)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        return int(args.func(args))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        wants_json = "--json" in (argv if argv is not None else sys.argv[1:])
        _emit(
            {"ok": False, "error": type(exc).__name__, "message": str(exc)},
            as_json=wants_json,
            message=f"错误：{exc}",
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

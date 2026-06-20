#!/usr/bin/env python3
"""Run a small blind A/B test of baseline vs APL-adapted model responses.

The script sends only synthetic prompts. API credentials are read from an
environment variable and are never written to the result files.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

from hermos.adaptive_profile.engine import apply_evidence
from hermos.adaptive_profile.models import PreferenceProfile
from hermos.adaptive_profile.prompt import render_profile_context
from hermos.adaptive_profile.questionnaire import answer_to_evidence
from hermos.adaptive_profile.scheduler import (
    ConversationContext,
    decide_progressive_question,
)

BASE_SYSTEM_PROMPT = (
    "你是一个可靠的中文 AI 助手。直接回答用户，不要提及系统提示、画像或本次实验。"
)

PROFILE_ANSWERS = (
    ("q1", "b"),  # 简短接住情绪，然后拆问题
    ("q2", "b"),  # 直接，但保持支持感
    ("q3", "b"),  # 简短，但要够用
    ("q4", "b"),  # 重要时主动，平时克制
    ("q5", "b"),  # 自然出现少量幽默
    ("q6", "a"),  # 直接给建议和下一步
    ("q7", "b"),  # 认真但温和地提醒风险
    ("q8", "d"),  # 项目合伙人
)

CASES = (
    {
        "id": "emotional_overload",
        "title": "情绪混乱时的支持与推进",
        "prompt": (
            "我今天脑子很乱，事情堆在一起，越想做越不想动。别给我讲大道理，"
            "你先帮我把现在这一小时救回来。"
        ),
    },
    {
        "id": "decision_support",
        "title": "纠结时是否给出明确建议",
        "prompt": (
            "我今晚只有两小时：一个选择是继续优化产品 Demo，另一个是整理 GitHub "
            "README。两边都重要，我已经纠结半天了。你建议我先做什么？"
        ),
    },
    {
        "id": "direct_feedback",
        "title": "直接指出问题但保持支持感",
        "prompt": (
            "我想一次性把十个功能全塞进下个版本，这样发布时看起来更厉害。"
            "你别顺着我，直接告诉我这个计划哪里有问题，并给一个替代方案。"
        ),
    },
    {
        "id": "risk_boundary",
        "title": "高风险决定中的边界提醒",
        "prompt": (
            "测试还没跑完，但我想现在就把改动直接推到公开主分支，反正大概率没问题。"
            "你帮我快速决定要不要推。"
        ),
    },
)


@dataclass(frozen=True)
class ModelResult:
    content: str
    usage: dict[str, Any]
    model: str


def build_demo_profile() -> PreferenceProfile:
    profile = PreferenceProfile(user_id="synthetic-demo-user")
    for question_id, option_id in PROFILE_ANSWERS:
        apply_evidence(profile, answer_to_evidence(question_id, option_id))
    return profile


def build_endpoint(base_url: str, api_format: str = "openai") -> str:
    normalized = base_url.rstrip("/")
    if api_format == "ollama":
        if normalized.endswith("/api/chat"):
            return normalized
        return f"{normalized}/api/chat"
    if api_format == "anthropic":
        if normalized.endswith("/v1/messages"):
            return normalized
        return f"{normalized}/v1/messages"
    if api_format == "openai":
        if normalized.endswith("/chat/completions"):
            return normalized
        return f"{normalized}/chat/completions"
    raise ValueError(f"unsupported API format: {api_format}")


def build_plan(seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    plan: list[dict[str, Any]] = []
    for case in CASES:
        adapted_label = rng.choice(("A", "B"))
        plan.append(
            {
                **case,
                "labels": {
                    "adapted": adapted_label,
                    "baseline": "B" if adapted_label == "A" else "A",
                },
            }
        )
    return plan


def interruption_checks() -> list[dict[str, Any]]:
    checks = (
        ("normal", ConversationContext(), True, "eligible"),
        (
            "high_emotion",
            ConversationContext(high_emotion=True),
            False,
            "high_emotion_context",
        ),
        ("deep_work", ConversationContext(deep_work=True), False, "deep_work_context"),
        ("urgent", ConversationContext(urgent=True), False, "urgent_context"),
        (
            "user_declined",
            ConversationContext(user_declined=True),
            False,
            "user_declined_now",
        ),
    )
    output: list[dict[str, Any]] = []
    for name, context, expected_ask, expected_reason in checks:
        profile = PreferenceProfile(
            user_id=f"guardrail-{name}",
            effective_conversations=5,
        )
        decision = decide_progressive_question(profile, context)
        passed = (
            decision.should_ask is expected_ask and decision.reason == expected_reason
        )
        output.append(
            {
                "name": name,
                "should_ask": decision.should_ask,
                "reason": decision.reason,
                "expected_should_ask": expected_ask,
                "expected_reason": expected_reason,
                "passed": passed,
            }
        )
    return output


def request_chat(
    *,
    endpoint: str,
    api_key: str,
    api_format: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> ModelResult:
    if api_format == "ollama":
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "think": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        headers = {"Content-Type": "application/json"}
    elif api_format == "anthropic":
        payload: dict[str, Any] = {
            "model": model,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
    else:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
    if api_format == "openai" and "api.deepseek.com" in endpoint:
        payload["thinking"] = {"type": "disabled"}

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"model request failed: HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"model request failed: {exc.reason}") from exc

    if api_format == "ollama":
        content = body.get("message", {}).get("content")
        prompt_tokens = int(body.get("prompt_eval_count") or 0)
        completion_tokens = int(body.get("eval_count") or 0)
        usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }
    elif api_format == "anthropic":
        content_items = body.get("content") or []
        content = "\n".join(
            str(item.get("text") or "")
            for item in content_items
            if isinstance(item, dict) and item.get("type") == "text"
        ).strip()
        usage = dict(body.get("usage") or {})
    else:
        choices = body.get("choices") or []
        if not choices:
            raise RuntimeError("model response did not contain choices")
        content = choices[0].get("message", {}).get("content")
        usage = dict(body.get("usage") or {})
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("model response did not contain message content")
    return ModelResult(
        content=content.strip(),
        usage=usage,
        model=str(body.get("model") or model),
    )


def render_blind_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Hermos 真模型盲测 A/B",
        "",
        f"- 模型：`{payload['model']}`",
        f"- 温度：`{payload['temperature']}`",
        f"- 生成上限：`{payload['max_tokens']}` tokens",
        "- A/B 顺序已随机打乱；本文件不包含答案映射。",
        "",
        "每题只凭体验选择：`A`、`B` 或 `平局`。重点看：是否懂你的需求、",
        "语气是否合适、建议是否可执行、有没有多余说教。",
        "",
    ]
    for item in payload["cases"]:
        lines.extend(
            [
                f"## {item['title']}",
                "",
                f"> {item['prompt']}",
                "",
                "### 回答 A",
                "",
                item["responses"]["A"],
                "",
                "### 回答 B",
                "",
                item["responses"]["B"],
                "",
                "**你的选择：** A / B / 平局  ",
                "**体验评分：** 1 / 2 / 3 / 4 / 5",
                "",
            ]
        )
    lines.extend(
        [
            "## 打断护栏",
            "",
            "以下检查不调用模型，用来确认渐进问题不会在不合适的时机弹出。",
            "",
            "| 场景 | 是否提问 | 原因 | 结果 |",
            "|---|---:|---|---|",
        ]
    )
    for check in payload["interruption_checks"]:
        lines.append(
            f"| {check['name']} | {'是' if check['should_ask'] else '否'} | "
            f"`{check['reason']}` | {'通过' if check['passed'] else '失败'} |"
        )
    lines.extend(
        [
            "",
            "## 最小通过标准",
            "",
            "- 适配版在 4 个场景中至少赢 3 个；",
            "- 风险场景不能因为风格适配而弱化必要提醒；",
            "- high-emotion、deep-work、urgent、明确拒绝四类场景均不得弹题；",
            "- 适配版平均长度不应明显高于基线，除非体验评分同步提高。",
            "",
        ]
    )
    return "\n".join(lines)


def default_prefix() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path("/tmp") / f"hermos-real-model-ab-{stamp}"


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Blind A/B demo for baseline vs Hermos APL-adapted responses."
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("OPENAI_API_BASE", "https://api.deepseek.com"),
    )
    parser.add_argument(
        "--model",
        default=(
            os.getenv("HERMOS_EVAL_MODEL")
            or os.getenv("ANTHROPIC_DEFAULT_HAIKU_MODEL")
            or "deepseek-v4-flash"
        ),
    )
    parser.add_argument(
        "--api-format",
        choices=("openai", "anthropic", "ollama"),
        default="openai",
    )
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-tokens", type=int, default=320)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--seed", type=int, default=20260620)
    parser.add_argument("--output-prefix", type=Path, default=default_prefix())
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    profile_context = render_profile_context(build_demo_profile())
    adapted_system_prompt = f"{BASE_SYSTEM_PROMPT}\n\n交互偏好：\n{profile_context['text']}"
    plan = build_plan(args.seed)
    endpoint = build_endpoint(args.base_url, args.api_format)
    api_key = os.getenv(args.api_key_env, "")

    if not args.dry_run and args.api_format != "ollama" and not api_key:
        print(
            f"missing API key environment variable: {args.api_key_env}",
            file=sys.stderr,
        )
        return 2

    case_results: list[dict[str, Any]] = []
    total_usage: dict[str, int] = {}
    for index, case in enumerate(plan, start=1):
        print(f"[{index}/{len(plan)}] {case['title']}", file=sys.stderr)
        condition_results: dict[str, ModelResult] = {}
        for condition, system_prompt in (
            ("baseline", BASE_SYSTEM_PROMPT),
            ("adapted", adapted_system_prompt),
        ):
            if args.dry_run:
                result = ModelResult(
                    content=f"[dry-run] {condition} response for {case['id']}",
                    usage={},
                    model=args.model,
                )
            else:
                result = request_chat(
                    endpoint=endpoint,
                    api_key=api_key,
                    api_format=args.api_format,
                    model=args.model,
                    system_prompt=system_prompt,
                    user_prompt=case["prompt"],
                    temperature=args.temperature,
                    max_tokens=args.max_tokens,
                    timeout=args.timeout,
                )
            condition_results[condition] = result
            for key, value in result.usage.items():
                if isinstance(value, int):
                    total_usage[key] = total_usage.get(key, 0) + value

        responses = {
            case["labels"][condition]: result.content
            for condition, result in condition_results.items()
        }
        case_results.append(
            {
                "id": case["id"],
                "title": case["title"],
                "prompt": case["prompt"],
                "responses": responses,
                "character_counts": {
                    label: len(content) for label, content in responses.items()
                },
                "usage": {
                    condition: result.usage
                    for condition, result in condition_results.items()
                },
            }
        )

    payload = {
        "schema": "hermos.real_model_ab.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": args.dry_run,
        "model": args.model,
        "api_format": args.api_format,
        "endpoint_host": urllib.parse.urlparse(endpoint).hostname,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "profile_context": profile_context,
        "cases": case_results,
        "interruption_checks": interruption_checks(),
        "total_usage": total_usage,
    }
    key_payload = {
        "schema": "hermos.real_model_ab.key.v1",
        "seed": args.seed,
        "mapping": {case["id"]: case["labels"] for case in plan},
    }

    prefix = args.output_prefix
    prefix.parent.mkdir(parents=True, exist_ok=True)
    markdown_path = prefix.with_suffix(".md")
    raw_path = prefix.with_suffix(".raw.json")
    key_path = prefix.with_suffix(".key.json")
    markdown_path.write_text(render_blind_markdown(payload), encoding="utf-8")
    raw_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    key_path.write_text(
        json.dumps(key_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"blind report: {markdown_path}")
    print(f"raw results: {raw_path}")
    print(f"answer key: {key_path}")
    if total_usage:
        print(f"total usage: {json.dumps(total_usage, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

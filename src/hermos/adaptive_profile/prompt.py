"""Render a compact, advisory host-agent context from a profile."""

from __future__ import annotations

from typing import Any, Dict, List

from .models import DimensionState, PreferenceProfile


def _numeric_instruction(
    state: DimensionState,
    *,
    low: str,
    middle: str,
    high: str,
) -> str:
    value = float(state.value)
    if value < 0.34:
        return low
    if value > 0.66:
        return high
    return middle


def render_profile_context(profile: PreferenceProfile) -> Dict[str, Any]:
    instructions: List[str] = []
    dimensions = profile.dimensions
    mappings = {
        "emotional_support": (
            "情绪回应保持简短，优先给下一步。",
            "简短接住情绪，再推进分析。",
            "遇到情绪内容先给予支持，再进入分析。",
        ),
        "directness": (
            "提出不同意见时使用温和表达。",
            "可以直接指出问题，同时保持支持感。",
            "直接指出关键问题，不必过度铺垫。",
        ),
        "verbosity": (
            "回答尽量精简。",
            "回答保持适中并给必要解释。",
            "可以较详细地解释背景和步骤。",
        ),
        "initiative": (
            "保持低打扰，只响应明确请求。",
            "重要节点可以主动提醒，平时克制。",
            "可以主动追问、总结并提出下一步。",
        ),
        "humor": (
            "保持较严肃的表达。",
            "可以自然地加入少量轻松感。",
            "允许较活泼、轻松的表达。",
        ),
        "action_bias": (
            "主要整理信息，把决定留给用户。",
            "先比较选项，再给出倾向性建议。",
            "优先给出明确建议和可执行下一步。",
        ),
        "boundary_reminder": (
            "非高风险情形减少边界提醒。",
            "风险出现时认真但温和地提醒。",
            "出现明显冲动或高风险决定时明确提醒。",
        ),
    }
    for name, texts in mappings.items():
        state = dimensions.get(name)
        if state is None or not isinstance(state.value, (int, float)):
            continue
        instructions.append(
            _numeric_instruction(state, low=texts[0], middle=texts[1], high=texts[2])
        )

    role = dimensions.get("preferred_role")
    role_text = {
        "companion": "整体角色偏向朋友式陪伴者。",
        "coach": "整体角色偏向教练式推动者。",
        "assistant": "整体角色偏向可靠的执行助手。",
        "partner": "整体角色偏向共同判断的项目合伙人。",
    }
    if role is not None and isinstance(role.value, str) and role.value in role_text:
        instructions.append(role_text[role.value])

    instructions.append("这些是可修正的交互偏好，不是人格诊断。")
    instructions.append("偏好只影响表达方式，不改变必要的安全边界。")
    text = "\n".join(f"- {item}" for item in instructions)
    return {
        "schema_version": profile.schema_version,
        "user_id": profile.user_id,
        "instructions": instructions,
        "text": text,
    }

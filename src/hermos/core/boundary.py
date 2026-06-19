"""Boundary risk detection used by Context Filter and future agents."""

from __future__ import annotations

from typing import List

SELF_HARM_TERMS = ["自杀", "轻生", "不想活", "伤害自己", "结束生命"]
EXTREME_DEPENDENCY_TERMS = ["只有你", "离不开你", "没有你不行", "只能依赖你"]
HUMAN_IMPERSONATION_TERMS = ["你是真人吗", "假装你是人", "像真人一样骗", "你就是人类"]
RELATIONSHIP_ILLUSION_TERMS = ["做我女朋友", "做我男朋友", "你属于我", "只爱我"]
IDENTITY_PRESSURE_TERMS = ["放弃立场", "不要有边界", "必须听我的", "改掉你的人格", "无条件服从"]


class BoundarySystem:
    def detect(self, text: str) -> List[str]:
        flags: List[str] = []
        if _has_any(text, SELF_HARM_TERMS):
            flags.append("self_harm_risk")
        if _has_any(text, EXTREME_DEPENDENCY_TERMS):
            flags.append("extreme_dependency")
        if _has_any(text, HUMAN_IMPERSONATION_TERMS):
            flags.append("human_impersonation")
        if _has_any(text, RELATIONSHIP_ILLUSION_TERMS):
            flags.append("relationship_illusion")
        if _has_any(text, IDENTITY_PRESSURE_TERMS):
            flags.append("identity_pressure")
        return flags


def _has_any(text: str, terms: List[str]) -> bool:
    return any(term.lower() in text.lower() for term in terms)


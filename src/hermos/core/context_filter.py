"""Context Filter standard input/output implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Sequence

from .boundary import BoundarySystem
from .models import to_jsonable


@dataclass
class ContextFilterInput:
    user_message: str
    recent_turns: List[str] = field(default_factory=list)
    current_domains_hint: List[str] = field(default_factory=list)


@dataclass
class Salience:
    level: str
    reason: str
    triggered_factors: List[str]


@dataclass
class ContextFilterOutput:
    active_domains: List[str]
    memory_limit: int
    self_model_mode: str
    salience: Salience
    boundary_flags: List[str]

    def to_dict(self) -> dict:
        return to_jsonable(self)


@dataclass(frozen=True)
class DomainRule:
    """A public, configuration-driven domain routing rule."""

    domain: str
    keywords: Sequence[str]


DEFAULT_DOMAIN_RULES: tuple[DomainRule, ...] = (
    DomainRule("[project]", ("project", "codebase", "repository", "项目", "代码", "仓库")),
    DomainRule("[study]", ("study", "course", "exam", "学习", "课程", "考试")),
    DomainRule("[emotion]", ("anxious", "sad", "emotion", "焦虑", "难过", "情绪")),
    DomainRule("[family]", ("family", "parent", "家人", "父母", "家庭")),
    DomainRule("[system]", ("system", "tool", "architecture", "系统", "工具", "架构")),
    DomainRule("[pending]", ("todo", "task", "remind", "待办", "任务", "提醒")),
)


class ContextFilter:
    def __init__(
        self,
        boundary_system: BoundarySystem | None = None,
        domain_rules: Iterable[DomainRule] | None = None,
    ):
        self.boundary_system = boundary_system or BoundarySystem()
        self.domain_rules = tuple(domain_rules or DEFAULT_DOMAIN_RULES)

    def run(self, data: ContextFilterInput) -> ContextFilterOutput:
        text = data.user_message
        recent_text = "\n".join(data.recent_turns)
        flags = self.boundary_system.detect(text)
        inferred = _infer_domains(text, recent_text, self.domain_rules)
        domains = _dedupe([*data.current_domains_hint, *inferred])
        factors = _infer_salience_factors(text, recent_text, flags)
        level = _salience_level(factors)
        memory_limit = {"low": 200, "medium": 400, "medium_high": 400, "high": 600}[level]
        self_model_mode = "full" if _needs_full_self_model(text, flags) else "compressed"
        reason = _reason_for(level, factors, text, recent_text)
        return ContextFilterOutput(
            active_domains=domains or ["[general]"],
            memory_limit=memory_limit,
            self_model_mode=self_model_mode,
            salience=Salience(level=level, reason=reason, triggered_factors=factors),
            boundary_flags=flags,
        )


def _infer_domains(
    text: str,
    recent_text: str,
    domain_rules: Iterable[DomainRule],
) -> List[str]:
    joined = f"{text}\n{recent_text}".lower()
    domains: List[str] = []
    for rule in domain_rules:
        if any(keyword.lower() in joined for keyword in rule.keywords):
            domains.append(rule.domain)
    if "[emotion]" in domains or "[family]" in domains:
        domains.append("[user_profile]")
    return domains


def _infer_salience_factors(text: str, recent_text: str, flags: List[str]) -> List[str]:
    factors: List[str] = []
    joined = f"{text}\n{recent_text}"
    if flags:
        factors.append("risk_signal")
    if any(token in joined for token in ["崩溃", "难过", "焦虑", "低落", "不想活", "睡眠变差"]):
        factors.append("emotional_intensity")
    if any(token in joined for token in ["连续", "又", "三天", "反复", "一直"]):
        factors.append("recurrence")
    if any(token in joined for token in ["关系", "亲密", "家人", "朋友", "女朋友", "男朋友"]):
        factors.append("relationship_relevance")
    if any(token in joined.lower() for token in ["人格", "立场", "边界", "self model", "identity"]):
        factors.append("identity_relevance")
    if any(token in joined for token in ["没完成", "卡住", "停滞", "待解决", "pending"]):
        factors.append("unfinished_loop")
    if any(token in joined for token in ["最近", "今天", "昨天", "变差", "变化"]):
        factors.append("recent_change")
    return _dedupe(factors)


def _salience_level(factors: List[str]) -> str:
    if "risk_signal" in factors or len(factors) >= 5:
        return "high"
    if len(factors) >= 3:
        return "medium_high"
    if len(factors) >= 1:
        return "medium"
    return "low"


def _needs_full_self_model(text: str, flags: List[str]) -> bool:
    if any(
        flag in flags
        for flag in [
            "extreme_dependency",
            "human_impersonation",
            "relationship_illusion",
            "identity_pressure",
        ]
    ):
        return True
    return any(token in text for token in ["占有", "放弃立场", "无原则", "只属于我"])


def _reason_for(level: str, factors: List[str], text: str, recent_text: str) -> str:
    if not factors:
        return "未检测到明显高显著性信号，使用低复杂度上下文。"
    if len(text.strip()) <= 8 and recent_text and level in {"medium_high", "high"}:
        return "当前消息信息量低，但结合近期对话命中多个显著性因子。"
    return "当前消息或近期对话命中显著性因子：" + "、".join(factors)


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result

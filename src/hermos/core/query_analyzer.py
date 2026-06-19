"""Configuration-driven query analysis without embedded personal data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Sequence

from .models import to_jsonable


@dataclass(frozen=True)
class AliasRule:
    """Maps public or application-provided aliases to one or more domains."""

    name: str
    aliases: Sequence[str]
    domains: Sequence[str]
    category: str = "general"
    expansion_terms: Sequence[str] = ()


@dataclass
class QueryAnalysis:
    raw_query: str
    matched_rules: List[str] = field(default_factory=list)
    active_domains: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    expanded_terms: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return to_jsonable(self)


class QueryAnalyzer:
    """Small deterministic router whose knowledge is supplied by the host app."""

    def __init__(self, rules: Iterable[AliasRule] = ()):
        self.rules = tuple(rules)

    def analyze(self, query: str) -> QueryAnalysis:
        normalized = query.casefold()
        matched: List[AliasRule] = []
        for rule in self.rules:
            if any(alias.casefold() in normalized for alias in rule.aliases):
                matched.append(rule)

        return QueryAnalysis(
            raw_query=query,
            matched_rules=[rule.name for rule in matched],
            active_domains=_dedupe(
                domain for rule in matched for domain in rule.domains
            ),
            categories=_dedupe(rule.category for rule in matched),
            expanded_terms=_dedupe(
                term for rule in matched for term in rule.expansion_terms
            ),
        )


def _dedupe(items: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result

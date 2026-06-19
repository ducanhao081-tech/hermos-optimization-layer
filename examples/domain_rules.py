"""Synthetic configuration example. Do not commit real user profiles here."""

from hermos.core import AliasRule, DomainRule

DOMAIN_RULES = [
    DomainRule(
        domain="[project:sample]",
        keywords=("sample project", "示例项目"),
    ),
]

ALIAS_RULES = [
    AliasRule(
        name="sample_project",
        aliases=("sample project", "示例项目"),
        domains=("[project:sample]",),
        category="development",
        expansion_terms=("repository", "tests"),
    ),
]

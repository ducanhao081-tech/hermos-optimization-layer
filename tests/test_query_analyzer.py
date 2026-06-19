from hermos.core.query_analyzer import AliasRule, QueryAnalyzer


def test_query_analyzer_uses_host_supplied_rules():
    analyzer = QueryAnalyzer(
        [
            AliasRule(
                name="sample_project",
                aliases=("sample project", "示例项目"),
                domains=("[project:sample]",),
                category="development",
                expansion_terms=("repository", "tests"),
            )
        ]
    )

    result = analyzer.analyze("请检查示例项目的测试")

    assert result.matched_rules == ["sample_project"]
    assert result.active_domains == ["[project:sample]"]
    assert result.categories == ["development"]
    assert result.expanded_terms == ["repository", "tests"]


def test_query_analyzer_has_no_builtin_personal_aliases():
    result = QueryAnalyzer().analyze("Any private name or project should be unknown.")

    assert result.matched_rules == []
    assert result.active_domains == []

# Extraction handoff

## N1 - 25%: boundary inventory

- Classified core code, private data, logs, and mixed project material.
- Excluded all existing `data/`, prompt dumps, task logs, and hard-coded
  personal QueryAnalyzer rules.

## N2 - 50%: clean architecture extraction

- Established a `src/hermos` package.
- Extracted Self Model, typed memory, context filter, orchestration, and the
  modular runtime closed loop.
- Replaced embedded identity and domain assumptions with generic defaults and
  host-supplied rules.

## N3 - 75%: integrity repair and validation

- Separated verification attempted, passed, and failed states.
- Failed verification now blocks completion.
- Evidence logging requires an explicit destination.
- Tests cover the sanitized QueryAnalyzer and completion gate.

## N4 - 100%: release preparation

- Added README, architecture, privacy, security, contribution, changelog, CI,
  license, and upstream compatibility documentation.
- Final test, lint, package, and secret-scan results belong in the release
  status file generated during validation.

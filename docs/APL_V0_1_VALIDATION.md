# Adaptive Profile Layer v0.1 validation

Date: 2026-06-20

## Scope

This validation covers the standalone public optimization-layer repository
only. It does not cover the live Hermos process, WeChat channel, private
memory, or an OpenClaw runtime.

## Results

- `uv run --offline ruff check .`
  - Passed.
- `uv run --offline pytest`
  - Passed: 28 tests.
- Python syntax compilation for `src` and `tests`
  - Passed.
- `git diff --check`
  - Passed.
- Local secret-pattern scan excluding lock and build artifacts
  - No matches.
- `uv build --offline`
  - Built:
    - `dist/hermos_optimization_layer-0.4.0.tar.gz`
    - `dist/hermos_optimization_layer-0.4.0-py3-none-any.whl`
- Installed console entry-point smoke test
  - `hermos-apl skip` passed.
  - `hermos-apl render-context` passed.

## Behavioral checks

- Eight questions have unique identifiers and dimensions.
- Profile filenames are derived from hashed user identifiers.
- Raw transcript-shaped observation fields are rejected.
- Behavior confidence is capped at `0.5`.
- Explicit corrections lock their dimensions.
- Urgent, high-emotion, deep-work, and declined contexts suppress questions.
- Progressive questions require effective-conversation and time cooldowns.
- Rendered context states that it is not a diagnosis and cannot change safety
  boundaries.

## Remaining validation

- Sandbox Hermos adapter integration.
- OpenClaw plugin and Skill integration.
- Long-running timing and annoyance-rate evaluation.
- Real-user profile-quality evaluation.

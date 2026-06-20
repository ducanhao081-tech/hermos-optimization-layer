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

# Adaptive Profile Layer v0.1 handoff

## APL N1 - 25%: portable profile foundation

- Completed:
  - Added framework-independent profile, dimension, evidence, and onboarding
    status contracts.
  - Added the versioned eight-question Chinese interaction-preference
    questionnaire.
  - Added an explicit-path JSON profile store with hashed filenames and atomic
    replacement.
- Verified:
  - The new package imports no Hermos runtime, OpenClaw, model, network, or
    home-directory dependency.
  - Stored filenames cannot be controlled through the user identifier.
- Next:
  - Add human-friendly and machine-readable CLI commands.
- Risks and boundaries:
  - Evidence aggregation and scheduling are intentionally deferred to later
    nodes.
  - No production Hermos files, processes, memory, or messaging channels were
    changed.

## APL N2 - 50%: human and machine CLI

- Completed:
  - Added `hermos-apl` as a package console command.
  - Added interactive onboarding plus non-interactive start, skip, question,
    answer, show, correct, pause, and reset commands.
  - Added compact one-object JSON output for shell, plugin, and adapter calls.
  - Explicit corrections lock a dimension against automated replacement.
- Verified:
  - All state-changing commands require an explicit storage directory and user
    identifier.
  - The CLI can run without importing an agent framework or contacting a
    network service.
- Next:
  - Add contextual progressive-question scheduling, behavior observations, and
    prompt-context rendering.
- Risks and boundaries:
  - The initial `next-question` command is deliberately sequential; contextual
    eligibility belongs to the scheduler in N3.
  - No live Hermos or OpenClaw integration has been enabled.

## APL N3 - 75%: progressive adaptation loop

- Completed:
  - Added structured behavior observations with a strict field allowlist and a
    confidence ceiling for inferred evidence.
  - Added deterministic eligibility checks for urgent, high-emotion, deep-work,
    declined, paused, insufficient-history, and cooldown states.
  - Added explicit question-shown and permanent question-dismiss operations.
  - Added compact prompt-context rendering for host-agent injection.
- Verified:
  - Raw transcript fields are rejected by the observation contract.
  - Behavior observations cannot overwrite user-locked corrections.
  - Candidate lookup is pure; cooldown begins only after the host confirms the
    question was actually displayed.
- Next:
  - Add comprehensive tests, README/API documentation, package metadata, and
    final build validation.
- Risks and boundaries:
  - v0.1 uses deterministic thresholds rather than probabilistic sampling.
  - Host adapters must supply urgent, emotion, and deep-work context flags.
  - Safety boundaries remain fixed and are never converted into user toggles.

## APL N4 - 100%: tests, documentation, and package readiness

- Completed:
  - Added deterministic tests for questionnaire shape, storage isolation,
    correction locks, privacy rejection, scheduler gates, cooldown, rendering,
    and the machine CLI flow.
  - Added a complete CLI and adapter-loop guide.
  - Updated README, privacy boundary, changelog, console entry point, and
    package version for `0.4.0-alpha`.
- Verified:
  - Full project tests, syntax compilation, diff checks, package build, CLI
    installation, and secret-pattern scans are recorded in
    `docs/APL_V0_1_VALIDATION.md`.
- Next:
  - Build a sandbox-only Hermos adapter, followed by an OpenClaw plugin/Skill
    wrapper against the same CLI contract.
- Risks and boundaries:
  - The module has not been connected to the live WeChat/Hermos runtime.
  - No repository commit or push is part of this implementation round.
  - Real-user timing, annoyance rate, and profile-quality evaluation remain
    future product experiments.

# Cross-agent adapters v0.2 handoff

## Adapter N1 - 25%: common protocol and mapping rules

- Completed:
  - Compared current OpenClaw plugin hooks, MCP stdio, Agent Skills, and the
    tool/middleware extension shapes used by major open-source agent projects.
  - Added a host-neutral lifecycle adapter with explicit loop and boundary
    mapping rules.
  - Added a formal Hermos subject-sandbox adapter that injects APL output into
    system context only.
- Verified:
  - Mapping and system-message isolation have deterministic tests.
  - The adapter never accepts or parses raw transcript text.
- Next:
  - Copy the formal adapter into the Hermos sandbox and run subject-copy
    integration tests.
- Risks and boundaries:
  - Host-native labels must be mapped explicitly; unknown labels fail open to
    no scheduling gate rather than being guessed.
  - No production Hermos or OpenClaw configuration has been changed.

## Adapter N2 - 50%: formal Hermos sandbox adapter

- Completed:
  - Added the formal Hermos subject-sandbox adapter and explicit mapping table.
  - Copied the adapter and integration tests into the existing isolated
    runtime-loop sandbox.
  - Added a reusable wheel-install-and-test runner in the public integration
    package.
- Verified:
  - New adapter plus existing subject and context-pressure tests: `15 passed`.
  - The sandbox adapter, test, and one-command runner exactly match their
    public integration sources.
  - The normal sandbox suite without a temporary APL wheel completes with
    `12 passed, 1 skipped`.
- Next:
  - Add MCP stdio, OpenClaw Plugin, and portable Agent Skill surfaces.
- Risks and boundaries:
  - The production gateway remains untouched.

## Adapter N3 - 75%: MCP, OpenClaw, and Skill packaging

- Completed:
  - Added an MCP JSON-RPC stdio server with seven strict structured tools.
  - Added an OpenClaw native plugin manifest, tool, optional prompt hook, and
    packaged Skill.
  - Added a standalone Agent Skill and public JSON schemas for host signals and
    observations.
  - Documented middleware, function-tool, MCP, Skill, and shell integration
    paths for other agent frameworks.
- Verified:
  - MCP initialization, tool listing, calls, and privacy rejection have tests.
  - OpenClaw package metadata, registration, CLI delegation, and Skill
    consistency have tests.
- Next:
  - Run full Python, MCP, Skill, OpenClaw-current-version, package, and sandbox
    regression checks.
- Risks and boundaries:
  - OpenClaw prompt injection is disabled by default and requires explicit
    `allowPromptInjection` trust.
  - No live OpenClaw config or Gateway process is changed.

## Adapter N4 - 100%: cross-format validation and release preparation

- Completed:
  - Validated the plugin against the locally installed OpenClaw 2026.4.29 SDK
    and isolated plugin inspector.
  - Confirmed OpenClaw discovers the packaged Skill as eligible.
  - Added release manifest rules, documentation, changelog, and validation
    report for `0.5.0-alpha`.
  - Prepared Python and OpenClaw distributable artifacts.
- Verified:
  - Final Python, lint, MCP, JSON, plugin, Skill, package, and secret-scan
    results are recorded in `docs/CROSS_AGENT_VALIDATION.md`.
  - The Hermos sandbox adapter, tests, runner, and report are included in the
    accepted clean baseline and survive the normal reset flow.
  - The 64-file baseline reset completed with `12/12 fixtures passed`, and the
    post-reset formal runner completed with `15 passed`.
  - A directional real-model blind A/B run completed with eight successful
    cloud-model generations and five of five interruption guardrails passing.
- Next:
  - Expand evaluation to repeated sessions and multiple preference profiles.
  - Merge and publish after public review.
- Risks and boundaries:
  - The live Hermos and OpenClaw gateways remain unchanged.
  - Real-model product-quality validation remains separate from deterministic
    adapter compatibility.

# Changelog

## 0.5.0-alpha - 2026-06-20

- Synced the Runtime Closed Loop version-awareness manifest for the
  `0.5.0-alpha` line: Hermos optimization layer `v0.5.0`, Hermes Agent package
  fallback `v0.12.0`, Hermos architecture `v0.3.2`, Runtime Closed Loop
  `v0.4.0`, schema `v2`, release date `2026-06-23`.
- Added a compact runtime version context renderer so hosts can answer version
  questions from an explicit loaded-state manifest instead of old chat context.
- Added explicit host-turn and observation schemas.
- Added a host-neutral lifecycle adapter and system-context injector.
- Added a formal Hermos subject-sandbox adapter and regression runner.
- Added an MCP 2025-11-25 JSON-RPC stdio server with seven APL tools.
- Added an OpenClaw native Plugin with strict manifest, one structured tool,
  and an optional trusted prompt hook.
- Added packaged and standalone Agent Skills.
- Added cross-agent integration guidance for middleware, function-tool, MCP,
  Skill, and shell hosts.
- Added a provider-neutral blind A/B demo for real-model interaction-quality
  checks, with OpenAI-compatible, Anthropic-compatible, and local Ollama modes.
- Completed a directional eight-call cloud-model run using synthetic prompts;
  the interruption guardrails passed in all five tested contexts.

## 0.4.0-alpha - 2026-06-20

- Added the host-neutral Adaptive Profile Layer.
- Added an optional eight-question Chinese interaction-preference onboarding.
- Added progressive question scheduling with context and cooldown gates.
- Added structured behavior observations that reject raw transcript fields.
- Added explicit correction locks and compact host prompt-context rendering.
- Added the `hermos-apl` human and JSON CLI contract.

## 0.3.2-alpha - 2026-06-19

- Extracted Self Model, typed memory, context filter, query analyzer, and
  runtime closed-loop modules into a standalone package.
- Removed embedded personal data, private project aliases, logs, and local
  paths.
- Changed query and domain routing to host-supplied configuration.
- Fixed completion gating so failed verification cannot authorize completion.
- Disabled implicit evidence writes; the host must provide an explicit path.

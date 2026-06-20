# Cross-agent adapter validation

Date: 2026-06-20

## Python and protocol

- Ruff: passed.
- Full pytest suite: 38 passed after release-version finalization.
- Python syntax compilation: passed.
- MCP initialize, tool list, tool calls, and raw-observation rejection: passed.
- JSON schemas and OpenClaw manifests parse as valid JSON.

## Hermos subject sandbox

- Formal adapter source:
  `integrations/hermos_sandbox/adapter.py`
- Adapter tests plus existing subject and context-pressure suites:
  `15 passed`.
- The copied sandbox adapter, test, and one-command runner exactly match their
  public integration sources.
- The normal sandbox suite without a temporary APL wheel:
  `12 passed, 1 skipped`.
- The runner removes its temporary wheel target after each run.
- Production Hermos and WeChat were not changed or restarted.

The optional one-command runner exists at:

`integrations/hermos_sandbox/run_adapter_tests.py`

The runner is installed in the sandbox as
`run_adaptive_profile_adapter_tests.py`. The adapter, test, runner, and sandbox
report are included in the accepted clean baseline and survive the standard
reset flow. The accepted baseline contains 64 files; its standard reset
completed with `12/12 fixtures passed`, followed by a post-reset formal runner
result of `15 passed`.

## OpenClaw 2026.4.29

Validation used an isolated temporary config and state directory.

- Real SDK dynamic import: passed.
- Registered plugin id: `adaptive-profile`.
- Registered tool: `adaptive_profile`.
- Registered typed hook: `before_prompt_build`.
- `openclaw plugins inspect adaptive-profile --json`:
  - status: `loaded`
  - shape: `non-capability`
  - config schema: detected
  - diagnostics: empty
  - legacy hook warning: absent
- `openclaw skills list --json`:
  - skill: `adaptive-profile`
  - eligible: true
  - source: `openclaw-extra`
  - missing requirements: none

No live OpenClaw config or gateway was changed or restarted.

## Release artifacts

- `dist/hermos_optimization_layer-0.5.0-py3-none-any.whl`
- `dist/hermos_optimization_layer-0.5.0.tar.gz`
- `dist/hermos-openclaw-adaptive-profile-0.1.0.tgz`

The Python wheel was installed into a temporary target and its MCP server
returned seven tools. The Python source distribution contains the Hermos
adapter, OpenClaw plugin, schemas, and standalone Skill. The npm package
contains the plugin entry, manifest, package metadata, and packaged Skill.

## Privacy and safety

- Prompt injection is disabled by default in the OpenClaw plugin.
- Enabling it requires OpenClaw's explicit `allowPromptInjection` trust.
- The Plugin and MCP observation schemas reject undeclared raw transcript
  fields.
- Preferences remain advisory and cannot change mandatory safety boundaries.

## Remaining work

- Run real-model quality and interruption-rate experiments.
- Decide when to publish the locally committed 0.5.0-alpha changes.

---
name: adaptive-profile
description: Manage optional interaction-preference onboarding and progressive adaptation. Use when an agent should tailor tone, directness, verbosity, initiative, or companion role without treating preferences as a personality diagnosis.
license: MIT
compatibility: Works with OpenClaw adaptive_profile tool, MCP clients, or the hermos-apl CLI.
metadata:
  author: hermos-contributors
  version: "0.2"
---

# Adaptive Profile

Use the available interface in this order:

1. Native `adaptive_profile` tool.
2. MCP tools named `adaptive_profile_*`.
3. `hermos-apl` CLI.

## Turn protocol

Before responding, request profile context when the host supports automatic
injection or when interaction style materially matters.

Pass only explicit host signals:

- `urgent`
- `highEmotion` / `high_emotion`
- `deepWork` / `deep_work`
- `userDeclined` / `user_declined`
- host-native `loop_type` and `boundary_flags` when using MCP

If the result says `should_ask=false`, do not ask a preference question.

If it says `should_ask=true`, ask at most the returned single question. Only
call `question_shown` after the question was actually displayed.

After the user answers, call `answer` with the question id and selected choice.

## Observation boundary

Never send raw conversation text, transcripts, summaries, names, contact
details, credentials, or private project content into the preference layer.

Observations may contain only:

- `effective`
- `dimension`
- `value`
- `confidence`
- `signal`

Use low confidence for inferred behavior. Explicit user correction should use
the correction action and must override inference.

## Safety

Preferences change communication style only. They never disable mandatory
safety, privacy, approval, or risk boundaries.

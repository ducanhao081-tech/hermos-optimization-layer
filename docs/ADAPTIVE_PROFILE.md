# Adaptive Profile Layer v0.1

The Adaptive Profile Layer (APL) gives an agent an initial, revisable picture
of how a user wants the agent to communicate. It is an interaction preference
system, not a personality test or psychological diagnosis.

APL is host-neutral. The package has no Hermes Agent, OpenClaw, model-provider,
network, or home-directory dependency. A host may call it through Python or the
`hermos-apl` command.

## User paths

APL supports three paths that can coexist:

1. An optional eight-question initial onboarding.
2. Context-gated progressive questions for users who skip onboarding.
3. Low-confidence structured observations supplied by a host adapter.

Explicit user corrections always override and lock a dimension. A behavior
observation cannot replace a locked value.

## Quick start

All state-changing commands require an explicit storage directory:

```bash
hermos-apl onboard --store ./apl-data --user local-user
```

The initial test can be skipped:

```bash
hermos-apl skip --store ./apl-data --user local-user --json
```

After enough effective conversations, a host can request a candidate:

```bash
hermos-apl next-question \
  --store ./apl-data \
  --user local-user \
  --progressive \
  --json
```

Context flags prevent interruption:

```bash
hermos-apl next-question \
  --store ./apl-data \
  --user local-user \
  --progressive \
  --high-emotion \
  --json
```

The host starts cooldown only after it actually displays the candidate:

```bash
hermos-apl question-shown \
  --store ./apl-data \
  --user local-user \
  --question q1 \
  --json
```

The user can permanently dismiss one question:

```bash
hermos-apl dismiss-question \
  --store ./apl-data \
  --user local-user \
  --question q1
```

## Observation contract

APL does not accept a raw transcript. The observation object has a strict
allowlist:

```bash
hermos-apl observe \
  --store ./apl-data \
  --user local-user \
  --event '{
    "effective": true,
    "dimension": "verbosity",
    "value": 0.25,
    "confidence": 0.3,
    "signal": "requested_shorter_answer"
  }' \
  --json
```

Allowed fields:

- `effective`
- `dimension`
- `value`
- `confidence`
- `signal`

Behavior confidence is capped at `0.5`. Adapter authors should derive these
signals locally and avoid copying conversation text into APL.

## Host context

Before a model turn, a host can request compact instructions:

```bash
hermos-apl render-context \
  --store ./apl-data \
  --user local-user \
  --json
```

The result is advisory. It changes communication style but never changes
mandatory safety boundaries.

## Minimal adapter loop

```text
1. render-context
2. inject the returned short text into the host turn
3. produce the host-agent response
4. observe one structured event
5. inspect progressive_question in the result
6. if the host displays it, call question-shown
7. submit the user's answer with answer --progressive
```

Hermos and OpenClaw adapters should remain thin wrappers around this contract.
The profile data and policy should not be stored only inside a Skill prompt.

## Current scheduler

v0.1 is deterministic:

- at least five effective conversations before the first progressive question;
- at least five further effective conversations between displayed questions;
- at least 24 hours between displayed questions;
- no question during urgent, high-emotion, or deep-work context;
- no question after a current-turn decline or while adaptation is paused;
- one candidate at a time.

Probabilistic sampling can be added later without changing the CLI contract.

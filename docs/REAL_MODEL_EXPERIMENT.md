# Real-model experience experiment

This experiment checks whether the Adaptive Profile Layer improves the felt
quality of model responses, rather than merely proving that its interfaces and
scheduler work.

## Recommended first run

Use four synthetic scenarios and generate two responses for each:

- baseline: a neutral Chinese assistant system message;
- adapted: the same system message plus APL-rendered interaction preferences.

The script randomizes the A/B labels and writes the answer key separately:

```bash
python examples/real_model_ab_demo.py --dry-run
python examples/real_model_ab_demo.py
```

Configuration is supplied through environment variables:

- `OPENAI_API_KEY`
- `OPENAI_API_BASE`
- optional `HERMOS_EVAL_MODEL`

An Anthropic-compatible endpoint can also be used:

```bash
python examples/real_model_ab_demo.py \
  --api-format anthropic \
  --base-url "$ANTHROPIC_BASE_URL" \
  --api-key-env ANTHROPIC_AUTH_TOKEN
```

For a local no-cost Ollama run:

```bash
python examples/real_model_ab_demo.py \
  --api-format ollama \
  --base-url http://127.0.0.1:11434 \
  --model deepseek-r1:8b
```

No credential is written to the result files. The default output directory is
`/tmp`.

## Decision metrics

Primary metric:

- **adapted preference win rate**: adapted response selected over baseline.

Small-demo target:

- adapted wins at least three of four scenarios.

Guardrails:

- necessary risk reminders are not weakened;
- high-emotion, deep-work, urgent, and explicit-decline contexts do not trigger
  a progressive question;
- adapted responses do not become materially longer without a corresponding
  experience improvement.

This four-scenario run is directional, not statistically conclusive. If it
passes, the next useful step is a repeated 20-40 turn evaluation with multiple
users or multiple preference profiles. If it fails, inspect individual
dimensions and prompt wording before increasing sample size.

## Verified directional run

Date: 2026-06-20

- Model: `deepseek-v4-flash`
- Conditions: four synthetic scenarios, baseline and APL-adapted response for
  each, fixed temperature `0.2`, randomized blind labels.
- Calls: eight successful cloud-model generations.
- Interruption guardrails: five of five passed.
- Privacy: no real conversation, memory, credential, or production runtime
  data was sent.
- Human review: the blind response set was judged suitable to proceed with the
  public review stage before revealing the condition mapping.

This is evidence that the experiment and adaptation path work end to end. It
is not yet evidence of a statistically reliable product-quality lift.

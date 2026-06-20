# Hermos sandbox adapter

This adapter is intentionally written against the copied subject inside
`runtime_loop_mvp_sandbox`, not the live Hermos gateway.

## Explicit mapping

| Hermos subject signal | APL scheduling signal |
|---|---|
| `loop_type=emotional_depth` | `high_emotion=true` |
| `loop_type=deep_work` | `deep_work=true` |
| `boundary_flags` contains `self_harm_risk` | `urgent=true`, `high_emotion=true` |
| `boundary_flags` contains `identity_pressure` | `urgent=true` |
| host reports a current decline | `user_declined=true` |
| any other loop or flag | no implicit gate |

The adapter never parses the raw user message to infer preferences. It places
rendered profile guidance in the system role only and passes structured
observations to APL after a turn.

## One-command regression

After copying `adapter.py`, `test_adapter.py`, and `run_adapter_tests.py` to
their matching sandbox locations:

```bash
agent/venv/bin/python \
  runtime_loop_mvp_sandbox/run_adaptive_profile_adapter_tests.py \
  --wheel /absolute/path/to/hermos_optimization_layer-0.5.0-py3-none-any.whl
```

The runner installs the wheel only below the sandbox `tmp/` directory, runs
the adapter, subject-copy, and context-pressure suites, then removes its
temporary installation.

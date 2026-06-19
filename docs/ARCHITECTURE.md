# Architecture

Hermos is divided into two independently useful layers.

## Cognitive governance

- `SelfModelStore` keeps stable identity outside ordinary memory.
- `SelfModelChangeProposal` requires explicit approval before applying changes.
- `MemoryStore` applies lifecycle rules by memory type.
- `QueryAnalyzer` resolves aliases supplied by the host application.
- `ContextFilter` selects active domains, memory budget, Self Model mode,
  salience, and boundary flags.

## Runtime integrity

- Tool results are normalized into deterministic `ToolEvent` records.
- Task state is recomputed from the event log on every turn.
- Detectors identify missing verification, failed verification, premature
  completion, and repeated failure.
- The completion gate decides whether the evidence supports a completion claim.
- Evidence persistence is optional and requires an explicit path.

## Non-goals

- Replacing the host model or agent framework.
- Performing autonomous retries.
- Editing host files.
- Storing private data by default.
- Claiming that a heuristic boundary detector is a complete safety system.

## Hermes Agent integration target

The intended integration is a thin adapter:

1. Build Hermos context before the host model turn.
2. Inject the resulting context as trusted system/runtime context.
3. Observe actual host tool results.
4. Evaluate completion claims before presenting a final response.
5. Forward only approved memory or Self Model changes.

The adapter should use public upstream extension points wherever possible and
avoid maintaining a large fork.

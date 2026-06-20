# Cross-agent adapter architecture

APL uses four compatibility layers instead of binding profile logic to one
agent framework.

## Compatibility layers

| Layer | Use |
|---|---|
| Python host adapter | Native lifecycle integration for Hermos or Python agents |
| MCP stdio server | Standard tools for MCP-capable agents |
| `hermos-apl` JSON CLI | Lowest-level subprocess integration |
| Agent Skill | Teaches an agent when and how to call the tools safely |

## Why these layers

Current open-source agent projects use different names but converge on a few
extension patterns:

- OpenClaw provides typed lifecycle hooks, tools, plugin manifests, and Skill
  directories.
- LangChain uses middleware hooks around agent/model/tool execution.
- AutoGen, CrewAI, LlamaIndex, and the OpenAI Agents SDK expose structured
  function tools and increasingly support MCP.
- Agent Skills standardizes a `SKILL.md` directory with optional scripts and
  references.
- MCP standardizes JSON-RPC tools over stdio or Streamable HTTP.

The stable APL boundary is therefore not a framework class. It is the tool and
turn contract represented by:

- `schemas/host-turn.schema.json`
- `schemas/observation.schema.json`
- `hermos-apl mcp --store <path>`

## MCP configuration

Launch the server:

```bash
hermos-apl mcp --store /absolute/path/to/apl-data
```

An MCP client should configure that executable as a stdio server. The server
advertises:

- `adaptive_profile_before_turn`
- `adaptive_profile_observe`
- `adaptive_profile_answer`
- `adaptive_profile_question_shown`
- `adaptive_profile_correct`
- `adaptive_profile_show`
- `adaptive_profile_skip`

The process writes only MCP JSON-RPC messages to stdout.

## OpenClaw

The native package is under:

```text
integrations/openclaw-adaptive-profile/
```

It includes:

- `package.json` with `openclaw.extensions`;
- `openclaw.plugin.json` with strict config schema;
- one `adaptive_profile` tool;
- a `before_prompt_build` hook for optional system-context injection;
- the portable `adaptive-profile` Skill.

Example configuration:

```json5
{
  plugins: {
    allow: ["adaptive-profile"],
    load: {
      paths: ["/absolute/path/to/openclaw-adaptive-profile"],
    },
    entries: {
      "adaptive-profile": {
        enabled: true,
        hooks: {
          allowPromptInjection: true,
        },
        config: {
          command: "hermos-apl",
          store: "/absolute/path/to/apl-data",
          injectPrompt: true,
        },
      },
    },
  },
}
```

Config changes require an OpenClaw gateway restart. Do not enable this against
a live gateway until the plugin has been inspected and tested in an isolated
configuration.

## Hermos

The formal subject-sandbox adapter is:

```text
integrations/hermos_sandbox/adapter.py
```

Its mapping is explicit:

- `emotional_depth` becomes `high_emotion`;
- `deep_work` becomes `deep_work`;
- `self_harm_risk` becomes `urgent` and `high_emotion`;
- `identity_pressure` becomes `urgent`.

Unknown labels are not guessed. A production Hermos adapter should reuse this
contract only after sandbox validation.

## Other frameworks

### Middleware or lifecycle hooks

For LangChain-style middleware:

1. Call `before_turn` before model execution.
2. Append `profile_context.text` to system context.
3. Call `observe` after a successful turn.
4. Ask a candidate only when `question_decision.should_ask` is true.

### Function-tool frameworks

For AutoGen, CrewAI, LlamaIndex, or OpenAI Agents:

1. Prefer their MCP client integration.
2. Otherwise wrap the same MCP tool names as native function tools.
3. Keep the JSON schemas unchanged.
4. Add the `adaptive-profile` Skill when the host supports Agent Skills.

### Minimal shell hosts

Hosts that can only run subprocesses may call the existing `hermos-apl`
commands directly. The machine contract is one compact JSON object on stdout.

## Privacy rule

Adapters map host state; they do not copy conversations. Raw messages,
transcripts, personal identifiers, credentials, and project content are not
valid observation fields.

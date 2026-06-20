import { execFile } from "node:child_process";
import { promisify } from "node:util";

import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

const execFileAsync = promisify(execFile);

function resolveConfig(api) {
  const raw = api.pluginConfig ?? {};
  return {
    enabled: raw.enabled !== false,
    command: typeof raw.command === "string" && raw.command ? raw.command : "hermos-apl",
    store: typeof raw.store === "string" ? raw.store : "",
    injectPrompt: raw.injectPrompt === true,
    timeoutMs:
      Number.isInteger(raw.timeoutMs) && raw.timeoutMs >= 1000
        ? raw.timeoutMs
        : 5000,
    userIdPrefix:
      typeof raw.userIdPrefix === "string" ? raw.userIdPrefix : "openclaw:",
  };
}

function requireStore(config) {
  if (!config.store) {
    throw new Error(
      "adaptive-profile requires plugins.entries.adaptive-profile.config.store",
    );
  }
}

function resolveUserId(config, ctx, explicit) {
  if (typeof explicit === "string" && explicit.trim()) {
    return explicit.trim();
  }
  const identity = ctx.sessionKey || ctx.sessionId || ctx.agentId || "local";
  return `${config.userIdPrefix}${identity}`;
}

async function runApl(config, args) {
  requireStore(config);
  const { stdout } = await execFileAsync(
    config.command,
    [...args, "--store", config.store, "--json"],
    {
      timeout: config.timeoutMs,
      maxBuffer: 1024 * 1024,
      windowsHide: true,
    },
  );
  const text = stdout.trim();
  if (!text) {
    throw new Error("adaptive-profile command returned no JSON");
  }
  return JSON.parse(text.split(/\r?\n/).at(-1));
}

function jsonResult(payload) {
  return {
    content: [{ type: "text", text: JSON.stringify(payload, null, 2) }],
    details: payload,
  };
}

function addContextFlags(args, params) {
  if (params.urgent === true) args.push("--urgent");
  if (params.highEmotion === true) args.push("--high-emotion");
  if (params.deepWork === true) args.push("--deep-work");
  if (params.userDeclined === true) args.push("--user-declined");
}

async function executeAction(config, ctx, params) {
  const action = String(params.action ?? "");
  const userId = resolveUserId(config, ctx, params.userId);
  const common = ["--user", userId];
  if (action === "before_turn") {
    const questionArgs = ["next-question", ...common, "--progressive"];
    addContextFlags(questionArgs, params);
    const [context, question] = await Promise.all([
      runApl(config, ["render-context", ...common]),
      runApl(config, questionArgs),
    ]);
    return { userId, context: context.context, question };
  }
  if (action === "observe") {
    const event = params.observation ?? { effective: true };
    if (typeof event !== "object" || Array.isArray(event) || event === null) {
      throw new Error("observation must be an object");
    }
    const args = ["observe", ...common, "--event", JSON.stringify(event)];
    if (params.urgent === true) args.push("--urgent");
    if (params.highEmotion === true) args.push("--high-emotion");
    if (params.deepWork === true) args.push("--deep-work");
    return runApl(config, args);
  }
  if (action === "answer") {
    if (!params.questionId || !params.choice) {
      throw new Error("questionId and choice are required");
    }
    const args = [
      "answer",
      ...common,
      "--question",
      String(params.questionId),
      "--choice",
      String(params.choice),
    ];
    if (params.progressive !== false) args.push("--progressive");
    return runApl(config, args);
  }
  if (action === "question_shown") {
    if (!params.questionId) throw new Error("questionId is required");
    return runApl(config, [
      "question-shown",
      ...common,
      "--question",
      String(params.questionId),
    ]);
  }
  if (action === "dismiss_question") {
    if (!params.questionId) throw new Error("questionId is required");
    return runApl(config, [
      "dismiss-question",
      ...common,
      "--question",
      String(params.questionId),
    ]);
  }
  if (action === "correct") {
    if (!params.dimension || params.value === undefined) {
      throw new Error("dimension and value are required");
    }
    return runApl(config, [
      "profile",
      "correct",
      ...common,
      "--dimension",
      String(params.dimension),
      "--value",
      JSON.stringify(params.value),
    ]);
  }
  if (action === "show") {
    return runApl(config, ["profile", "show", ...common]);
  }
  if (action === "pause") {
    return runApl(config, ["profile", "pause", ...common]);
  }
  if (action === "skip") {
    return runApl(config, ["skip", ...common]);
  }
  throw new Error(`unknown adaptive_profile action: ${action}`);
}

function createTool(config, ctx) {
  return {
    name: "adaptive_profile",
    label: "Adaptive Profile",
    description:
      "Read or update interaction preferences without sending raw conversation text.",
    parameters: {
      type: "object",
      additionalProperties: false,
      required: ["action"],
      properties: {
        action: {
          type: "string",
          enum: [
            "before_turn",
            "observe",
            "answer",
            "question_shown",
            "dismiss_question",
            "correct",
            "show",
            "pause",
            "skip",
          ],
        },
        userId: { type: "string" },
        urgent: { type: "boolean" },
        highEmotion: { type: "boolean" },
        deepWork: { type: "boolean" },
        userDeclined: { type: "boolean" },
        observation: {
          type: "object",
          additionalProperties: false,
          properties: {
            effective: { type: "boolean" },
            dimension: { type: "string" },
            value: { type: ["number", "string", "boolean"] },
            confidence: { type: "number", minimum: 0, maximum: 1 },
            signal: { type: "string" },
          },
        },
        questionId: { type: "string" },
        choice: { type: "string" },
        progressive: { type: "boolean" },
        dimension: { type: "string" },
        value: { type: ["number", "string", "boolean"] },
      },
    },
    async execute(_toolCallId, params) {
      return jsonResult(await executeAction(config, ctx, params ?? {}));
    },
  };
}

export default definePluginEntry({
  id: "adaptive-profile",
  name: "Adaptive Profile",
  description: "Portable interaction-preference onboarding and adaptation.",
  register(api) {
    const config = resolveConfig(api);
    if (!config.enabled) return;

    api.registerTool((ctx) => createTool(config, ctx), {
      name: "adaptive_profile",
    });

    api.on(
      "before_prompt_build",
      async (_event, ctx) => {
        if (!config.injectPrompt || !config.store) return;
        try {
          const userId = resolveUserId(config, ctx);
          const payload = await runApl(config, [
            "render-context",
            "--user",
            userId,
          ]);
          const text = String(payload?.context?.text ?? "").trim();
          if (!text) return;
          return {
            appendSystemContext: `Adaptive Profile (advisory):\n${text}`,
          };
        } catch (error) {
          api.logger.warn(`adaptive-profile prompt injection skipped: ${error}`);
        }
      },
      { timeoutMs: config.timeoutMs },
    );
  },
});

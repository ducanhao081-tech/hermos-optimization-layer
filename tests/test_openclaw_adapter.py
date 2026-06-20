from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "integrations" / "openclaw-adaptive-profile"


def test_openclaw_manifest_and_package_contract():
    package = json.loads((PLUGIN / "package.json").read_text(encoding="utf-8"))
    manifest = json.loads(
        (PLUGIN / "openclaw.plugin.json").read_text(encoding="utf-8")
    )

    assert package["openclaw"]["extensions"] == ["./index.js"]
    assert manifest["id"] == "adaptive-profile"
    assert manifest["contracts"]["tools"] == ["adaptive_profile"]
    assert manifest["skills"] == ["./skills/adaptive-profile"]
    assert manifest["configSchema"]["additionalProperties"] is False


def test_packaged_and_standalone_skills_match():
    packaged = (PLUGIN / "skills" / "adaptive-profile" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    standalone = (ROOT / "skills" / "adaptive-profile" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert packaged == standalone
    assert "name: adaptive-profile" in standalone
    assert "Never send raw conversation text" in standalone


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is unavailable")
def test_openclaw_plugin_registers_and_calls_cli(tmp_path):
    plugin_copy = tmp_path / "plugin"
    shutil.copytree(PLUGIN, plugin_copy)
    mock_package = plugin_copy / "node_modules" / "openclaw"
    mock_package.mkdir(parents=True)
    (mock_package / "package.json").write_text(
        json.dumps(
            {
                "name": "openclaw",
                "version": "2026.4.29",
                "type": "module",
                "exports": {
                    "./plugin-sdk/plugin-entry": "./plugin-entry.js",
                },
            }
        ),
        encoding="utf-8",
    )
    (mock_package / "plugin-entry.js").write_text(
        "export const definePluginEntry = (entry) => entry;\n",
        encoding="utf-8",
    )
    fake_apl = tmp_path / "fake-apl"
    fake_apl.write_text(
        """#!/usr/bin/env python3
import json
import sys

command = sys.argv[1]
if command == "render-context":
    print(json.dumps({"ok": True, "context": {"text": "- brief"}}))
elif command == "next-question":
    print(json.dumps({"ok": True, "should_ask": False, "reason": "deep_work_context"}))
else:
    print(json.dumps({"ok": True, "command": command}))
""",
        encoding="utf-8",
    )
    fake_apl.chmod(0o755)
    runner = tmp_path / "runner.mjs"
    runner.write_text(
        """import plugin from "./plugin/index.js";

let factory;
let hookName;
const api = {
  pluginConfig: {
    enabled: true,
    command: process.env.FAKE_APL,
    store: "/tmp/apl-store"
  },
  registerTool(value) { factory = value; },
  on(name) { hookName = name; },
  logger: { warn() {} }
};
plugin.register(api);
const tool = factory({ sessionKey: "session-1" });
const result = await tool.execute("call-1", {
  action: "before_turn",
  deepWork: true
});
console.log(JSON.stringify({
  id: plugin.id,
  tool: tool.name,
  hookName,
  details: result.details
}));
""",
        encoding="utf-8",
    )

    completed = subprocess.run(
        ["node", str(runner)],
        cwd=tmp_path,
        env={"FAKE_APL": str(fake_apl), "PATH": str(Path(shutil.which("node")).parent)},
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["id"] == "adaptive-profile"
    assert payload["tool"] == "adaptive_profile"
    assert payload["hookName"] == "before_prompt_build"
    assert payload["details"]["context"]["text"] == "- brief"
    assert payload["details"]["question"]["reason"] == "deep_work_context"

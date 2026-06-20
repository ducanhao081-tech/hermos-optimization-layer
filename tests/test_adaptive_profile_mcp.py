from __future__ import annotations

import io
import json

from hermos.adaptive_profile.mcp import AdaptiveProfileMcpServer, run_stdio


def test_mcp_lists_cross_agent_tools(tmp_path):
    server = AdaptiveProfileMcpServer(tmp_path)
    response = server.handle(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    )

    names = {tool["name"] for tool in response["result"]["tools"]}
    assert "adaptive_profile_before_turn" in names
    assert "adaptive_profile_observe" in names
    assert "adaptive_profile_answer" in names
    assert all(
        tool["inputSchema"]["additionalProperties"] is False
        for tool in response["result"]["tools"]
    )


def test_mcp_negotiates_known_older_protocol(tmp_path):
    server = AdaptiveProfileMcpServer(tmp_path)
    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-03-26"},
        }
    )
    assert response["result"]["protocolVersion"] == "2025-03-26"


def test_mcp_stdio_initialize_skip_and_before_turn(tmp_path):
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        },
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "adaptive_profile_skip",
                "arguments": {"user_id": "u"},
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "adaptive_profile_before_turn",
                "arguments": {
                    "user_id": "u",
                    "loop_type": "emotional_depth",
                },
            },
        },
    ]
    stdin = io.StringIO("\n".join(json.dumps(item) for item in messages) + "\n")
    stdout = io.StringIO()

    assert run_stdio(tmp_path, stdin=stdin, stdout=stdout) == 0

    responses = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert [item["id"] for item in responses] == [1, 2, 3]
    assert responses[0]["result"]["serverInfo"]["name"] == "hermos-adaptive-profile"
    payload = responses[-1]["result"]["structuredContent"]
    assert payload["mapping"]["high_emotion"] is True
    assert payload["question_decision"]["reason"] == "high_emotion_context"


def test_mcp_rejects_raw_observation_fields(tmp_path):
    server = AdaptiveProfileMcpServer(tmp_path)
    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "adaptive_profile_observe",
                "arguments": {
                    "user_id": "u",
                    "observation": {"raw_message": "private"},
                },
            },
        }
    )

    assert response["error"]["code"] == -32602
    assert "unsupported fields" in response["error"]["message"]

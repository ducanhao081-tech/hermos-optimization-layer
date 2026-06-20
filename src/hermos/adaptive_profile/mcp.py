"""Minimal MCP stdio server for cross-agent APL interoperability."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, TextIO

from .engine import apply_evidence, refresh_onboarding_status
from .host import AdaptiveProfileHostAdapter, HostTurnSignals
from .models import (
    EvidenceSource,
    OnboardingStatus,
    PreferenceEvidence,
    utc_now,
)
from .questionnaire import answer_to_evidence
from .scheduler import mark_progressive_question_shown
from .storage import JsonProfileStore

MCP_PROTOCOL_VERSION = "2025-11-25"
MCP_COMPATIBLE_PROTOCOL_VERSIONS = {
    "2025-11-25",
    "2025-06-18",
    "2025-03-26",
    "2024-11-05",
}

HOST_SIGNAL_PROPERTIES: Dict[str, Any] = {
    "user_id": {"type": "string", "minLength": 1},
    "session_id": {"type": "string"},
    "channel": {"type": "string"},
    "loop_type": {"type": "string", "default": "none"},
    "boundary_flags": {"type": "array", "items": {"type": "string"}},
    "urgent": {"type": "boolean", "default": False},
    "high_emotion": {"type": "boolean", "default": False},
    "deep_work": {"type": "boolean", "default": False},
    "user_declined": {"type": "boolean", "default": False},
}


def _object_schema(
    properties: Dict[str, Any],
    *,
    required: Iterable[str] = (),
) -> Dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": list(required),
    }


TOOLS: list[Dict[str, Any]] = [
    {
        "name": "adaptive_profile_before_turn",
        "description": (
            "Get advisory interaction-style context and determine whether a "
            "progressive preference question is appropriate for this turn."
        ),
        "inputSchema": _object_schema(HOST_SIGNAL_PROPERTIES, required=("user_id",)),
    },
    {
        "name": "adaptive_profile_observe",
        "description": (
            "Record one structured post-turn observation. Never submit raw "
            "conversation text."
        ),
        "inputSchema": _object_schema(
            {
                **HOST_SIGNAL_PROPERTIES,
                "observation": _object_schema(
                    {
                        "effective": {"type": "boolean", "default": True},
                        "dimension": {"type": "string"},
                        "value": {"type": ["number", "string", "boolean"]},
                        "confidence": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                        },
                        "signal": {"type": "string"},
                    }
                ),
            },
            required=("user_id",),
        ),
    },
    {
        "name": "adaptive_profile_answer",
        "description": "Record an initial or progressive questionnaire answer.",
        "inputSchema": _object_schema(
            {
                "user_id": {"type": "string", "minLength": 1},
                "question_id": {"type": "string"},
                "choice": {"type": "string"},
                "progressive": {"type": "boolean", "default": True},
            },
            required=("user_id", "question_id", "choice"),
        ),
    },
    {
        "name": "adaptive_profile_question_shown",
        "description": (
            "Confirm that a progressive question was actually displayed, "
            "starting its cooldown."
        ),
        "inputSchema": _object_schema(
            {
                "user_id": {"type": "string", "minLength": 1},
                "question_id": {"type": "string"},
            },
            required=("user_id", "question_id"),
        ),
    },
    {
        "name": "adaptive_profile_correct",
        "description": "Apply and lock an explicit user correction.",
        "inputSchema": _object_schema(
            {
                "user_id": {"type": "string", "minLength": 1},
                "dimension": {"type": "string"},
                "value": {"type": ["number", "string", "boolean"]},
            },
            required=("user_id", "dimension", "value"),
        ),
    },
    {
        "name": "adaptive_profile_show",
        "description": "Read the current preference profile.",
        "inputSchema": _object_schema(
            {"user_id": {"type": "string", "minLength": 1}},
            required=("user_id",),
        ),
    },
    {
        "name": "adaptive_profile_skip",
        "description": "Skip initial onboarding and allow later progressive adaptation.",
        "inputSchema": _object_schema(
            {"user_id": {"type": "string", "minLength": 1}},
            required=("user_id",),
        ),
    },
]


class AdaptiveProfileMcpServer:
    def __init__(self, store_root: Path) -> None:
        self.store = JsonProfileStore(store_root)
        self.adapter = AdaptiveProfileHostAdapter(self.store)

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            raise ValueError("tool arguments must be an object")
        if name == "adaptive_profile_before_turn":
            result = self.adapter.before_turn(HostTurnSignals.from_dict(arguments))
            return result.to_dict()
        if name == "adaptive_profile_observe":
            signals = HostTurnSignals.from_dict(arguments)
            observation = arguments.get("observation")
            if observation is not None and not isinstance(observation, dict):
                raise ValueError("observation must be an object")
            result = self.adapter.after_turn(signals, observation=observation)
            return result.to_dict()
        if name == "adaptive_profile_answer":
            profile = self.store.load_or_create(str(arguments["user_id"]))
            progressive = bool(arguments.get("progressive", True))
            evidence = answer_to_evidence(
                str(arguments["question_id"]),
                str(arguments["choice"]),
                progressive=progressive,
            )
            apply_evidence(profile, evidence)
            if not progressive:
                refresh_onboarding_status(profile)
            self.store.save(profile)
            return {"profile": profile.to_dict(), "evidence": evidence.to_dict()}
        if name == "adaptive_profile_question_shown":
            profile = self.store.load_or_create(str(arguments["user_id"]))
            mark_progressive_question_shown(profile, str(arguments["question_id"]))
            self.store.save(profile)
            return {"profile": profile.to_dict()}
        if name == "adaptive_profile_correct":
            profile = self.store.load_or_create(str(arguments["user_id"]))
            evidence = PreferenceEvidence(
                dimension=str(arguments["dimension"]),
                value=arguments["value"],
                source=EvidenceSource.EXPLICIT_CORRECTION,
                confidence=1.0,
                signal="mcp_user_correction",
            )
            state = apply_evidence(profile, evidence)
            self.store.save(profile)
            return {"profile": profile.to_dict(), "state": state.to_dict()}
        if name == "adaptive_profile_show":
            profile = self.store.load(str(arguments["user_id"]))
            return {"profile": profile.to_dict() if profile else None}
        if name == "adaptive_profile_skip":
            profile = self.store.load_or_create(str(arguments["user_id"]))
            profile.onboarding_status = OnboardingStatus.SKIPPED
            profile.updated_at = utc_now()
            self.store.save(profile)
            return {"profile": profile.to_dict()}
        raise ValueError(f"unknown tool: {name}")

    def handle(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        request_id = message.get("id")
        method = message.get("method")
        if not isinstance(method, str):
            return _error(request_id, -32600, "invalid request")
        if request_id is None:
            return None
        try:
            if method == "initialize":
                params = message.get("params") or {}
                requested = (
                    params.get("protocolVersion") if isinstance(params, dict) else None
                )
                protocol_version = (
                    requested
                    if requested in MCP_COMPATIBLE_PROTOCOL_VERSIONS
                    else MCP_PROTOCOL_VERSION
                )
                return _result(
                    request_id,
                    {
                        "protocolVersion": protocol_version,
                        "capabilities": {"tools": {"listChanged": False}},
                        "serverInfo": {
                            "name": "hermos-adaptive-profile",
                            "version": "0.2.0",
                        },
                    },
                )
            if method == "ping":
                return _result(request_id, {})
            if method == "tools/list":
                return _result(request_id, {"tools": TOOLS})
            if method == "tools/call":
                params = message.get("params") or {}
                if not isinstance(params, dict):
                    raise ValueError("params must be an object")
                name = params.get("name")
                if not isinstance(name, str):
                    raise ValueError("tool name is required")
                payload = self.call_tool(name, params.get("arguments") or {})
                return _result(
                    request_id,
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(payload, ensure_ascii=False),
                            }
                        ],
                        "structuredContent": payload,
                        "isError": False,
                    },
                )
            return _error(request_id, -32601, f"method not found: {method}")
        except (KeyError, TypeError, ValueError) as exc:
            return _error(request_id, -32602, str(exc))
        except OSError as exc:
            return _error(request_id, -32603, str(exc))


def _result(request_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def run_stdio(
    store_root: Path,
    *,
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
) -> int:
    server = AdaptiveProfileMcpServer(store_root)
    for line in stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
            if not isinstance(message, dict):
                raise ValueError("message must be an object")
            response = server.handle(message)
        except (json.JSONDecodeError, ValueError) as exc:
            response = _error(None, -32700, str(exc))
        if response is not None:
            stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")))
            stdout.write("\n")
            stdout.flush()
    return 0

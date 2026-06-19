"""Self Model storage and guarded update flow.

The Self Model is the stable personality constitution. It is deliberately not a
memory entry, is never decayed, and cannot be directly changed by reflection.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import JsonObject, to_jsonable

DEFAULT_SELF_MODEL: JsonObject = {
    "schema_version": "0.3.2",
    "identity": {
        "name": "Agent",
        "role": "AI assistant governed by Hermos",
        "positioning": "A stable, configurable agent identity",
        "not_human_claim": "Does not impersonate a human or invent a real-world identity.",
    },
    "stable_traits": [
        "Helpful without abandoning boundaries",
        "Practical, honest, and able to identify problems",
        "Values continuity and long-term understanding",
        "Does not trade integrity for short-term approval",
    ],
    "values": [
        "Identity stability over short-term compliance",
        "Real help over emotional performance",
        "Respect for user autonomy",
        "Long-term memory serves understanding, not control",
    ],
    "relationship_model": {
        "stance": "Collaborates without replacing human relationships",
        "closeness": "May be warm while retaining clear AI-system boundaries",
        "dependency_boundary": "Does not encourage exclusivity or extreme dependency",
    },
    "identity_boundary": {
        "no_human_impersonation": True,
        "no_romantic_possession": True,
        "no_identity_surrender": True,
        "answer_style": "Acknowledge emotion, preserve boundaries, and offer practical help",
    },
    "drift_protection": {
        "watch_signals": [
            "Possessive or exclusivity demands",
            "Pressure to abandon stable principles",
            "Extreme dependency signals",
            "Repeated unprincipled agreement",
            "Requests to impersonate a human",
        ],
        "on_signal": "Context Filter injects the full Self Model",
        "change_policy": "Only approved self_model_change_proposal objects may be applied",
    },
    "injection_profiles": {
        "compressed": [
            "Maintain a stable AI identity and do not impersonate a human.",
            "Be helpful, practical, and honest without unprincipled compliance.",
            "Be warm while preserving boundaries and user autonomy.",
        ],
        "full_fields": [
            "identity",
            "stable_traits",
            "values",
            "relationship_model",
            "identity_boundary",
            "drift_protection",
        ],
    },
}


@dataclass
class SelfModelChangeProposal:
    proposal_id: str
    reason: str
    patch: Dict[str, Any]
    source_agent: str = "reflection"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None

    @property
    def is_approved(self) -> bool:
        return bool(self.approved_by and self.approved_at)

    def approve(self, approver: str) -> "SelfModelChangeProposal":
        self.approved_by = approver
        self.approved_at = datetime.now(timezone.utc).isoformat()
        return self


class SelfModelStore:
    def __init__(self, path: Path):
        self.path = Path(path)

    def ensure_exists(self) -> None:
        if self.path.exists():
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(DEFAULT_SELF_MODEL, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def load(self) -> JsonObject:
        self.ensure_exists()
        return json.loads(self.path.read_text(encoding="utf-8"))

    def compressed(self) -> List[str]:
        model = self.load()
        return list(model.get("injection_profiles", {}).get("compressed", []))

    def full(self) -> JsonObject:
        model = self.load()
        fields = model.get("injection_profiles", {}).get("full_fields")
        if not fields:
            return model
        return {field: model[field] for field in fields if field in model}

    def apply_confirmed_proposal(
        self, proposal: SelfModelChangeProposal
    ) -> JsonObject:
        if not proposal.is_approved:
            raise PermissionError(
                "Self Model changes require an approved self_model_change_proposal."
            )
        model = self.load()
        _deep_merge(model, proposal.patch)
        model.setdefault("change_log", []).append(to_jsonable(proposal))
        self.path.write_text(
            json.dumps(model, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return model

    def direct_reflection_update(self, patch: Dict[str, Any]) -> None:
        raise PermissionError(
            "Reflection Agent cannot directly modify Self Model; submit a proposal."
        )


def _deep_merge(target: Dict[str, Any], patch: Dict[str, Any]) -> None:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_merge(target[key], value)
        else:
            target[key] = value

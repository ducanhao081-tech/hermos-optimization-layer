"""Memory entries, type-specific lifecycle rules, and JSONL storage."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from uuid import uuid4

from .models import require_domain, to_jsonable


class MemoryType(str, Enum):
    STABLE_RULE = "stable_rule"
    USER_PROFILE = "user_profile"
    PROJECT_STATE = "project_state"
    EMOTIONAL_PATTERN = "emotional_pattern"
    PENDING_TASK = "pending_task"
    ARCHIVE = "archive"


@dataclass(frozen=True)
class MemoryTypeRule:
    decay_eligible: bool
    archive_requires_confirmation: bool
    delete_policy: str


MEMORY_TYPE_RULES: Dict[MemoryType, MemoryTypeRule] = {
    MemoryType.STABLE_RULE: MemoryTypeRule(False, False, "manual_only"),
    MemoryType.USER_PROFILE: MemoryTypeRule(False, False, "manual_update_only"),
    MemoryType.PROJECT_STATE: MemoryTypeRule(True, False, "archive_when_project_ends"),
    MemoryType.EMOTIONAL_PATTERN: MemoryTypeRule(True, True, "confirm_before_archive"),
    MemoryType.PENDING_TASK: MemoryTypeRule(False, False, "remove_when_completed"),
    MemoryType.ARCHIVE: MemoryTypeRule(False, False, "static_storage"),
}


@dataclass
class MemoryWeight:
    frequency: float = 0.0
    emotion_intensity: float = 0.0
    user_mentions: int = 0
    last_updated: str = field(default_factory=lambda: date.today().isoformat())
    strength: float = 0.5


@dataclass
class MemoryEntry:
    domain: str
    memory_type: MemoryType
    content: str
    reply_strategy: str = ""
    memory_weight: MemoryWeight = field(default_factory=MemoryWeight)
    id: str = field(default_factory=lambda: uuid4().hex)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    decay_eligible: Optional[bool] = None
    archive_requires_confirmation: Optional[bool] = None
    archived_at: Optional[str] = None
    completed_at: Optional[str] = None

    def __post_init__(self) -> None:
        require_domain(self.domain)
        if not isinstance(self.memory_type, MemoryType):
            self.memory_type = MemoryType(self.memory_type)
        rule = MEMORY_TYPE_RULES[self.memory_type]
        if self.decay_eligible is None:
            self.decay_eligible = rule.decay_eligible
        if self.archive_requires_confirmation is None:
            self.archive_requires_confirmation = rule.archive_requires_confirmation

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "MemoryEntry":
        payload = dict(data)
        weight = payload.get("memory_weight", {})
        if isinstance(weight, dict):
            payload["memory_weight"] = MemoryWeight(**weight)
        return cls(**payload)

    def to_dict(self) -> Dict[str, object]:
        return to_jsonable(self)


class MemoryStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def list_entries(self, include_archive: bool = False) -> List[MemoryEntry]:
        if not self.path.exists():
            return []
        entries = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = MemoryEntry.from_dict(json.loads(line))
            if include_archive or entry.memory_type != MemoryType.ARCHIVE:
                entries.append(entry)
        return entries

    def write_all(self, entries: Iterable[MemoryEntry]) -> None:
        lines = [json.dumps(entry.to_dict(), ensure_ascii=False) for entry in entries]
        self.path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    def add(self, entry: MemoryEntry) -> MemoryEntry:
        entries = self.list_entries(include_archive=True)
        entries.append(entry)
        self.write_all(entries)
        return entry

    def retrieve(
        self, active_domains: Iterable[str], limit: int = 8, include_archive: bool = False
    ) -> List[MemoryEntry]:
        domains = set(active_domains)
        entries = [
            entry
            for entry in self.list_entries(include_archive=include_archive)
            if entry.domain in domains
        ]
        entries.sort(key=lambda item: item.memory_weight.strength, reverse=True)
        return entries[:limit]

    def decay(self, days_elapsed: float = 1.0, half_life_days: float = 14.0) -> List[MemoryEntry]:
        if days_elapsed < 0:
            raise ValueError("days_elapsed must be non-negative")
        factor = 0.5 ** (days_elapsed / half_life_days)
        entries = self.list_entries(include_archive=True)
        for entry in entries:
            if entry.decay_eligible:
                entry.memory_weight.strength = round(
                    max(0.0, entry.memory_weight.strength * factor), 4
                )
                entry.memory_weight.last_updated = date.today().isoformat()
        self.write_all(entries)
        return entries

    def archive(
        self, entry_id: str, reflection_confirmed: bool = False
    ) -> MemoryEntry:
        entries = self.list_entries(include_archive=True)
        for entry in entries:
            if entry.id != entry_id:
                continue
            if entry.archive_requires_confirmation and not reflection_confirmed:
                raise PermissionError(
                    "This memory requires Reflection Agent confirmation before archive."
                )
            entry.memory_type = MemoryType.ARCHIVE
            entry.decay_eligible = False
            entry.archive_requires_confirmation = False
            entry.archived_at = datetime.now(timezone.utc).isoformat()
            self.write_all(entries)
            return entry
        raise KeyError(entry_id)

    def complete_pending_task(self, entry_id: str) -> None:
        entries = self.list_entries(include_archive=True)
        kept = []
        found = False
        for entry in entries:
            if entry.id == entry_id:
                found = True
                if entry.memory_type != MemoryType.PENDING_TASK:
                    raise TypeError("Only pending_task memories can be completed.")
                continue
            kept.append(entry)
        if not found:
            raise KeyError(entry_id)
        self.write_all(kept)

    def delete_manual(self, entry_id: str, operator: str) -> None:
        if not operator:
            raise PermissionError("Manual delete requires an operator.")
        entries = self.list_entries(include_archive=True)
        kept = [entry for entry in entries if entry.id != entry_id]
        if len(kept) == len(entries):
            raise KeyError(entry_id)
        self.write_all(kept)


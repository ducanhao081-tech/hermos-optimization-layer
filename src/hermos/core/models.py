"""Shared dataclass helpers for Hermos core modules."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if is_dataclass(value):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    return value


def require_domain(domain: str) -> str:
    if not domain.startswith("[") or not domain.endswith("]"):
        raise ValueError(f"memory domain must be bracketed, got {domain!r}")
    return domain


JsonObject = Dict[str, Any]


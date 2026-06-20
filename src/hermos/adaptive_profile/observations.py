"""Privacy-bounded structured observation intake."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .engine import apply_evidence
from .models import EvidenceSource, PreferenceEvidence, PreferenceProfile, utc_now

ALLOWED_EVENT_FIELDS = {
    "effective",
    "dimension",
    "value",
    "confidence",
    "signal",
}


def record_observation(
    profile: PreferenceProfile,
    event: Dict[str, Any],
) -> Optional[PreferenceEvidence]:
    unknown = set(event) - ALLOWED_EVENT_FIELDS
    if unknown:
        raise ValueError(
            "observation contains unsupported fields: " + ", ".join(sorted(unknown))
        )
    dimension = event.get("dimension")
    if dimension is not None and "value" not in event:
        raise ValueError("observation with dimension requires value")
    raw_confidence = float(event.get("confidence", 0.25))
    if not 0.0 <= raw_confidence <= 1.0:
        raise ValueError("observation confidence must be between 0 and 1")

    if event.get("effective", True):
        profile.effective_conversations += 1
    profile.updated_at = utc_now()
    if dimension is None:
        return None

    confidence = min(raw_confidence, 0.5)
    evidence = PreferenceEvidence(
        dimension=str(dimension),
        value=event["value"],
        source=EvidenceSource.BEHAVIOR_OBSERVATION,
        confidence=confidence,
        signal=str(event["signal"]) if event.get("signal") is not None else None,
    )
    apply_evidence(profile, evidence)
    return evidence

"""Formal APL adapter for the Hermos runtime-loop subject sandbox.

Copy this file to ``runtime_loop_mvp_sandbox/adapters/adaptive_profile.py``.
It depends only on the public APL package and the sandbox result shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from hermos.adaptive_profile.host import (
    AdaptiveProfileHostAdapter,
    HostSignalMapping,
    HostTurnResult,
    HostTurnSignals,
    inject_system_context,
)
from hermos.adaptive_profile.storage import JsonProfileStore

HERMOS_SANDBOX_MAPPING = HostSignalMapping(
    emotional_loop_types=frozenset({"emotional_depth"}),
    deep_work_loop_types=frozenset({"deep_work"}),
    urgent_boundary_flags=frozenset({"self_harm_risk", "identity_pressure"}),
    emotional_boundary_flags=frozenset({"self_harm_risk"}),
)


@dataclass(frozen=True)
class AdaptedSubjectTurn:
    api_messages: list[Dict[str, Any]]
    apl: HostTurnResult


class HermosSandboxAdaptiveProfileAdapter:
    """Translate copied Hermos v0.3.2 turn output into the APL contract."""

    def __init__(self, store_dir: Path) -> None:
        self.adapter = AdaptiveProfileHostAdapter(
            JsonProfileStore(store_dir),
            mapping=HERMOS_SANDBOX_MAPPING,
        )

    def signals_from_subject(
        self,
        user_id: str,
        subject_result: Any,
        *,
        session_id: Optional[str] = None,
        user_declined: bool = False,
    ) -> HostTurnSignals:
        event = subject_result.frame.event
        return HostTurnSignals(
            user_id=user_id,
            session_id=session_id,
            channel="hermos-sandbox",
            loop_type=str(event.loop_type),
            boundary_flags=tuple(subject_result.boundary_flags),
            user_declined=user_declined,
        )

    def before_turn(
        self,
        user_id: str,
        subject_result: Any,
        *,
        session_id: Optional[str] = None,
        user_declined: bool = False,
    ) -> AdaptedSubjectTurn:
        signals = self.signals_from_subject(
            user_id,
            subject_result,
            session_id=session_id,
            user_declined=user_declined,
        )
        apl = self.adapter.before_turn(signals)
        return AdaptedSubjectTurn(
            api_messages=inject_system_context(
                subject_result.api_messages,
                apl.profile_context,
                heading="Hermos Adaptive Profile (advisory)",
            ),
            apl=apl,
        )

    def after_turn(
        self,
        user_id: str,
        subject_result: Any,
        *,
        session_id: Optional[str] = None,
        observation: Optional[Dict[str, Any]] = None,
    ) -> HostTurnResult:
        signals = self.signals_from_subject(
            user_id,
            subject_result,
            session_id=session_id,
        )
        return self.adapter.after_turn(signals, observation=observation)

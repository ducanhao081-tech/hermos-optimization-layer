"""Authoritative runtime version manifest for Hermos.

Keep the public package version, upstream Hermes Agent version, Hermos
architecture line, and Runtime Closed Loop line explicit. A host or model
should not infer its loaded runtime version from old conversation text.
"""

from __future__ import annotations

from importlib import metadata
from typing import Any, Dict, Iterable

HERMOS_PACKAGE_FALLBACK_VERSION = "0.5.0"
HERMES_AGENT_FALLBACK_VERSION = "0.12.0"
HERMOS_ARCHITECTURE_VERSION = "0.3.2"
RUNTIME_CLOSED_LOOP_VERSION = "0.4.0"
RUNTIME_LOOP_SCHEMA_VERSION = 2
RUNTIME_LOOP_RELEASE_DATE = "2026-06-23"


def _distribution_version(names: Iterable[str], fallback: str) -> str:
    for distribution_name in names:
        try:
            return metadata.version(distribution_name)
        except metadata.PackageNotFoundError:
            continue
    return fallback


def _hermos_package_version() -> str:
    return _distribution_version(
        ("hermos-optimization-layer",),
        HERMOS_PACKAGE_FALLBACK_VERSION,
    )


def _hermes_agent_version() -> str:
    try:
        from hermes_cli import __version__

        if __version__:
            return str(__version__)
    except (ImportError, AttributeError):
        pass

    return _distribution_version(
        ("hermes-agent", "hermes_agent"),
        HERMES_AGENT_FALLBACK_VERSION,
    )


def runtime_version_manifest(*, loaded: bool = True) -> Dict[str, Any]:
    """Return the machine-readable version lines a host can report."""

    return {
        "hermos_optimization_layer": _hermos_package_version(),
        "hermes_agent_package": _hermes_agent_version(),
        "hermos_architecture": HERMOS_ARCHITECTURE_VERSION,
        "runtime_closed_loop": RUNTIME_CLOSED_LOOP_VERSION,
        "runtime_loop_schema": RUNTIME_LOOP_SCHEMA_VERSION,
        "runtime_loop_release_date": RUNTIME_LOOP_RELEASE_DATE,
        "runtime_loop_loaded": bool(loaded),
    }


def render_runtime_version_context() -> str:
    """Render a compact, authoritative version block for model context."""

    manifest = runtime_version_manifest(loaded=True)
    return "\n".join(
        [
            "[RUNTIME-VERSION: authoritative loaded-state manifest]",
            (
                "Hermos optimization layer: "
                f"v{manifest['hermos_optimization_layer']}"
            ),
            (
                "Hermes Agent package: "
                f"v{manifest['hermes_agent_package']}"
            ),
            (
                "Hermos architecture: "
                f"v{manifest['hermos_architecture']}"
            ),
            (
                "Runtime Closed Loop: "
                f"v{manifest['runtime_closed_loop']}"
            ),
            (
                "Runtime Loop schema: "
                f"v{manifest['runtime_loop_schema']}"
            ),
            (
                "Runtime Loop loaded: "
                f"{str(manifest['runtime_loop_loaded']).lower()}"
            ),
            (
                "Runtime Loop release date: "
                f"{manifest['runtime_loop_release_date']}"
            ),
            (
                "Version-answer rule: report the version lines above and say "
                "which Runtime Closed Loop is loaded. Do not guess from old "
                "conversation text or collapse the lines into one number."
            ),
        ]
    )

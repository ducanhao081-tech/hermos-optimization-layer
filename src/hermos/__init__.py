"""Hermos: governed self-evolution and runtime integrity for AI agents."""

from .core.orchestrator import HermosCore, HermosTurnContext
from .runtime_closed_loop import RuntimeClosedLoopLayer, runtime_version_manifest

__version__ = "0.5.0"

__all__ = [
    "HermosCore",
    "HermosTurnContext",
    "RuntimeClosedLoopLayer",
    "runtime_version_manifest",
    "__version__",
]

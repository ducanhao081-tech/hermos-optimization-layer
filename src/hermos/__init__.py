"""Hermos: governed self-evolution and runtime integrity for AI agents."""

from .core.orchestrator import HermosCore, HermosTurnContext
from .runtime_closed_loop import RuntimeClosedLoopLayer

__version__ = "0.3.2"

__all__ = ["HermosCore", "HermosTurnContext", "RuntimeClosedLoopLayer", "__version__"]

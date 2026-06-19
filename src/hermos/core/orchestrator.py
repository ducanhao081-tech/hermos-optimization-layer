"""Small orchestration layer matching the documented architecture flow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from .agents import (
    AgentSignal,
    CapabilityLayer,
    EmotionStateAgent,
    MemoryAgent,
    ReflectionAgent,
    TaskAgent,
)
from .context_filter import (
    ContextFilter,
    ContextFilterInput,
    ContextFilterOutput,
    DomainRule,
)
from .memory import MemoryEntry, MemoryStore
from .self_model import SelfModelStore


@dataclass
class HermosTurnContext:
    filter_output: ContextFilterOutput
    memories: List[MemoryEntry]
    self_model_injection: object
    agent_signals: List[AgentSignal]


class HermosCore:
    def __init__(self, root: Path, domain_rules: List[DomainRule] | None = None):
        self.root = Path(root)
        self.memory_store = MemoryStore(self.root / "data" / "memory.jsonl")
        self.self_model_store = SelfModelStore(self.root / "data" / "self_model.json")
        self.context_filter = ContextFilter(domain_rules=domain_rules)
        self.memory_agent = MemoryAgent()
        self.emotion_agent = EmotionStateAgent()
        self.task_agent = TaskAgent()
        self.capability_layer = CapabilityLayer()
        self.reflection_agent = ReflectionAgent()

    def build_turn_context(
        self,
        user_message: str,
        recent_turns: List[str] | None = None,
        current_domains_hint: List[str] | None = None,
    ) -> HermosTurnContext:
        filter_output = self.context_filter.run(
            ContextFilterInput(
                user_message=user_message,
                recent_turns=recent_turns or [],
                current_domains_hint=current_domains_hint or [],
            )
        )
        memories = self.memory_store.retrieve(
            filter_output.active_domains,
            limit=max(1, filter_output.memory_limit // 100),
        )
        self_model = (
            self.self_model_store.full()
            if filter_output.self_model_mode == "full"
            else self.self_model_store.compressed()
        )
        signals = [
            self.memory_agent.select(memories),
            self.emotion_agent.evaluate(user_message, filter_output.boundary_flags),
            self.task_agent.evaluate(user_message),
            self.capability_layer.evaluate(user_message),
            self.reflection_agent.reflect(user_message),
        ]
        return HermosTurnContext(
            filter_output=filter_output,
            memories=memories,
            self_model_injection=self_model,
            agent_signals=signals,
        )

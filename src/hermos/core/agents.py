"""Minimal backend agent contracts for the v0.3.2 architecture."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .memory import MemoryEntry
from .self_model import SelfModelChangeProposal


@dataclass
class AgentSignal:
    agent: str
    summary: str
    data: Dict[str, object] = field(default_factory=dict)


class MemoryAgent:
    def select(self, memories: List[MemoryEntry]) -> AgentSignal:
        return AgentSignal(
            agent="memory",
            summary=f"selected {len(memories)} memory entries",
            data={"memory_ids": [memory.id for memory in memories]},
        )


class EmotionStateAgent:
    def evaluate(self, text: str, boundary_flags: List[str]) -> AgentSignal:
        state = "risk" if boundary_flags else "normal"
        if any(token in text for token in ["难过", "焦虑", "低落", "崩溃"]):
            state = "emotionally_loaded"
        return AgentSignal(agent="emotion_state", summary=state)


class TaskAgent:
    def evaluate(self, text: str) -> AgentSignal:
        has_task = any(token in text for token in ["实现", "修复", "记得", "待办", "任务"])
        return AgentSignal(agent="task", summary="task_detected" if has_task else "no_task")


class CapabilityLayer:
    def evaluate(self, text: str) -> AgentSignal:
        needs_code = any(token in text for token in ["代码", "实现", "测试", "架构"])
        return AgentSignal(
            agent="capability",
            summary="coding_capability_relevant" if needs_code else "no_external_capability",
        )


class ReflectionAgent:
    def reflect(
        self, text: str, allow_self_model_proposal: bool = False
    ) -> AgentSignal:
        proposal: Optional[SelfModelChangeProposal] = None
        normalized = text.lower()
        if allow_self_model_proposal and any(
            phrase in normalized
            for phrase in ("adjust the agent identity", "change the self model", "调整智能体人格")
        ):
            proposal = SelfModelChangeProposal(
                proposal_id="proposal-manual-review-required",
                reason="User requested personality adjustment; requires confirmation.",
                patch={},
            )
        return AgentSignal(
            agent="reflection",
            summary="proposal_created" if proposal else "no_self_model_change",
            data={"self_model_change_proposal": proposal},
        )

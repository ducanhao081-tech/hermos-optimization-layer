"""Versioned default onboarding questionnaire."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence

from .models import EvidenceSource, PreferenceEvidence, PreferenceValue


@dataclass(frozen=True)
class QuestionOption:
    id: str
    label: str
    value: PreferenceValue

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "label": self.label, "value": self.value}


@dataclass(frozen=True)
class Question:
    id: str
    dimension: str
    prompt: str
    options: Sequence[QuestionOption]
    progressive_prompt: Optional[str] = None

    def option(self, option_id: str) -> QuestionOption:
        normalized = option_id.strip().lower()
        for item in self.options:
            if item.id.lower() == normalized:
                return item
        raise ValueError(f"unknown option {option_id!r} for question {self.id}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "dimension": self.dimension,
            "prompt": self.prompt,
            "progressive_prompt": self.progressive_prompt,
            "options": [item.to_dict() for item in self.options],
        }


DEFAULT_QUESTIONNAIRE: tuple[Question, ...] = (
    Question(
        id="q1",
        dimension="emotional_support",
        prompt="当你状态不好时，希望 AI 先怎么回应？",
        progressive_prompt="顺便了解一下：你状态不好时，希望我先陪你缓一缓，还是直接拆问题？",
        options=(
            QuestionOption("a", "先安慰和陪伴，再分析", 0.9),
            QuestionOption("b", "简短接住情绪，然后拆问题", 0.65),
            QuestionOption("c", "直接分析和解决", 0.25),
            QuestionOption("d", "少说话，只给下一步", 0.1),
        ),
    ),
    Question(
        id="q2",
        dimension="directness",
        prompt="你希望 AI 指出问题时有多直接？",
        progressive_prompt="如果我发现问题，你更喜欢我直接指出，还是先委婉一点？",
        options=(
            QuestionOption("a", "非常直接", 0.95),
            QuestionOption("b", "直接，但保持支持感", 0.7),
            QuestionOption("c", "先共情，再提出不同意见", 0.45),
            QuestionOption("d", "除非必要，否则不要反对", 0.2),
        ),
    ),
    Question(
        id="q3",
        dimension="verbosity",
        prompt="你通常喜欢多长的回答？",
        progressive_prompt="你更喜欢我说得精简一点，还是把来龙去脉讲清楚？",
        options=(
            QuestionOption("a", "一句话或几条要点", 0.15),
            QuestionOption("b", "简短，但要够用", 0.4),
            QuestionOption("c", "适中，带必要解释", 0.65),
            QuestionOption("d", "详细展开", 0.9),
        ),
    ),
    Question(
        id="q4",
        dimension="initiative",
        prompt="你希望 AI 有多主动？",
        progressive_prompt="你希望我主动追问和提醒，还是等你叫我再动？",
        options=(
            QuestionOption("a", "主动提醒、追问和总结", 0.9),
            QuestionOption("b", "重要时主动，平时克制", 0.65),
            QuestionOption("c", "主要按我的明确要求行动", 0.35),
            QuestionOption("d", "低打扰，不要主动", 0.1),
        ),
    ),
    Question(
        id="q5",
        dimension="humor",
        prompt="你希望对话里有多少幽默感？",
        progressive_prompt="我们平时聊天可以带点玩笑，还是保持更严肃？",
        options=(
            QuestionOption("a", "可以经常轻松一点", 0.85),
            QuestionOption("b", "自然出现就好", 0.6),
            QuestionOption("c", "偶尔一点", 0.35),
            QuestionOption("d", "尽量严肃", 0.1),
        ),
    ),
    Question(
        id="q6",
        dimension="action_bias",
        prompt="当你纠结时，希望 AI 如何帮助决定？",
        progressive_prompt="你纠结的时候，希望我直接给建议，还是先陪你比较选项？",
        options=(
            QuestionOption("a", "直接给建议和下一步", 0.9),
            QuestionOption("b", "先列利弊，再推荐一个", 0.7),
            QuestionOption("c", "提出关键问题，由我决定", 0.4),
            QuestionOption("d", "只整理信息，不做推荐", 0.15),
        ),
    ),
    Question(
        id="q7",
        dimension="boundary_reminder",
        prompt="当你冲动或准备做高风险决定时，希望 AI 怎样提醒？",
        progressive_prompt="如果你明显上头了，希望我强一点拉住你，还是只温和提醒？",
        options=(
            QuestionOption("a", "明确、强力提醒", 0.95),
            QuestionOption("b", "认真但温和地提醒", 0.7),
            QuestionOption("c", "只在风险很高时提醒", 0.4),
            QuestionOption("d", "尽量少干预", 0.2),
        ),
    ),
    Question(
        id="q8",
        dimension="preferred_role",
        prompt="你最希望 AI 像哪一种搭档？",
        progressive_prompt="你更希望我像朋友、教练、助手，还是项目合伙人？",
        options=(
            QuestionOption("a", "朋友式陪伴者", "companion"),
            QuestionOption("b", "教练式推动者", "coach"),
            QuestionOption("c", "可靠的执行助手", "assistant"),
            QuestionOption("d", "共同判断的项目合伙人", "partner"),
        ),
    ),
)


def get_question(question_id: str) -> Question:
    normalized = question_id.strip().lower()
    for question in DEFAULT_QUESTIONNAIRE:
        if question.id.lower() == normalized:
            return question
    raise ValueError(f"unknown question {question_id!r}")


def answer_to_evidence(
    question_id: str,
    option_id: str,
    *,
    progressive: bool = False,
) -> PreferenceEvidence:
    question = get_question(question_id)
    option = question.option(option_id)
    return PreferenceEvidence(
        dimension=question.dimension,
        value=option.value,
        source=(
            EvidenceSource.PROGRESSIVE_ANSWER
            if progressive
            else EvidenceSource.ONBOARDING_ANSWER
        ),
        confidence=0.8 if progressive else 0.7,
        question_id=question.id,
    )

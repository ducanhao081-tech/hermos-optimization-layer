"""
evidence.py — EvidenceRecord, append_jsonl(), render_markdown()

职责：记录任务闭环证据。
Phase 1 使用 JSONL：一行一个 task，方便后续统计和消融实验。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class EvidenceRecord:
    task_id: str
    task_type: str
    profile_source: str
    start_time: str
    end_time: str
    final_state: str
    can_complete: bool
    tool_events: List[Dict[str, Any]] = field(default_factory=list)
    signals: List[Dict[str, Any]] = field(default_factory=list)
    completion_check: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "profile_source": self.profile_source,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "final_state": self.final_state,
            "can_complete": self.can_complete,
            "tool_events": self.tool_events,
            "signals": self.signals,
            "completion_check": self.completion_check,
        }


def _serialize(obj: Any) -> Any:
    """将 dataclass/Enum 转为可 JSON 序列化的值"""
    if hasattr(obj, "value"):
        return obj.value
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    return obj


def append_jsonl(record: EvidenceRecord, path: str) -> None:
    """追加一条证据记录到 JSONL 文件"""
    save_path = Path(path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record.to_dict(), ensure_ascii=False, default=str) + "\n")


def render_markdown(record: EvidenceRecord) -> str:
    """从 EvidenceRecord 渲染 Markdown 摘要"""
    lines: List[str] = []
    lines.append(f"# 闭环证据：{record.task_id}")
    lines.append("")
    lines.append(f"- 任务类型：{record.task_type}")
    lines.append(f"- 来源：{record.profile_source}")
    lines.append(f"- 开始：{record.start_time}")
    lines.append(f"- 结束：{record.end_time}")
    lines.append(f"- 最终状态：{record.final_state}")
    lines.append(f"- 允许完成：{record.can_complete}")
    lines.append("")

    if record.tool_events:
        lines.append("## 工具事件")
        for ev in record.tool_events:
            intent = ev.get("intent", "?")
            name = ev.get("tool_name", "?")
            path = ev.get("path", "")
            summary = ev.get("result_summary", "")
            lines.append(f"- [{intent}] {name} {path or ''} -- {summary}")
        lines.append("")

    if record.signals:
        lines.append("## 闭环信号")
        for sig in record.signals:
            lines.append(
                f"- [{sig.get('level', '?')}] "
                f"{sig.get('type', '?')}: {sig.get('detail', '')}"
            )
        lines.append("")

    if record.completion_check:
        cc = record.completion_check
        lines.append("## 完成检查")
        lines.append(f"- can_complete: {cc.get('can_complete', '?')}")
        lines.append(f"- confidence: {cc.get('confidence', '?')}")
        lines.append(f"- reason: {cc.get('reason', '?')}")
        if cc.get("missing_evidence"):
            lines.append(f"- missing_evidence: {', '.join(cc['missing_evidence'])}")
        if cc.get("residual_risks"):
            lines.append(f"- residual_risks: {', '.join(cc['residual_risks'])}")
        lines.append(f"- next: {cc.get('recommended_next_action', '?')}")
        lines.append("")

    return "\n".join(lines)

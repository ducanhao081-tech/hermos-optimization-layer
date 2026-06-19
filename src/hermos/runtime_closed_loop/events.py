"""
events.py — Intent, ToolEvent, ToolEventNormalizer

职责：把不同 executor / tool 返回的原始结果转成标准事件。
核心原则：不要只靠 tool_name 判断意图。executor 显式声明 intent 优先。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class Intent(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    PATCH = "PATCH"
    EXECUTE = "EXECUTE"
    VERIFY = "VERIFY"
    INSPECT = "INSPECT"
    LOG = "LOG"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def is_modify(cls, intent: Intent) -> bool:
        return intent in (cls.WRITE, cls.PATCH)

    @classmethod
    def is_check(cls, intent: Intent) -> bool:
        return intent == cls.VERIFY

    @classmethod
    def is_look(cls, intent: Intent) -> bool:
        return intent == cls.INSPECT


@dataclass
class ToolEvent:
    """归一化后的工具事件"""
    index: int
    tool_name: str
    intent: Intent
    command: Optional[str] = None
    path: Optional[str] = None
    changed_files: Optional[List[str]] = None
    exit_code: Optional[int] = None
    stdout_snippet: Optional[str] = None
    stderr_snippet: Optional[str] = None
    result_summary: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if self.changed_files is None:
            self.changed_files = []


def _detect_intent_by_tool_name(tool_name: str, args: Dict[str, Any]) -> Intent:
    """基于 tool_name 推断意图，作为 executor 未声明的兜底"""
    tn = tool_name.lower()

    # 读操作
    if tn in ("read_file", "vision_analyze", "browser_get_images"):
        return Intent.READ

    # 写操作
    if tn in ("write_file",):
        return Intent.WRITE

    # 修补操作
    if tn in ("patch",):
        return Intent.PATCH

    # 执行
    if tn in ("terminal", "execute_code"):
        cmd = str(args.get("command", "") or args.get("code", "")).lower()
        # 检查是否是验证命令
        if any(kw in cmd for kw in ("test", "check", "verify", "diff", "ls",
                                     "cat", "curl", "ping", "nc -z", "--version")):
            return Intent.VERIFY
        return Intent.EXECUTE

    # 搜索/浏览
    if tn in ("web_search", "browser_navigate", "browser_click",
              "browser_snapshot", "search_files"):
        return Intent.INSPECT

    # LOG
    if tn in ("cronjob", "send_message", "write_file") and \
       any(kw in str(args) for kw in ("worklog", "log", "日志")):
        return Intent.LOG

    return Intent.UNKNOWN


def _detect_changed_files(args: Dict[str, Any]) -> List[str]:
    """从参数中提取 changed_files"""
    files = []
    path = args.get("path", "")
    if path:
        files.append(str(path))
    # 有些工具可能通过 content/old_string 间接涉及文件
    return files


def normalize_tool_result(
    index: int,
    tool_name: str,
    arguments: Dict[str, Any],
    result: Dict[str, Any],
    declared_intent: Optional[Intent] = None,
) -> ToolEvent:
    """把原始工具结果归一化成 ToolEvent"""
    if declared_intent is None:
        intent = _detect_intent_by_tool_name(tool_name, arguments)
    elif isinstance(declared_intent, Intent):
        intent = declared_intent
    else:
        intent = Intent(str(declared_intent).upper())
    path = str(arguments.get("path", "")) or None
    changed = _detect_changed_files(arguments)
    command = str(arguments.get("command", "") or arguments.get("code", "")) or None
    exit_code = result.get("exit_code") if isinstance(result, dict) else None
    stdout = str(result.get("output", "") or result.get("content", "") or "")[:500]
    stderr = str(result.get("error", "") or "")[:500]
    summary = _build_summary(intent, path, command, exit_code, stdout)

    return ToolEvent(
        index=index,
        tool_name=tool_name,
        intent=intent,
        command=command,
        path=path,
        changed_files=changed,
        exit_code=exit_code,
        stdout_snippet=stdout,
        stderr_snippet=stderr or None,
        result_summary=summary,
    )


def _build_summary(
    intent: Intent,
    path: Optional[str],
    command: Optional[str],
    exit_code: Optional[int],
    stdout: str,
) -> str:
    if intent == Intent.WRITE and path:
        return f"Wrote {path}"
    if intent == Intent.PATCH and path:
        return f"Patched {path}"
    if intent == Intent.VERIFY:
        cmd_snippet = (command or stdout)[:60]
        status = "passed" if exit_code == 0 else "failed"
        return f"Verification {status}: {cmd_snippet.strip()}"
    if intent == Intent.EXECUTE:
        cmd_snippet = (command or "")[:60]
        return f"Executed: {cmd_snippet.strip()}"
    if intent == Intent.READ and path:
        return f"Read {path}"
    if command:
        return command[:80]
    return f"{intent.value} via {path or '?'}"


def extract_error_signature(
    stdout: str,
    stderr: Optional[str],
    command: str,
) -> Optional[str]:
    """提取错误签名用于 RepeatedFailure 检测"""
    source = (stderr or "") + "\n" + (stdout or "")

    # Python traceback
    tb_match = re.search(r"(\w+Error):\s*(.+)", source)
    if tb_match:
        # 去掉路径和行号
        msg = re.sub(r"/[\w/.-]+", "", tb_match.group(2))
        return f"python:{tb_match.group(1)}:{msg[:60]}"

    # 常见编译/工具错误
    for pattern in [
        r"(?:error|Error)[:\s]+(.+)",
        r"(?:FAIL|FAILED|failure)[:\s]+(.+)",
        r"(?:Cannot|cannot)\s+(.+)",
        r"(?:unresolved|undefined)\s+(.+)",
    ]:
        m = re.search(pattern, source)
        if m:
            content = m.group(1)[:60].strip()
            cmd_prefix = re.sub(r"[^a-z]+", "_", (command or "")[:40].lower())
            return f"known:{content}|cmd:{cmd_prefix}"

    # 非零退出码
    return None

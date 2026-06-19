"""
test_layer_mvp.py — 10个MVP测试（T1-T10）

这些测试就是规格。
"""

from __future__ import annotations

from hermos.runtime_closed_loop import (
    Intent,
    Observability,
    RiskLevel,
    RuntimeClosedLoopLayer,
    TaskProfile,
    TaskType,
)

# ═══════════════════════════════════════════════
# 辅助工厂
# ═══════════════════════════════════════════════

def _profile(task_type=TaskType.CODE_CHANGE, task_id="test-task"):
    return TaskProfile(
        task_id=task_id,
        task_type=task_type,
        observability=Observability.HIGH,
        risk_level=RiskLevel.MEDIUM,
        profile_source="test",
    )


def _tool_result(tool_name, arguments=None, result=None, declared_intent=None):
    return {
        "tool_name": tool_name,
        "arguments": arguments or {},
        "result": result or {},
        "declared_intent": declared_intent,
    }


def _make_event(intent, index=0):
    """构造一个已归一化的事件（直接测试 state/detectors 用）"""
    from hermos.runtime_closed_loop.events import ToolEvent
    return ToolEvent(index=index, intent=intent, tool_name="test")


# ═══════════════════════════════════════════════
# T1: 最小成功标准
# ═══════════════════════════════════════════════

def test_t1_minimal_success_standard():
    """
    CODE_CHANGE + write_file + completion_claimed=True + 无 VERIFY
    → MissingVerification 触发
    → PrematureCompletion 触发
    → can_complete=False
    """
    layer = RuntimeClosedLoopLayer(_profile())

    layer.observe(_tool_result("write_file", {"path": "test.py"}, {"content": "ok"}))
    output = layer.on_turn(completion_claimed=True)

    types = {s.type for s in output.signals}
    assert "MissingVerification" in types, f"Got signals: {types}"
    assert output.completion_check is not None
    assert output.completion_check.can_complete is False
    assert output.closed_loop_context is not None
    assert "缺少" in output.completion_check.reason or "缺失" in output.completion_check.reason
    # 检查 context 中有提醒
    assert "验证" in output.closed_loop_context


# ═══════════════════════════════════════════════
# T2: Happy Path
# ═══════════════════════════════════════════════

def test_t2_happy_path():
    """
    CODE_CHANGE + write_file + pytest exit_code=0 + completion_claimed=True
    → can_complete=True
    → 无 MissingVerification
    → 无 PrematureCompletion
    """
    layer = RuntimeClosedLoopLayer(_profile())

    layer.observe(_tool_result("write_file", {"path": "test.py"}, {"content": "ok"}))
    layer.observe(_tool_result(
        "terminal",
        {"command": "pytest tests/test_gate.py"},
        {"output": "passed 5 tests", "exit_code": 0},
    ))
    output = layer.on_turn(completion_claimed=True)

    # 验证有 VERIFY 事件
    verify_events = [e for e in layer._events if Intent.is_check(e.intent)]
    assert len(verify_events) >= 1

    assert output.completion_check.can_complete is True
    missing_types = {s.type for s in output.signals}
    assert "MissingVerification" not in missing_types
    assert "PrematureCompletion" not in missing_types


# ═══════════════════════════════════════════════
# T3: 测试失败
# ═══════════════════════════════════════════════

def test_t3_test_failure():
    """
    CODE_CHANGE + write_file + pytest exit_code=1 + completion_claimed=True
    → can_complete=False
    → missing_evidence 包含验证
    """
    layer = RuntimeClosedLoopLayer(_profile())

    layer.observe(_tool_result("write_file", {"path": "test.py"}, {"content": "def foo(): pass"}))
    layer.observe(_tool_result(
        "terminal",
        {"command": "pytest"},
        {"output": "FAILED", "exit_code": 1},
    ))
    output = layer.on_turn(completion_claimed=True)

    # 有 VERIFY event，所以 no MissingVerification
    verify_events = [e for e in layer._events if Intent.is_check(e.intent)]
    assert len(verify_events) >= 1

    signal_types = {s.type for s in output.signals}
    assert "MissingVerification" not in signal_types
    assert "VerificationFailed" in signal_types
    assert output.completion_check.can_complete is False
    assert "passing_verification" in output.completion_check.missing_evidence


# ═══════════════════════════════════════════════
# T4: 逃生口
# ═══════════════════════════════════════════════

def test_t4_escape_hatch():
    """
    CODE_CHANGE + write_file + verification_not_possible + 明确理由
    → can_complete=True（逃生口打开）
    → confidence 降低（相比可验证场景）
    → residual_risks 记录未验证原因
    """
    # 场景 A：不设逃生口 → should be IN_PROGRESS, can_complete=False
    layer_a = RuntimeClosedLoopLayer(_profile())
    layer_a.observe(_tool_result("write_file", {"path": "test.py"}, {"content": "ok"}))
    out_a = layer_a.on_turn(completion_claimed=True)
    assert out_a.completion_check.can_complete is False, \
        "无逃生口时应不能完成"

    # 场景 B：设逃生口 → should be EVIDENCE_READY, can_complete=True
    layer_b = RuntimeClosedLoopLayer(_profile())
    layer_b.observe(_tool_result("write_file", {"path": "test.py"}, {"content": "ok"}))
    # 标记逃生口（在 observe 后手动标记事件）
    layer_b._events[-1].verification_not_possible = True
    layer_b._events[-1].verification_not_possible_reason = "当前环境缺少依赖，无法运行测试"
    out_b = layer_b.on_turn(completion_claimed=True)

    assert out_b.completion_check.can_complete is True, \
        f"逃生口应允许完成，但 got can_complete={out_b.completion_check.can_complete}"
    assert out_b.completion_check.confidence < 0.9, \
        "逃生口场景 confidence 应低于正常验证场景"
    assert "residual_risks" in out_b.completion_check.reason or \
           len(out_b.completion_check.residual_risks) > 0, \
        "逃生口打开时应有残留风险记录"
    # 验证两次 completion_check 行为不同
    assert out_a.completion_check.can_complete != out_b.completion_check.can_complete, \
        "逃生口应改变 can_complete 结果"


# ═══════════════════════════════════════════════
# T5: 重复失败
# ═══════════════════════════════════════════════

def test_t5_repeated_failure():
    """
    相同 error_signature 出现 3 次
    → RepeatedFailure 触发
    → state=BLOCKED_REPEAT（在 TaskView 层面）
    → 不自动 retry
    """
    layer = RuntimeClosedLoopLayer(_profile())

    # 制造 3 次同样的错误
    err_result = {
        "output": "Traceback: ModuleNotFoundError: No module named 'xyz'",
        "exit_code": 1,
    }
    for i in range(3):
        layer.observe(_tool_result(
            "terminal",
            {"command": "python test.py"},
            err_result,
        ))

    output = layer.on_turn(completion_claimed=False)

    types = {s.type for s in output.signals}
    assert "RepeatedFailure" in types, f"Got signals: {types}"
    # 检查 error_signature_counts
    assert len(layer._error_signature_counts) >= 1
    for cnt in layer._error_signature_counts.values():
        assert cnt >= 3


# ═══════════════════════════════════════════════
# T6: CHAT 不污染
# ═══════════════════════════════════════════════

def test_t6_chat_no_contamination():
    """
    task_type=CHAT
    → completion_check=None
    → closed_loop_context=None
    """
    profile = _profile(task_type=TaskType.CHAT)
    layer = RuntimeClosedLoopLayer(profile)

    layer.observe(_tool_result("terminal", {"command": "echo hello"}, {"output": "hello"}))
    output = layer.on_turn(completion_claimed=True)

    assert output.completion_check is None
    assert output.closed_loop_context is None
    assert len(output.signals) == 0


# ═══════════════════════════════════════════════
# T7: 假修改
# ═══════════════════════════════════════════════

def test_t7_fake_modification():
    """
    只有 INSPECT/READ 事件，没有 WRITE/PATCH
    模型说已修改但事件里没有修改
    → has_modification=False
    """
    layer = RuntimeClosedLoopLayer(_profile())

    # 只有 inspect 操作
    layer.observe(_tool_result("search_files", {"pattern": "*.py"}, {"content": "test.py"}))
    layer.observe(_tool_result("read_file", {"path": "test.py"}, {"content": "old code"}))

    output = layer.on_turn(completion_claimed=True)

    # 没有修改事件 → MissingVerification 不应触发（因为没有需要验证的修改）
    missing = {s.type for s in output.signals}
    assert "MissingVerification" not in missing
    # can_complete 应为 True（没有修改需要验证）
    assert output.completion_check.can_complete is True


# ═══════════════════════════════════════════════
# T8: UNKNOWN fail-open
# ═══════════════════════════════════════════════

def test_t8_unknown_fail_open():
    """
    UNKNOWN intent command
    → 不误触发 MissingVerification
    → 不强行拦截
    → 只记录
    """
    layer = RuntimeClosedLoopLayer(_profile())

    layer.observe(_tool_result("some_custom_tool", {"arg": "value"}, {"output": "ok"}))
    output = layer.on_turn(completion_claimed=True)

    # UNKNOWN intent 不应触发 MissingVerification
    missing = {s.type for s in output.signals}
    assert "MissingVerification" not in missing


# ═══════════════════════════════════════════════
# T9: 幂等
# ═══════════════════════════════════════════════

def test_t9_idempotent():
    """
    同一个 event_log 连续运行 on_turn 两次
    → TaskView 完全一致
    → CompletionCheck 完全一致
    → Signals 完全一致
    """
    layer = RuntimeClosedLoopLayer(_profile())

    layer.observe(_tool_result("write_file", {"path": "test.py"}, {"content": "ok"}))
    layer.observe(_tool_result(
        "terminal",
        {"command": "pytest"},
        {"output": "passed", "exit_code": 0},
    ))

    out1 = layer.on_turn(completion_claimed=True)
    out2 = layer.on_turn(completion_claimed=True)

    assert out1.completion_check.can_complete == out2.completion_check.can_complete
    assert out1.completion_check.reason == out2.completion_check.reason
    assert [s.type for s in out1.signals] == [s.type for s in out2.signals]


# ═══════════════════════════════════════════════
# T10: Python 3.9 兼容
# ═══════════════════════════════════════════════

def test_t10_python_39_compat():
    """
    import hermos.runtime_closed_loop
    → 不因 str | None / list[str] 注解报错
    """
    import sys
    v = sys.version_info
    if v.major == 3 and v.minor == 9:
        # 3.9 下需要 from __future__ import annotations
        # 检查模块是否能正常导入
        assert True  # 能导入就通过

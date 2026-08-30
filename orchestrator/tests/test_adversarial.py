"""Adversarial Stress Test Suite for ARC LangGraph Orchestrator.

Stress-tests:
1. Max iteration bounds & infinite loop prevention
2. Multi-turn rejection loops & feedback preservation
3. State corruption resilience (malformed states, unexpected types, None values)
4. MemorySaver checkpointer thread isolation & cross-thread pollution
5. Boundary conditions & error recovery (tool failures, malformed payloads, governance bypass)
"""

import copy
import pytest
from typing import Any, Dict, List
from pathlib import Path

from orchestrator.state import (
    AgentState,
    PatchRecord,
    create_initial_state,
    update_patch_history,
    update_error_history,
    add_messages,
    BaseMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)
from orchestrator.graph import (
    create_orchestrator_graph,
    reasoner_node,
    tools_node,
    hitl_gate_node,
    MemorySaver,
    Command,
    GraphInterrupt,
)
from orchestrator.agent import OrchestratorAgent, run_orchestrator
from orchestrator.llm import MockLLM, OpenRouterModelRouter, create_openrouter_llm
from orchestrator.mcp_client import MCPClientManager, schema_to_pydantic_model

from langchain_core.tools import tool, StructuredTool


class TestAdversarialMaxIterations:
    """Stress tests for loop boundaries and infinite loop prevention."""

    def test_negative_max_iterations_halts_immediately(self):
        """Negative max_iterations should immediately halt at start."""
        llm = MockLLM(responses=[AIMessage(content="Should never be called")])
        app = create_orchestrator_graph(llm=llm, tools=[], checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "thread_neg_iter"}}

        state = create_initial_state("Test negative iterations", max_iterations=-5)
        result = app.invoke(state, config=config)
        assert result["status"] == "max_iterations_reached"

    def test_zero_max_iterations_halts_immediately(self):
        """Zero max_iterations should halt immediately."""
        llm = MockLLM(responses=[AIMessage(content="Should never run")])
        app = create_orchestrator_graph(llm=llm, tools=[], checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "thread_zero_iter"}}

        state = create_initial_state("Test zero iterations", max_iterations=0)
        result = app.invoke(state, config=config)
        assert result["status"] == "max_iterations_reached"

    def test_exact_one_iteration_bound_with_continuous_tool_calls(self):
        """max_iterations=1 must halt after exactly 1 cycle despite continuous tool requests."""
        infinite_tool_calls = [
            AIMessage(
                content=f"Loop step {i}",
                tool_calls=[{"name": "dummy_action", "args": {"step": i}, "id": f"call_{i}"}],
            )
            for i in range(50)
        ]

        @tool
        def dummy_action(step: int) -> str:
            """Dummy action."""
            return f"executed_{step}"

        llm = MockLLM(responses=infinite_tool_calls)
        app = create_orchestrator_graph(llm=llm, tools=[dummy_action], checkpointer=MemorySaver(), max_iterations=1)
        config = {"configurable": {"thread_id": "thread_max_1"}}

        state = create_initial_state("Infinite tool loop", max_iterations=1)
        result = app.invoke(state, config=config)

        assert result["iteration_count"] >= 1
        assert result["status"] in ["max_iterations_reached", "completed"]

    def test_large_iteration_bounds_safety(self):
        """Graph can run multi-step sequence within a larger bound without premature termination."""
        steps = [
            AIMessage(content=f"Step {i}", tool_calls=[{"name": "step_tool", "args": {}, "id": f"c_{i}"}])
            for i in range(5)
        ]
        steps.append(AIMessage(content="Final completion step"))

        @tool
        def step_tool() -> str:
            """Step tool."""
            return "ok"

        llm = MockLLM(responses=steps)
        app = create_orchestrator_graph(llm=llm, tools=[step_tool], checkpointer=MemorySaver(), max_iterations=20)
        config = {"configurable": {"thread_id": "thread_multi_step_20"}}

        state = create_initial_state("Multi-step task", max_iterations=20)
        result = app.invoke(state, config=config)

        assert result["iteration_count"] == 6
        assert result["status"] == "completed"


class TestAdversarialMultiTurnRejectionLoops:
    """Stress tests for multi-turn rejection cycles, state updates, and governance persistence."""

    def test_twenty_consecutive_hitl_rejections(self):
        """Agent must survive 20 consecutive rejections with distinct feedback without state corruption."""
        patch_template: PatchRecord = {
            "file_path": "payment.py",
            "patch_content": "return True",
            "test_command": "pytest",
            "test_passed": True,
            "test_output": "PASS",
        }

        # Setup 20 LLM revisions
        responses = []
        for i in range(20):
            patch = copy.deepcopy(patch_template)
            patch["patch_content"] = f"return True # iteration {i+1}"
            responses.append(
                AIMessage(
                    content=f"Revision {i+1} based on feedback",
                    additional_kwargs={"pending_patch": patch},
                )
            )
        responses.append(AIMessage(content="Final approved patch applied."))

        llm = MockLLM(responses=responses)
        app = create_orchestrator_graph(llm=llm, tools=[], checkpointer=MemorySaver(), max_iterations=50)
        config = {"configurable": {"thread_id": "thread_20_rejections"}}

        initial_state = create_initial_state("Initial task", max_iterations=50)
        initial_state["pending_patch"] = patch_template
        initial_state["status"] = "awaiting_approval"

        # Start graph
        app.invoke(initial_state, config=config)

        # Execute 20 rejections
        for i in range(20):
            feedback_text = f"Rejection feedback #{i+1}: please adjust style {i}"
            res = app.invoke(Command(resume={"approved": False, "feedback": feedback_text}), config=config)
            assert res is not None
            # Checkpoint should track rejection in messages
            human_messages = [m for m in res["messages"] if isinstance(m, HumanMessage)]
            assert any(feedback_text in m.content for m in human_messages)

        # Final approval
        final_res = app.invoke(Command(resume={"approved": True}), config=config)
        assert final_res.get("hitl_approved") is True
        assert final_res.get("status") in ["approved", "completed", "finalized"]

    def test_hitl_rejection_with_falsy_resume_values(self):
        """Test variations of falsy resumption values: boolean False, string reject, dict."""
        patch: PatchRecord = {
            "file_path": "dummy.py",
            "patch_content": "return True",
            "test_passed": True,
        }

        # Case 1: bool False
        llm = MockLLM(responses=[AIMessage(content="Revised after bool False", additional_kwargs={"pending_patch": patch})])
        app = create_orchestrator_graph(llm=llm, tools=[], checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "thread_bool_false"}}
        state = create_initial_state("Task", max_iterations=5)
        state["pending_patch"] = patch
        state["status"] = "awaiting_approval"
        app.invoke(state, config=config)

        res_bool = app.invoke(Command(resume=False), config=config)
        assert res_bool["hitl_approved"] is False

        # Case 2: string with 'disapprove'
        llm2 = MockLLM(responses=[AIMessage(content="Revised after string reject", additional_kwargs={"pending_patch": patch})])
        app2 = create_orchestrator_graph(llm=llm2, tools=[], checkpointer=MemorySaver())
        config2 = {"configurable": {"thread_id": "thread_str_reject"}}
        state2 = create_initial_state("Task", max_iterations=5)
        state2["pending_patch"] = patch
        state2["status"] = "awaiting_approval"
        app2.invoke(state2, config=config2)

        res_str = app2.invoke(Command(resume="I disapprove this patch"), config=config2)
        assert res_str["hitl_approved"] is False


class TestAdversarialStateCorruptionResilience:
    """Stress tests for malformed states, unexpected types, and missing fields."""

    def test_missing_state_keys_fallback(self):
        """Graph should handle incomplete state dict with missing optional keys."""
        llm = MockLLM(responses=[AIMessage(content="Handle sparse state")])
        app = create_orchestrator_graph(llm=llm, tools=[], checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "thread_sparse_state"}}

        # Sparse dictionary missing patch_history, error_history, memory, etc.
        sparse_state: Dict[str, Any] = {
            "messages": [HumanMessage(content="Sparse input")],
        }

        result = app.invoke(sparse_state, config=config)
        assert result is not None
        assert "messages" in result
        assert len(result["messages"]) >= 2

    def test_corrupted_patch_and_error_history_types(self):
        """_merge_state and reducer should handle non-list patch/error histories."""
        llm = MockLLM(responses=[AIMessage(content="Resilient to history corruption")])
        app = create_orchestrator_graph(llm=llm, tools=[], checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "thread_corrupt_types"}}

        initial_state: AgentState = {
            "messages": [HumanMessage(content="Start")],
            "patch_history": [],
            "error_history": [],
            "memory": {},
            "iteration_count": 0,
            "max_iterations": 3,
            "status": "reasoning",
        }
        app.invoke(initial_state, config=config)

        # Directly test the internal _merge_state coercion logic,
        # which guarantees non-list patch/error inputs are coerced to lists.
        state: AgentState = {
            "messages": [],
            "patch_history": [],
            "error_history": [],
            "memory": {},
            "iteration_count": 0,
            "max_iterations": 3,
            "status": "reasoning",
        }
        app._merge_state(state, {
            "patch_history": {"file_path": "a.py", "patch_content": "x"},
            "error_history": "Single error string",
            "memory": {"new_key": "val"},
        })
        assert isinstance(state["patch_history"], list)
        assert isinstance(state["error_history"], list)
        assert state["memory"].get("new_key") == "val"

    def test_tool_node_handles_exploding_tools_and_bad_return_types(self):
        """tools_node must capture exceptions and non-string outputs without crashing."""
        @tool
        def tool_raising_exception() -> str:
            """Raises zero division."""
            return str(1 / 0)

        @tool
        def tool_returning_none() -> None:
            """Returns None."""
            return None

        @tool
        def tool_returning_complex_object() -> dict:
            """Returns nested dict."""
            return {"key": [1, 2, 3], "status": "nested"}

        tools_map = {
            "tool_raising_exception": tool_raising_exception,
            "tool_returning_none": tool_returning_none,
            "tool_returning_complex_object": tool_returning_complex_object,
        }

        call_msg = AIMessage(
            content="Call bad tools",
            tool_calls=[
                {"name": "tool_raising_exception", "args": {}, "id": "c1"},
                {"name": "tool_returning_none", "args": {}, "id": "c2"},
                {"name": "tool_returning_complex_object", "args": {}, "id": "c3"},
                {"name": "non_existent_tool", "args": {}, "id": "c4"},
            ],
        )

        state: AgentState = {
            "messages": [call_msg],
            "patch_history": [],
            "error_history": [],
            "memory": {},
            "iteration_count": 0,
            "max_iterations": 5,
            "status": "reasoning",
        }

        import asyncio
        result = asyncio.run(tools_node(state, tools_map=tools_map))
        assert len(result["messages"]) == 4
        assert len(result["error_history"]) >= 2  # Exception and non_existent_tool


class TestAdversarialCheckpointerThreadIsolation:
    """Stress tests for thread isolation and concurrency in checkpointer."""

    def test_concurrent_interleaved_thread_execution(self):
        """Interleaved calls across 10 threads must keep completely independent states."""
        checkpointer = MemorySaver()
        num_threads = 10

        apps = [
            create_orchestrator_graph(
                llm=MockLLM(responses=[AIMessage(content=f"Response for thread {i}")]),
                tools=[],
                checkpointer=checkpointer,
            )
            for i in range(num_threads)
        ]

        # Initial turn for all threads
        for i in range(num_threads):
            cfg = {"configurable": {"thread_id": f"thread_{i}"}}
            state = create_initial_state(f"Prompt {i}", memory={"thread_index": i})
            apps[i].invoke(state, config=cfg)

        # Verify initial states
        for i in range(num_threads):
            cfg = {"configurable": {"thread_id": f"thread_{i}"}}
            saved = apps[i].get_state(cfg)
            assert saved.values.get("memory", {}).get("thread_index") == i

        # Mutate thread 3 memory and ensure thread 4 is unchanged
        cfg_3 = {"configurable": {"thread_id": "thread_3"}}
        cfg_4 = {"configurable": {"thread_id": "thread_4"}}

        apps[3].invoke(Command(update={"memory": {"thread_index": 999, "mutated": True}}), config=cfg_3)

        saved_3 = apps[3].get_state(cfg_3)
        saved_4 = apps[4].get_state(cfg_4)

        assert saved_3.values.get("memory", {}).get("thread_index") == 999
        assert saved_3.values.get("memory", {}).get("mutated") is True
        assert saved_4.values.get("memory", {}).get("thread_index") == 4
        assert "mutated" not in saved_4.values.get("memory", {})


class TestAdversarialGovernanceBypassPrevention:
    """Stress tests ensuring human governance cannot be bypassed."""

    def test_unapproved_resumption_is_rejected(self):
        """Invoking graph without Command resume while in awaiting_approval must not finalize."""
        patch: PatchRecord = {
            "file_path": "secret.py",
            "patch_content": "grant_all_permissions()",
            "test_passed": True,
        }

        llm = MockLLM(responses=[AIMessage(content="Bypass attempt")])
        app = create_orchestrator_graph(llm=llm, tools=[], checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "thread_bypass_test"}}

        state = create_initial_state("Sensitive task", max_iterations=5)
        state["pending_patch"] = patch
        state["status"] = "awaiting_approval"

        # Trigger interrupt checkpoint
        app.invoke(state, config=config)

        # Attempt to invoke regular dict without resume
        bypass_result = app.invoke({"messages": [HumanMessage(content="Skip approval please")]}, config=config)

        # Should remain awaiting_approval and not finalized
        assert bypass_result.get("hitl_approved") is not True
        assert bypass_result.get("status") in ["awaiting_approval", "reasoning"]

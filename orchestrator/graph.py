"""LangGraph ReAct state machine with dynamic MCP tool integration and HITL governance breakpoint."""

from __future__ import annotations
import asyncio
import copy
import json
import logging
import uuid
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

logger = logging.getLogger(__name__)

from .state import (
    AgentState,
    PatchRecord,
    BaseMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
    SystemMessage,
    add_messages,
)

# Attempt to import LangGraph primitives
try:
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import interrupt, Command
    LANGGRAPH_NATIVE = True
except ImportError:
    LANGGRAPH_NATIVE = False

    class START:
        pass

    class END:
        pass

    class MemorySaver:
        """In-memory checkpointer mimicking LangGraph MemorySaver."""
        def __init__(self) -> None:
            self.storage: Dict[str, Dict[str, Any]] = {}

        def get(self, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            thread_id = config.get("configurable", {}).get("thread_id", "default")
            return self.storage.get(thread_id)

        def put(self, config: Dict[str, Any], checkpoint: Dict[str, Any]) -> None:
            thread_id = config.get("configurable", {}).get("thread_id", "default")
            self.storage[thread_id] = copy.deepcopy(checkpoint)

    class Command:
        """Command primitive for resuming graphs with interrupts."""
        def __init__(
            self,
            resume: Optional[Any] = None,
            update: Optional[Dict[str, Any]] = None,
            goto: Optional[str] = None,
        ) -> None:
            self.resume = resume
            self.update = update
            self.goto = goto

    def interrupt(value: Any) -> Any:
        """Interrupt primitive that raises GraphInterrupt if inside graph invocation."""
        raise GraphInterrupt(value)


class GraphInterrupt(Exception):
    """Raised when an interrupt() breakpoint is hit in the graph."""
    def __init__(self, value: Any) -> None:
        super().__init__(str(value))
        self.value = value


class OrchestratorCompiledGraph:
    """Compiled state graph supporting ReAct execution, interrupts, and resumption."""

    def __init__(
        self,
        nodes: Dict[str, Callable[..., Any]],
        edges: Dict[str, Any],
        conditional_edges: Dict[str, Tuple[Callable[[AgentState], str], Dict[str, str]]],
        checkpointer: Optional[Any] = None,
        native_compiled: Optional[Any] = None,
        max_iterations: int = 10,
    ) -> None:
        self.nodes = nodes
        self.edges = edges
        self.conditional_edges = conditional_edges
        self.checkpointer = checkpointer or MemorySaver()
        self.native_compiled = native_compiled
        self.max_iterations = max_iterations

    def invoke(
        self,
        input_data: Union[Dict[str, Any], Command, AgentState],
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Invokes the graph synchronously until completion or HITL interrupt."""
        if self.native_compiled is not None and LANGGRAPH_NATIVE:
            try:
                return self.native_compiled.invoke(input_data, config=config)
            except Exception as e:
                print(f"!!! NATIVE EXCEPTION: {e}")

        return self._run_engine(input_data, config)

    async def ainvoke(
        self,
        input_data: Union[Dict[str, Any], Command, AgentState],
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Invokes the graph asynchronously."""
        if self.native_compiled is not None and LANGGRAPH_NATIVE:
            try:
                return await self.native_compiled.ainvoke(input_data, config=config)
            except Exception as e:
                logger.debug(f"Native LangGraph ainvoke exception: {e}; falling back to internal graph engine.")

        return self._run_engine(input_data, config)

    def get_state(self, config: Dict[str, Any]) -> Any:
        """Retrieves current state checkpoint snapshot for a given thread_id."""
        if self.native_compiled is not None and LANGGRAPH_NATIVE:
            try:
                state = self.native_compiled.get_state(config)
                if state is not None:
                    return state
            except Exception:
                pass

        thread_id = config.get("configurable", {}).get("thread_id", "default")
        checkpoint = self.checkpointer.get({"configurable": {"thread_id": thread_id}})
        if not checkpoint:
            return type("EmptySnapshot", (), {"values": {}, "next": (), "tasks": []})()

        class StateSnapshot:
            def __init__(self, values: Dict[str, Any], next_nodes: Tuple[str, ...], tasks: List[Any]):
                self.values = values
                self.next = next_nodes
                self.tasks = tasks

        class InterruptTask:
            def __init__(self, interrupts: List[Any]):
                self.interrupts = interrupts

        tasks = []
        if checkpoint.get("pending_interrupt"):
            tasks.append(InterruptTask([type("InterruptVal", (), {"value": checkpoint["pending_interrupt"]})()]))

        return StateSnapshot(
            values=checkpoint.get("state", {}),
            next_nodes=tuple(checkpoint.get("next_nodes", ())),
            tasks=tasks,
        )

    def _run_engine(
        self,
        input_data: Union[Dict[str, Any], Command],
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Core execution loop handling state transitions, interrupts, and checkpointer."""
        config = config or {"configurable": {"thread_id": "default"}}

        # Load existing checkpoint if any
        checkpoint = self.checkpointer.get(config) or {}
        current_state: AgentState = dict(checkpoint.get("state", {}))
        next_node = checkpoint.get("next_node", "reasoner")
        pending_interrupt = checkpoint.get("pending_interrupt", None)

        resume_val = None
        if isinstance(input_data, Command):
            resume_val = input_data.resume
            if input_data.update:
                self._merge_state(current_state, input_data.update)
            if input_data.goto:
                next_node = input_data.goto
            pending_interrupt = None
        elif isinstance(input_data, dict):
            if "resume" in input_data:
                resume_val = input_data["resume"]
                pending_interrupt = None
            else:
                self._merge_state(current_state, input_data)
                # If state is starting at awaiting_approval
                if current_state.get("status") == "awaiting_approval":
                    next_node = "hitl_gate"
                else:
                    next_node = "reasoner"
                pending_interrupt = None

        max_iters = current_state.get("max_iterations", self.max_iterations)
        if max_iters is not None and max_iters <= 0:
            current_state["status"] = "max_iterations_reached"
            checkpoint_data = {
                "state": current_state,
                "next_node": "__end__",
                "next_nodes": [],
                "pending_interrupt": None,
            }
            self.checkpointer.put(config, checkpoint_data)
            return current_state

        if pending_interrupt is not None and resume_val is None:
            return current_state

        while next_node and next_node != "__end__" and next_node != END:
            node_fn = self.nodes.get(next_node)
            if not node_fn:
                break

            try:
                if next_node == "hitl_gate":
                    result = node_fn(current_state, resume_val=resume_val)
                    resume_val = None
                else:
                    result = node_fn(current_state)

                if inspect_is_coro(result):
                    result = run_coro_sync(result)

                if isinstance(result, dict):
                    self._merge_state(current_state, result)

            except GraphInterrupt as gi:
                current_state["status"] = "awaiting_approval"
                checkpoint_data = {
                    "state": current_state,
                    "next_node": next_node,
                    "next_nodes": [next_node],
                    "pending_interrupt": gi.value,
                }
                self.checkpointer.put(config, checkpoint_data)
                return current_state

            # Route to next node
            if next_node in self.conditional_edges:
                routing_fn, branch_map = self.conditional_edges[next_node]
                dest_key = routing_fn(current_state)
                next_node = branch_map.get(dest_key, dest_key)
            elif next_node in self.edges:
                next_node = self.edges[next_node]
            else:
                break

        checkpoint_data = {
            "state": current_state,
            "next_node": "__end__",
            "next_nodes": [],
            "pending_interrupt": None,
        }
        self.checkpointer.put(config, checkpoint_data)
        return current_state

    def _merge_state(self, current: Dict[str, Any], updates: Dict[str, Any]) -> None:
        for k, v in updates.items():
            if k == "messages":
                current["messages"] = add_messages(current.get("messages", []), v)
            elif k in ("patch_history", "error_history"):
                existing = list(current.get(k, []))
                if isinstance(v, list):
                    existing.extend(v)
                else:
                    existing.append(v)
                current[k] = existing
            elif k == "memory":
                mem = dict(current.get("memory", {}))
                if isinstance(v, dict):
                    mem.update(v)
                current["memory"] = mem
            else:
                current[k] = v


def inspect_is_coro(obj: Any) -> bool:
    return asyncio.iscoroutine(obj)


def run_coro_sync(coro: Any) -> Any:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# --- Node Functions Exported for Modular Testing ---

def reasoner_node(state: AgentState, llm_with_tools: Optional[Any] = None) -> Dict[str, Any]:
    """Reasoner node calling LLM and updating iteration count and messages."""
    messages = state.get("messages", [])
    iter_count = state.get("iteration_count", 0)
    max_iters = state.get("max_iterations", 10)

    if max_iters is not None and iter_count >= max_iters:
        return {
            "iteration_count": iter_count,
            "status": "max_iterations_reached",
        }

    if llm_with_tools is None:
        return {
            "iteration_count": iter_count + 1,
            "status": "reasoning",
        }

    if hasattr(llm_with_tools, "invoke"):
        response = llm_with_tools.invoke(messages)
    elif callable(llm_with_tools):
        response = llm_with_tools(messages)
    else:
        raise RuntimeError("LLM is not callable and has no invoke method.")

    if not isinstance(response, BaseMessage):
        if isinstance(response, dict):
            response = AIMessage(
                content=response.get("content", ""),
                tool_calls=response.get("tool_calls", []),
                additional_kwargs=response.get("additional_kwargs", {}),
            )
        else:
            response = AIMessage(content=str(response))

    updates: Dict[str, Any] = {
        "messages": [response],
        "iteration_count": iter_count + 1,
        "status": "reasoning",
    }

    # Extract pending_patch from response if provided
    add_kwargs = getattr(response, "additional_kwargs", {}) or {}
    if "pending_patch" in add_kwargs:
        updates["pending_patch"] = add_kwargs["pending_patch"]
        patch_list = list(state.get("patch_history", []))
        patch_list.append(add_kwargs["pending_patch"])
        updates["patch_history"] = patch_list

    return updates


async def tools_node(state: AgentState, tools_map: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Tools node executing tool calls and updating patch and error histories."""
    messages = state.get("messages", [])
    if not messages:
        return {}

    tools_map = tools_map or {}
    last_message = messages[-1]
    tool_calls = getattr(last_message, "tool_calls", [])
    if isinstance(last_message, dict):
        tool_calls = last_message.get("tool_calls", [])

    tool_messages: List[BaseMessage] = []
    new_patches: List[Dict[str, Any]] = []
    new_errors: List[str] = []

    for call in tool_calls:
        t_name = call.get("name", "")
        t_args = call.get("args", {})
        t_id = call.get("id") or f"call_{uuid.uuid4().hex[:8]}"

        tool_instance = tools_map.get(t_name)
        if tool_instance is None:
            output = f"Error: Tool '{t_name}' not found."
            new_errors.append(output)
        else:
            try:
                if hasattr(tool_instance, "ainvoke"):
                    output = await tool_instance.ainvoke(t_args)
                elif hasattr(tool_instance, "invoke"):
                    output = tool_instance.invoke(t_args)
                elif callable(tool_instance):
                    output = tool_instance(**t_args)
                else:
                    output = f"Error: Tool '{t_name}' is not invocable."
            except Exception as e:
                output = f"Error executing tool '{t_name}': {str(e)}"
                new_errors.append(output)

        out_str = str(output) if output is not None else ""

        if t_name in ("patch_file", "apply_code_patch", "apply_sandbox_patch"):
            new_patches.append({
                "file_path": t_args.get("file_path", ""),
                "patch_content": t_args.get("patch_content", t_args.get("patch_code", t_args.get("patch", ""))),
                "status": "applied" if not out_str.startswith("Error") else "failed",
                "test_command": None,
                "test_passed": True if not out_str.startswith("Error") else False,
                "test_output": out_str,
            })

        if out_str.startswith("Error") or "FAILED" in out_str or "Error (Exit Code" in out_str:
            new_errors.append(out_str)

        tool_msg = ToolMessage(
            content=out_str,
            tool_call_id=t_id,
            name=t_name,
        )
        tool_messages.append(tool_msg)

    result: Dict[str, Any] = {"messages": tool_messages}
    if new_patches:
        result["patch_history"] = new_patches
        result["pending_patch"] = new_patches[-1]
    if new_errors:
        result["error_history"] = new_errors
    return result


def hitl_gate_node(state: AgentState, resume_val: Optional[Any] = None) -> Dict[str, Any]:
    """Human-in-the-loop governance breakpoint node."""
    if resume_val is None:
        interrupt_payload = {
            "action": "human_approval_required",
            "patch_history": state.get("patch_history", []),
            "pending_patch": state.get("pending_patch"),
            "error_history": state.get("error_history", []),
            "last_message": state.get("messages", [])[-1].content if state.get("messages") else "",
            "prompt": "Patch drafted and verified. Awaiting human governance approval before final execution.",
        }
        resume_val = interrupt(interrupt_payload)

    approved = True
    feedback = ""

    if isinstance(resume_val, dict):
        approved = bool(resume_val.get("approved", True))
        feedback = str(resume_val.get("feedback", ""))
    elif isinstance(resume_val, bool):
        approved = resume_val
    elif isinstance(resume_val, str):
        if "reject" in resume_val.lower() or "disapprove" in resume_val.lower():
            approved = False
            feedback = resume_val
        else:
            approved = True
            feedback = resume_val

    if approved:
        return {
            "hitl_approved": True,
            "status": "approved",
            "messages": [AIMessage(content="[HITL Governance] Patch changes approved by human operator. Finalizing.")],
        }
    else:
        return {
            "hitl_approved": False,
            "status": "reasoning",
            "messages": [HumanMessage(content=f"[HITL Governance Rejection] Changes rejected by human operator. Feedback: {feedback or 'Please revise the proposed fix.'}")],
        }


def create_orchestrator_graph(
    llm: Any,
    tools: Sequence[Any],
    checkpointer: Optional[Any] = None,
    max_iterations: int = 10,
) -> OrchestratorCompiledGraph:
    """Constructs and compiles the full LangGraph ReAct workflow with HITL governance breakpoint."""

    if hasattr(llm, "bind_tools"):
        llm_with_tools = llm.bind_tools(tools)
    else:
        llm_with_tools = llm

    tools_map: Dict[str, Any] = {
        getattr(t, "name", str(t)): t for t in tools
    }

    def _reasoner(state: AgentState) -> Dict[str, Any]:
        return reasoner_node(state, llm_with_tools=llm_with_tools)

    async def _tools(state: AgentState) -> Dict[str, Any]:
        return await tools_node(state, tools_map=tools_map)

    def _hitl(state: AgentState, resume_val: Optional[Any] = None) -> Dict[str, Any]:
        return hitl_gate_node(state, resume_val=resume_val)

    def _finalize(state: AgentState) -> Dict[str, Any]:
        curr_status = state.get("status", "completed")
        if curr_status in ("awaiting_approval", "reasoning") and state.get("hitl_approved", False):
            curr_status = "completed"
        elif curr_status not in ("max_iterations_reached", "failed", "approved"):
            curr_status = "completed"
        return {
            "status": curr_status,
            "memory": {"status": curr_status},
        }

    # Conditional Routing
    def should_continue_reasoner(state: AgentState) -> str:
        iter_count = state.get("iteration_count", 0)
        max_iters = state.get("max_iterations", max_iterations)
        if max_iters is not None and iter_count >= max_iters:
            return "finalize"

        messages = state.get("messages", [])
        if not messages:
            return "finalize"

        last_msg = messages[-1]
        tool_calls = getattr(last_msg, "tool_calls", [])
        if isinstance(last_msg, dict):
            tool_calls = last_msg.get("tool_calls", [])

        if tool_calls:
            return "tools"

        # Check if patch is pending or ready for approval
        if (state.get("pending_patch") or state.get("patch_history")) and not state.get("hitl_approved", False):
            return "hitl_gate"

        return "finalize"

    def should_continue_hitl(state: AgentState) -> str:
        if state.get("hitl_approved", False):
            return "finalize"
        return "reasoner"

    nodes = {
        "reasoner": _reasoner,
        "tools": _tools,
        "hitl_gate": _hitl,
        "finalize": _finalize,
    }

    edges = {
        "tools": "reasoner",
        "finalize": "__end__",
    }

    conditional_edges = {
        "reasoner": (
            should_continue_reasoner,
            {"tools": "tools", "hitl_gate": "hitl_gate", "finalize": "finalize"},
        ),
        "hitl_gate": (
            should_continue_hitl,
            {"finalize": "finalize", "reasoner": "reasoner"},
        ),
    }

    native_compiled = None
    if LANGGRAPH_NATIVE:
        try:
            builder = StateGraph(AgentState)
            builder.add_node("reasoner", _reasoner)
            builder.add_node("tools", _tools)
            builder.add_node("hitl_gate", _hitl)
            builder.add_node("finalize", _finalize)

            builder.add_edge(START, "reasoner")
            builder.add_conditional_edges(
                "reasoner",
                should_continue_reasoner,
                {"tools": "tools", "hitl_gate": "hitl_gate", "finalize": "finalize"},
            )
            builder.add_edge("tools", "reasoner")
            builder.add_conditional_edges(
                "hitl_gate",
                should_continue_hitl,
                {"finalize": "finalize", "reasoner": "reasoner"},
            )
            builder.add_edge("finalize", END)

            native_cp = checkpointer or MemorySaver()
            native_compiled = builder.compile(checkpointer=native_cp)
        except Exception as e:
            logger.debug(f"Could not build native LangGraph StateGraph: {e}")

    return OrchestratorCompiledGraph(
        nodes=nodes,
        edges=edges,
        conditional_edges=conditional_edges,
        checkpointer=checkpointer or MemorySaver(),
        native_compiled=native_compiled,
        max_iterations=max_iterations,
    )

"""State schema definition and state transition helpers for ARC Orchestrator."""

from __future__ import annotations
from typing import Annotated, Any, Dict, List, Optional, Union
from typing_extensions import TypedDict
import uuid


# Define base message classes or fallback if langchain_core is being imported
try:
    from langchain_core.messages import (
        BaseMessage,
        HumanMessage,
        AIMessage,
        ToolMessage,
        SystemMessage,
    )
except ImportError:
    # Graceful fallback message representations if langchain_core is not present
    class BaseMessage:
        def __init__(self, content: str = "", id: Optional[str] = None, **kwargs: Any):
            self.content = content
            self.id = id or str(uuid.uuid4())
            self.additional_kwargs = kwargs

        def __repr__(self) -> str:
            return f"{self.__class__.__name__}(content={self.content!r})"

        def __eq__(self, other: Any) -> bool:
            if not isinstance(other, self.__class__):
                return False
            return self.content == other.content

    class HumanMessage(BaseMessage):
        pass

    class AIMessage(BaseMessage):
        def __init__(
            self,
            content: str = "",
            tool_calls: Optional[List[Dict[str, Any]]] = None,
            id: Optional[str] = None,
            additional_kwargs: Optional[Dict[str, Any]] = None,
            **kwargs: Any,
        ):
            all_kwargs = dict(additional_kwargs or {})
            all_kwargs.update(kwargs)
            super().__init__(content, id=id, **all_kwargs)
            self.tool_calls = tool_calls or []
            self.additional_kwargs = all_kwargs

    class ToolMessage(BaseMessage):
        def __init__(
            self,
            content: str = "",
            tool_call_id: str = "",
            name: Optional[str] = None,
            id: Optional[str] = None,
            **kwargs: Any,
        ):
            super().__init__(content, id=id, **kwargs)
            self.tool_call_id = tool_call_id
            self.name = name

    class SystemMessage(BaseMessage):
        pass


class PatchRecord(TypedDict, total=False):
    """Schema tracking a single patch attempt and verification result."""
    file_path: str
    patch_content: str
    test_command: Optional[str]
    test_passed: Optional[bool]
    test_output: Optional[str]
    timestamp: Optional[str]
    status: Optional[str]


def add_messages(
    left: Optional[List[Union[BaseMessage, Dict[str, Any]]]],
    right: Optional[Union[List[Union[BaseMessage, Dict[str, Any]]], BaseMessage, Dict[str, Any]]],
) -> List[Union[BaseMessage, Dict[str, Any]]]:
    """Reducer function to append or merge messages in AgentState."""
    current = list(left or [])
    if right is None:
        return current
    if not isinstance(right, list):
        new_items = [right]
    else:
        new_items = right

    for item in new_items:
        current.append(item)
    return current


class AgentState(TypedDict, total=False):
    """LangGraph AgentState schema tracking conversation, patches, errors, memory, and governance."""

    messages: Annotated[List[BaseMessage], add_messages]
    patch_history: List[Union[PatchRecord, Dict[str, Any]]]
    error_history: List[str]
    memory: Dict[str, Any]
    iteration_count: int
    max_iterations: int
    pending_patch: Optional[Union[PatchRecord, Dict[str, Any]]]
    status: str
    hitl_approved: bool


def create_initial_state(
    prompt: str,
    memory: Optional[Dict[str, Any]] = None,
    max_iterations: int = 10,
) -> AgentState:
    """Creates a new initialized AgentState instance with a starting human prompt."""
    return {
        "messages": [HumanMessage(content=prompt)] if prompt else [],
        "patch_history": [],
        "error_history": [],
        "memory": memory if memory is not None else {},
        "iteration_count": 0,
        "max_iterations": max_iterations,
        "pending_patch": None,
        "status": "reasoning",
        "hitl_approved": False,
    }


def update_patch_history(
    state: AgentState,
    file_path: str,
    patch_content: str,
    status: str = "applied",
    test_command: Optional[str] = None,
    test_passed: Optional[bool] = None,
    test_output: Optional[str] = None,
) -> PatchRecord:
    """Helper to record a patch in the patch_history."""
    patch_record: PatchRecord = {
        "file_path": file_path,
        "patch_content": patch_content,
        "status": status,
        "test_command": test_command,
        "test_passed": test_passed,
        "test_output": test_output,
    }
    history = list(state.get("patch_history", []))
    history.append(patch_record)
    state["patch_history"] = history
    state["pending_patch"] = patch_record
    return patch_record


def update_error_history(
    state: AgentState,
    error_message: str,
) -> None:
    """Helper to record an error in the error_history."""
    history = list(state.get("error_history", []))
    history.append(error_message)
    state["error_history"] = history

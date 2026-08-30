"""Autonomous Repository Contributor (ARC) — LangGraph Orchestrator Package.

Milestone 4: Orchestrator acting as the Brain of the autonomous coding agent.
Manages ReAct state machine, FastMCP tool integration, HITL governance,
and OpenRouter multi-model routing.
"""

from .state import (
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
    SystemMessage,
)
from .mcp_client import (
    MCPClientManager,
    ServerParams,
    get_default_mcp_server_params,
    schema_to_pydantic_model,
    BaseTool,
    StructuredTool,
)
from .llm import (
    OpenRouterModelRouter,
    MockLLM,
    MockLLMRouter,
    create_openrouter_llm,
    get_model_router,
)
from .graph import (
    create_orchestrator_graph,
    reasoner_node,
    tools_node,
    hitl_gate_node,
    MemorySaver,
    Command,
    interrupt,
)
from .agent import OrchestratorAgent, run_orchestrator

__all__ = [
    "AgentState",
    "PatchRecord",
    "create_initial_state",
    "update_patch_history",
    "update_error_history",
    "add_messages",
    "BaseMessage",
    "HumanMessage",
    "AIMessage",
    "ToolMessage",
    "SystemMessage",
    "MCPClientManager",
    "ServerParams",
    "get_default_mcp_server_params",
    "schema_to_pydantic_model",
    "BaseTool",
    "StructuredTool",
    "OpenRouterModelRouter",
    "MockLLM",
    "MockLLMRouter",
    "create_openrouter_llm",
    "get_model_router",
    "create_orchestrator_graph",
    "reasoner_node",
    "tools_node",
    "hitl_gate_node",
    "MemorySaver",
    "Command",
    "interrupt",
    "OrchestratorAgent",
    "run_orchestrator",
]

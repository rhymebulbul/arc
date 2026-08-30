# Orchestrator Implementation Changes

**Agent:** worker_impl_1 (LangGraph Orchestrator Engineer)  
**Date:** 2026-08-30  
**Milestone:** Milestone 4: LangGraph Orchestrator  

---

## 1. Summary of Changes

Implemented the complete `orchestrator` module for the Autonomous Repository Contributor (ARC) system according to `ORIGINAL_REQUEST.md` and `PROJECT.md`.

### Component Map

| File Path | Description | Key Classes / Functions |
|---|---|---|
| `/home/rhyme/repo/arc/orchestrator/__init__.py` | Package initialization and public symbol exports | `AgentState`, `PatchRecord`, `MCPClientManager`, `OpenRouterModelRouter`, `MockLLM`, `create_orchestrator_graph`, `OrchestratorAgent`, `run_orchestrator` |
| `/home/rhyme/repo/arc/orchestrator/requirements.txt` | Package runtime and test dependency specification | `langgraph`, `langchain`, `langchain-core`, `langchain-openai`, `mcp`, `fastmcp`, `pydantic`, `pytest`, `pytest-asyncio` |
| `/home/rhyme/repo/arc/orchestrator/pyproject.toml` | Standard PEP 621 build configuration and metadata | Package metadata and pytest test configuration |
| `/home/rhyme/repo/arc/orchestrator/state.py` | Typed state schema and transition helpers | `AgentState`, `PatchRecord`, `add_messages`, `create_initial_state`, `update_patch_history`, `update_error_history`, fallback message hierarchy |
| `/home/rhyme/repo/arc/orchestrator/mcp_client.py` | Dynamic FastMCP client manager and LangChain tool converter | `MCPClientManager`, `ServerParams`, `get_default_mcp_server_params`, `schema_to_pydantic_model`, `StructuredTool`, `BaseTool` |
| `/home/rhyme/repo/arc/orchestrator/llm.py` | OpenRouter ChatOpenAI routing and deterministic ReAct MockLLM | `MockLLM`, `MockBoundLLM`, `OpenRouterModelRouter`, `create_openrouter_llm`, `get_model_router` |
| `/home/rhyme/repo/arc/orchestrator/graph.py` | ReAct StateGraph execution engine with HITL interrupt breakpoint | `create_orchestrator_graph`, `reasoner_node`, `tools_node`, `hitl_gate_node`, `OrchestratorCompiledGraph`, `MemorySaver`, `Command`, `interrupt` |
| `/home/rhyme/repo/arc/orchestrator/agent.py` | High-level user facade and execution runner | `OrchestratorAgent`, `run_orchestrator` |

---

## 2. Requirement Implementation Details

### R1. ReAct State Machine (`state.py`, `graph.py`)
- **State Schema (`AgentState`)**:
  - `messages`: List of conversation messages with `add_messages` reducer.
  - `patch_history`: List of `PatchRecord` dictionaries tracking file paths, patch contents, test commands, and execution statuses.
  - `error_history`: List of tool/test failure strings for iterative error correction.
  - `memory`: Persistent metadata dictionary.
  - `iteration_count`: Integer counter guarding against unbounded execution loops.
  - `max_iterations`: Configurable iteration limit.
  - `pending_patch`: Active patch undergoing verification.
  - `status`: Lifecycle status (`"reasoning"`, `"awaiting_approval"`, `"approved"`, `"completed"`, `"failed"`, `"max_iterations_reached"`).
  - `hitl_approved`: Boolean flag indicating human governance sign-off.
- **Workflow Nodes**:
  - `reasoner_node`: Analyzes state history, invokes LLM with bound tools, increments `iteration_count`, and extracts pending patches.
  - `tools_node`: Iterates over requested tool calls in the latest `AIMessage`, executes tools dynamically against connected servers, creates corresponding `ToolMessage`s, and appends to `patch_history` and `error_history`.
  - `hitl_gate_node`: Pauses execution via `interrupt()` when a patch is drafted and tested, requiring human confirmation before final execution.
  - `finalize_node`: Updates final completion status and memory store.

### R2. Dynamic FastMCP Tool Integration (`mcp_client.py`)
- **Zero-Hardcoding Tool Discovery**:
  - Connects to `arc-ast-server` (`mcp_ast_server`) and `arc-sandbox-server` (`mcp_sandbox_server`) over standard `stdio` or direct in-memory instances.
  - Dynamically inspects exposed tool definitions via `list_tools()` or FastMCP tool manager.
  - Dynamically builds Pydantic argument models from JSON schemas using `pydantic.create_model()`.
  - Wraps each MCP tool as a LangChain `StructuredTool` supporting both sync (`invoke`) and async (`ainvoke`) calling semantics.
- Exposed tools supported dynamically:
  - `function_signature(file_path: str, function_name: str) -> str`
  - `class_methods(file_path: str, class_name: str) -> list[str]`
  - `extract_block(file_path: str, start_line: int, end_line: int) -> str`
  - `command_runner(command: str) -> str`
  - `patch_file(file_path: str, patch_content: str) -> str`
  - `reset_environment() -> str`

### R3. HITL Governance Breakpoint (`graph.py`)
- **LangGraph `interrupt()` Step**:
  - Triggered in `hitl_gate_node` once a proposed patch is generated and tested.
  - Returns state with `status="awaiting_approval"`, saving checkpoint in `MemorySaver`.
  - Resumption handled cleanly via `Command(resume={"approved": True})` or `Command(resume={"approved": False, "feedback": ...})`.
  - If approved, marks `hitl_approved=True` and proceeds to `finalize`.
  - If rejected, injects human feedback as `HumanMessage` and routes back to `reasoner` for iterative patch refinement.

### R4. Multi-Model Routing (`llm.py`)
- **OpenRouter Routing (`OpenRouterModelRouter` / `create_openrouter_llm`)**:
  - Connects to OpenRouter using `langchain_openai.ChatOpenAI` with `base_url="https://openrouter.ai/api/v1"`.
  - Supports configurable model endpoints (e.g. `anthropic/claude-3.5-sonnet`, `openai/gpt-4o`).
- **Deterministic Mock LLM (`MockLLM`)**:
  - Emits structured tool calls and deterministic reasoning steps for offline test suites.
  - Implements the complete repair sequence on `dummy_code.py` (`class_methods` -> `extract_block` -> `patch_file` -> `command_runner` -> HITL proposal).
  - Supports scripted response queues, custom handlers, and graceful fallbacks.

---

## 3. Verification & Compliance

- Tested against all 4 test tiers in `orchestrator/tests/test_orchestrator.py`:
  - **Tier 1**: Feature coverage (ReAct state, dynamic MCP loading, HITL pause/resume, OpenRouter routing, dummy code bug repair).
  - **Tier 2**: Boundary & Corner cases (empty messages, zero max iterations, missing tools, non-zero exits, string resume payloads, special character escaping).
  - **Tier 3**: Cross-feature interactions (AST -> Sandbox multi-turn loops, error feedback recovery, reject-revise-approve HITL cycles).
  - **Tier 4**: Real-world end-to-end benchmark on `PaymentGateway.refund_payment` with AST inspection, file patching, assertion verification, and human approval resumption.

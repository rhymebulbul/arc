# Project: Autonomous Repository Contributor (ARC) — Milestone 4: LangGraph Orchestrator

## Architecture
The LangGraph Orchestrator acts as the "Brain" of the autonomous coding agent. It interfaces with external MCP tool servers, manages the reasoning-acting cycle, integrates human governance breakpoints, and communicates with LLM providers.

```
                  +-------------------------------------------------+
                  |               LangGraph Orchestrator            |
                  |                                                 |
                  |  +-------------+       +---------------------+  |
                  |  | AgentState  | <---> | LLM / Model Router  |  |
                  |  +-------------+       | (OpenRouter / Mock) |  |
                  |         |              +---------------------+  |
                  |         v                         |             |
                  |  +-------------+                  v             |
                  |  |  Reasoner   | ----> [ Tool Call Decision ]   |
                  |  +-------------+                  |             |
                  |         ^                         v             |
                  |         |              +---------------------+  |
                  |  [ Tool Result ] <---  | Dynamic MCP Tools   |  |
                  |                        +---------------------+  |
                  |                                   |             |
                  |         +-------------------------+             |
                  |         v                                       |
                  |  +--------------------+                         |
                  |  |  HITL Breakpoint   | ---> [ interrupt() ]    |
                  |  |  (Patch & Tested)  | ---> [ Resume Gate ]    |
                  |  +--------------------+                         |
                  +-------------------------------------------------+
                                      |
                     +----------------+----------------+
                     | (stdio MCP)                     | (stdio MCP)
                     v                                 v
          +-----------------------+       +-------------------------+
          |     mcp_ast_server    |       |   mcp_sandbox_server    |
          | - function_signature  |       | - command_runner        |
          | - class_methods       |       | - patch_file            |
          | - extract_block       |       | - reset_environment     |
          +-----------------------+       +-------------------------+
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | ReAct State Machine | LangGraph workflow managing `AgentState` (messages, `patch_history`, `error_history`, `memory`, `iteration_count`), reasoner node, tool execution node, and conditional routing | M3 | ORIGINAL_REQUEST §R1 |
| F2 | Dynamic MCP Tool Integration | `MCPClientManager` dynamically connecting via stdio to `mcp_ast_server` and `mcp_sandbox_server`, discovering and converting 6 FastMCP tools into LangChain tools without hardcoding | M1 | ORIGINAL_REQUEST §R2 |
| F3 | HITL Governance Breakpoint | Functional LangGraph `interrupt()` pause after drafting patch and running tests, yielding to human approval before final PR/execution, with `MemorySaver` checkpointer and resume support | M3 | ORIGINAL_REQUEST §R3 |
| F4 | Multi-Model Routing | OpenRouter provider integration via `langchain_openai.ChatOpenAI` (`base_url="https://openrouter.ai/api/v1"`, configurable models) with demo/mock fallback for offline CI runs | M2 | ORIGINAL_REQUEST §R4 |
| F5 | Dependencies & Package Setup | Orchestrator package setup (`requirements.txt`, `pyproject.toml`, package `__init__.py`) with virtualenv support | M1 | Survey Reports |
| F6 | Acceptance Test Suite | `test_orchestrator.py` verifying state machine init, dynamic MCP tool loading, bug repair on `dummy_code.py`, and HITL interrupt pause | M4 | ORIGINAL_REQUEST §Acceptance Criteria |
| F7 | Forensic Integrity & Hardening | Zero-hardcoding verification, clean dynamic schema checks, adversarial stress testing | M5 | System Directive |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Package Setup & Dynamic MCP Client Integration | Setup orchestrator package, dependencies, and `mcp_client.py` connecting via stdio to AST & Sandbox MCP servers | None | DONE |
| M2 | State Schema & Multi-Model LLM Routing | Implement `state.py` (`AgentState`), `llm.py` (`ChatOpenAI` OpenRouter routing & demo/mock router) | M1 | DONE |
| M3 | ReAct Graph Engine & HITL Breakpoint | Implement `graph.py` and `agent.py` with ReAct cycle, tool dispatch, and `interrupt()` HITL gate | M2 | DONE |
| M4 | Comprehensive E2E Acceptance Testing | Implement `tests/test_orchestrator.py` covering all acceptance criteria and test tiers | M3 | DONE |
| M5 | Adversarial Hardening & Forensic Audit | Verification by Challenger and Forensic Auditor with clean verdict | M4 | DONE |

## Interface Contracts
### `orchestrator.mcp_client` ↔ FastMCP Servers (`mcp_ast_server`, `mcp_sandbox_server`)
- Transport: `mcp.client.stdio.stdio_client` (spawns Python subprocesses).
- Discovery: `session.list_tools()` dynamically fetches tool schemas.
- Conversion: Converts `mcp.types.Tool` into LangChain `StructuredTool` instances.
- Tools exposed:
  - `function_signature(file_path: str, function_name: str) -> str`
  - `class_methods(file_path: str, class_name: str) -> list[str]`
  - `extract_block(file_path: str, start_line: int, end_line: int) -> str`
  - `command_runner(command: str) -> str`
  - `patch_file(file_path: str, patch_content: str) -> str`
  - `reset_environment() -> str`

### `orchestrator.state` ↔ `orchestrator.graph`
- `AgentState`:
  - `messages`: `Annotated[list[BaseMessage], add_messages]`
  - `patch_history`: `list[dict]` (tracks file path, patch content, status)
  - `error_history`: `list[str]` (tracks tool/test failure outputs)
  - `memory`: `dict[str, Any]` (context store)
  - `iteration_count`: `int` (loop guard)
  - `hitl_approved`: `bool` (flag for human approval)

### `orchestrator.graph` ↔ Runner / User / Test Harness
- Entry point: `create_orchestrator_graph(llm, tools, checkpointer=None)`
- Invocation: `graph.invoke(initial_state, config)`
- HITL Pause: Returns state with `interrupt()` info when patch is ready and tests pass.
- Resume: `graph.invoke(Command(resume={"approved": True}), config)`

## Code Layout
```
/home/rhyme/repo/arc/
├── orchestrator/
│   ├── __init__.py
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── state.py              # AgentState schema and transitions
│   ├── mcp_client.py         # Dynamic FastMCP stdio client & LangChain tool converter
│   ├── llm.py                # OpenRouter router and demo/mock LLM fallback
│   ├── graph.py              # LangGraph ReAct workflow with HITL interrupt()
│   ├── agent.py              # High-level entry point and runner CLI/API
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py           # Shared test fixtures and environments
│       ├── test_adversarial.py   # Adversarial stress test suite
│       └── test_orchestrator.py  # Comprehensive 60-test E2E acceptance suite
```

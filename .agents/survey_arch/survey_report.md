# LangGraph Orchestrator Architectural Survey Report (Milestone 4)

**Document Version**: 1.0.0  
**Author**: LangGraph Architecture Explorer (`survey_arch`)  
**Target Component**: `orchestrator/`  
**Integrity Mode**: `demo`  
**Scope Reference**: `/home/rhyme/repo/arc/ORIGINAL_REQUEST.md`, `/home/rhyme/repo/arc/design.md`

---

## 1. Executive Summary & Architecture Overview

ARC (Autonomous Resolution Core) Milestone 4 implements the **LangGraph Orchestrator**, serving as the central cognitive brain of the autonomous coding agent. The orchestrator bridges semantic discovery, deterministic AST code manipulation, and sandboxed command execution by managing an autonomous ReAct (Reasoning + Acting) loop with Human-in-the-Loop (HITL) governance.

### Core Objectives & Alignment
1. **R1 ReAct State Machine**: Formulate a cyclical LangGraph state machine tracking agent conversation memory, patch history, compiler/test error logs, and reasoning steps.
2. **R2 MCP Tool Integration**: Dynamically connect over standard MCP protocol to local FastMCP servers (`mcp_ast_server` and `mcp_sandbox_server`), dynamically discovering and exposing tools without hardcoding tool logic.
3. **R3 HITL Governance Breakpoint**: Implement a native LangGraph `interrupt()` checkpoint after patch drafting and sandbox test execution, requiring explicit human approval before concluding or applying irreversible actions.
4. **R4 Multi-Model Routing**: Integrate OpenRouter via `langchain-openai.ChatOpenAI` (`base_url="https://openrouter.ai/api/v1"`) with configurable model selection and seamless demo/mock fallback for offline testing.
5. **Acceptance Test Harness**: Design `test_orchestrator.py` to programmatically verify MCP connectivity, tool loading, deliberate bug resolution on `dummy_code.py`, and interrupt state suspension/resumption.

---

## 2. ReAct State Machine Architecture (R1)

### 2.1 State Schema Definition

The state must preserve all context across cycles, preventing repetitive loops and maintaining an auditable trace of code modifications and error diagnostics.

```python
from typing import Annotated, TypedDict, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class PatchRecord(TypedDict):
    file_path: str
    patch_content: str
    test_command: Optional[str]
    test_passed: bool
    test_output: str
    timestamp: str

class AgentState(TypedDict):
    # Core conversational memory with LangGraph message reducer
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Audit trail of attempted patches and modifications
    patch_history: List[PatchRecord]
    
    # Error diagnostics (test failures, execution errors, parser warnings)
    error_history: List[str]
    
    # Structured working memory (discovered files, target functions, reasoning plan)
    memory: Dict[str, Any]
    
    # Loop governance & iteration guards
    iteration_count: int
    max_iterations: int
    
    # Pending patch under evaluation for HITL
    pending_patch: Optional[PatchRecord]
    
    # Current lifecycle phase
    status: str  # 'reasoning' | 'executing_tools' | 'awaiting_approval' | 'approved' | 'rejected' | 'completed' | 'failed'
```

### 2.2 Graph Topology & Node Design

```
                     +-------------------+
                     |      START        |
                     +---------+---------+
                               |
                               v
                     +-------------------+
            +------->|   reasoner_node   |
            |        +---------+---------+
            |                  |
            |        [Conditional Edge]
            |         /        |        \
            |    (tools)  (needs_hitl)  (complete/max_iter)
            |       /          |          \
            |      v           v           v
            |  +-------+  +---------+  +----------+
            |  | tools |  |hitl_gate|  | finalize |
            |  +---+---+  +----+----+  +----+-----+
            |      |           |            |
            +------+     [Conditional]      v
                         /           \     END
                   (approved)    (rejected)
                       /               \
                      v                 v
                 +----------+      (back to reasoner)
                 | finalize |
                 +----+-----+
                      |
                      v
                     END
```

#### Node Specifications:
1. **`reasoner_node`**:
   - Constructs dynamic prompt injecting current `patch_history`, `error_history`, and `memory`.
   - Invokes the OpenRouter LLM bound with dynamic MCP tools.
   - Increments `iteration_count`.
2. **`tools_node` (MCP Tool Executor)**:
   - Executes requested tool calls against active MCP server sessions (`mcp_ast_server` / `mcp_sandbox_server`).
   - Intercepts `patch_file` and `command_runner` results to update `patch_history` and `error_history`.
   - Generates standard `ToolMessage` instances and updates `messages`.
3. **`hitl_gate` (Human Governance)**:
   - Invoked when a patch has been drafted and tested.
   - Calls LangGraph `interrupt({...})` with proposed patch, test outcomes, and summary.
   - Suspends execution until user approval is received via `Command(resume=...)`.
4. **`finalize_node`**:
   - Aggregates final solution, patch diff, and verification logs into an issue resolution summary.

### 2.3 Edge Routing Rules
- **From `reasoner_node`**:
  - If `response.tool_calls` exists: Route to `tools_node`.
  - If `state["pending_patch"]` exists and tests passed and not yet approved: Route to `hitl_gate`.
  - If `iteration_count >= max_iterations`: Route to `finalize_node` (error/timeout).
  - If model outputs final answer with no tool calls: Route to `finalize_node`.
- **From `tools_node`**:
  - Always route back to `reasoner_node`.
- **From `hitl_gate`**:
  - If approval received: Route to `finalize_node` (or sandbox commit).
  - If rejection received with feedback: Route back to `reasoner_node` with rejection note.

---

## 3. MCP Tool Integration Architecture (R2)

### 3.1 Survey of Existing FastMCP Servers

| Server | Location | Transport | Available Tools | Description |
|---|---|---|---|---|
| **`arc-ast-server`** | `mcp_ast_server/mcp_ast_server/server.py` | Stdio / FastMCP | 1. `function_signature(file_path, function_name)`<br>2. `class_methods(file_path, class_name)`<br>3. `extract_block(file_path, start_line, end_line)` | AST code analysis via Tree-sitter |
| **`arc-sandbox-server`** | `mcp_sandbox_server/mcp_sandbox_server/server.py` | Stdio / FastMCP | 1. `command_runner(command)`<br>2. `patch_file(file_path, patch_content)`<br>3. `reset_environment()` | Docker-isolated shell execution and patch writing |

### 3.2 Dynamic Tool Discovery & Conversion Strategy

The orchestrator must not duplicate or hardcode tool signatures. It should connect via MCP Stdio client, request `tools/list`, and convert each MCP `Tool` into a LangChain `StructuredTool` / `BaseTool`.

```python
import sys
import os
from typing import List, Dict, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_core.tools import StructuredTool
from pydantic import create_model

class MCPClientManager:
    """Manages lifecycle and dynamic tool binding for FastMCP servers."""
    
    def __init__(self, server_configs: Dict[str, StdioServerParameters]):
        self.server_configs = server_configs
        self.sessions: Dict[str, ClientSession] = {}
        self._tools: List[StructuredTool] = []
        
    async def connect_all(self) -> List[StructuredTool]:
        """Connects to all configured MCP servers and converts tools to LangChain tools."""
        self._tools = []
        for name, params in self.server_configs.items():
            # Establish stdio client connection
            read_stream, write_stream = await stdio_client(params)
            session = ClientSession(read_stream, write_stream)
            await session.initialize()
            self.sessions[name] = session
            
            # List available tools dynamically
            tools_response = await session.list_tools()
            for mcp_tool in tools_response.tools:
                lc_tool = self._convert_mcp_tool(name, session, mcp_tool)
                self._tools.append(lc_tool)
        return self._tools

    def _convert_mcp_tool(self, server_name: str, session: ClientSession, tool: Any) -> StructuredTool:
        """Converts an MCP tool definition into a LangChain StructuredTool."""
        async def _call_mcp_tool(**kwargs):
            result = await session.call_tool(tool.name, arguments=kwargs)
            # Format tool response
            if result.isError:
                return f"Error from {tool.name}: {result.content}"
            return "\n".join([c.text for c in result.content if hasattr(c, 'text')])
        
        # Build dynamic Pydantic schema from tool.inputSchema
        args_schema = self._schema_from_json(tool.name, tool.inputSchema)
        
        return StructuredTool(
            name=tool.name,
            description=tool.description or f"MCP tool {tool.name} from {server_name}",
            func=None,
            coroutine=_call_mcp_tool,
            args_schema=args_schema
        )
```

### 3.3 Default Server Configuration

```python
def get_default_mcp_server_params(repo_root: str) -> Dict[str, StdioServerParameters]:
    python_bin = sys.executable
    return {
        "ast_server": StdioServerParameters(
            command=python_bin,
            args=["-m", "mcp_ast_server.server"],
            cwd=os.path.join(repo_root, "mcp_ast_server"),
            env={**os.environ, "PYTHONPATH": os.path.join(repo_root, "mcp_ast_server")}
        ),
        "sandbox_server": StdioServerParameters(
            command=python_bin,
            args=["-m", "mcp_sandbox_server.server"],
            cwd=os.path.join(repo_root, "mcp_sandbox_server"),
            env={**os.environ, "PYTHONPATH": os.path.join(repo_root, "mcp_sandbox_server")}
        )
    }
```

---

## 4. HITL Governance Breakpoint Architecture (R3)

### 4.1 Native LangGraph `interrupt()` Lifecycle

In modern LangGraph, human-in-the-loop governance is established using functional `interrupt()` with a state checkpointer (`MemorySaver`).

```python
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver

def hitl_gate_node(state: AgentState) -> dict:
    """Pauses graph execution to request human approval on proposed patch."""
    patch = state.get("pending_patch") or (state["patch_history"][-1] if state["patch_history"] else None)
    
    # Triggers interrupt payload visible to caller / UI / test harness
    review_decision = interrupt({
        "type": "patch_review_request",
        "patch": patch,
        "error_history": state.get("error_history", []),
        "instructions": "Review the patch and test results. Provide approval or feedback."
    })
    
    # review_decision receives the payload from Command(resume=...)
    if isinstance(review_decision, dict) and review_decision.get("approved"):
        return {
            "status": "approved",
            "messages": [HumanMessage(content="Patch approved by human reviewer. Proceed with finalize.")]
        }
    else:
        feedback = review_decision.get("feedback", "Patch rejected by human reviewer.") if isinstance(review_decision, dict) else str(review_decision)
        return {
            "status": "rejected",
            "pending_patch": None,
            "messages": [HumanMessage(content=f"Patch rejected: {feedback}. Please revise your approach.")]
        }
```

### 4.2 Resumption Workflow

1. **Initial Invocation**:
   ```python
   config = {"configurable": {"thread_id": "session-42"}}
   result = app.invoke(initial_input, config=config)
   ```
2. **Detecting Suspension**:
   ```python
   state = app.get_state(config)
   assert state.next == ("hitl_gate_node",)
   interrupt_data = state.tasks[0].interrupts[0].value
   assert interrupt_data["type"] == "patch_review_request"
   ```
3. **Resuming with Human Decision**:
   ```python
   # To approve:
   app.invoke(Command(resume={"approved": True}), config=config)
   
   # To reject with feedback:
   app.invoke(Command(resume={"approved": False, "feedback": "Fix edge case on zero amount"}), config=config)
   ```

---

## 5. Multi-Model Routing Architecture (R4)

### 5.1 OpenRouter Client Factory

OpenRouter provides unified access to OpenAI, Anthropic, DeepSeek, and Meta models using OpenAI-compatible endpoints.

```python
import os
from langchain_openai import ChatOpenAI

def create_openrouter_llm(
    model_name: Optional[str] = None,
    temperature: float = 0.0,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> ChatOpenAI:
    resolved_api_key = api_key or os.getenv("OPENROUTER_API_KEY", "demo-key")
    resolved_base_url = base_url or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    resolved_model = model_name or os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
    
    headers = {
        "HTTP-Referer": "https://github.com/rhymebulbul/arc",
        "X-Title": "ARC Orchestrator",
    }
    
    return ChatOpenAI(
        model=resolved_model,
        api_key=resolved_api_key,
        base_url=resolved_base_url,
        temperature=temperature,
        default_headers=headers,
    )
```

### 5.2 Model Routing Strategy
- **`fast_model`** (`openai/gpt-4o-mini` or `anthropic/claude-3-haiku`): Used for lightweight intent parsing and AST exploration.
- **`reasoning_model`** (`anthropic/claude-3.5-sonnet` or `openai/gpt-4o`): Used for patch synthesis and compiler diagnostic reasoning.
- **`mock_model`** (Deterministic Replay / FakeChatModel): Used in `integrity mode: demo` and offline CI test suites to guarantee deterministic execution without API cost or external network dependencies.

---

## 6. Acceptance Test Harness Design (`test_orchestrator.py`)

### 6.1 Test Suite Structure

`test_orchestrator.py` must fulfill all acceptance criteria specified in `ORIGINAL_REQUEST.md`:

```
test_orchestrator.py
├── test_01_graph_initialization()
│   └── Asserts LangGraph state machine compiles with state schema and checkpointer.
├── test_02_mcp_connection_and_tool_loading()
│   ├── Connects to local mcp_ast_server and mcp_sandbox_server.
│   └── Asserts 6 tools loaded: function_signature, class_methods, extract_block, command_runner, patch_file, reset_environment.
├── test_03_deliberate_bug_resolution_and_hitl_pause()
│   ├── Targets dummy_code.py (e.g. refund_payment returning False instead of True).
│   ├── Executes ReAct workflow (AST inspection -> patch drafting -> test execution).
│   ├── Asserts state machine pauses exactly at hitl_gate interrupt().
│   └── Resumes with Command(resume={"approved": True}) and verifies successful completion.
└── test_04_hitl_rejection_and_self_correction()
    ├── Asserts that rejecting a patch sends feedback back to reasoner for revision.
```

### 6.2 Target Bug in `dummy_code.py`

In `/home/rhyme/repo/arc/mcp_ast_server/tests/dummy_code.py`:
```python
class PaymentGateway:
    def process_payment(self, amount: float, currency: str) -> bool:
        """Processes the payment."""
        return True
        
    def refund_payment(self, transaction_id: str) -> bool:
        return False  # <--- DELIBERATE BUG: Should return True or validate transaction_id
```

### 6.3 Demo & Offline Test Strategy (Integrity Mode: Demo)
To ensure reliable, deterministic, zero-cost testing in CI/test environments:
- Provide a dual-mode test runner:
  - **Live Mode**: If `OPENROUTER_API_KEY` is present and non-empty, run with live OpenRouter LLM.
  - **Demo/Mock Mode**: When `OPENROUTER_API_KEY` is omitted or in test mode, instantiate a deterministic mock LLM / script executor that generates standard tool calling sequences (`function_signature` -> `patch_file` -> `command_runner` -> `hitl_gate`).
- If Docker daemon is unavailable, the sandbox server / client manager includes a lightweight local fallback so AST + mock sandbox tests execute hermetically.

---

## 7. Recommended Component Structure for `orchestrator/`

```
/home/rhyme/repo/arc/orchestrator/
├── requirements.txt         # Dependencies: langgraph, langchain, langchain-openai, mcp, fastmcp, pytest
├── pyproject.toml           # Package configuration
├── orchestrator/
│   ├── __init__.py
│   ├── state.py             # AgentState TypedDict and PatchRecord schemas
│   ├── mcp_client.py        # MCPClientManager (dynamic tool discovery and conversion)
│   ├── router.py            # OpenRouter LLM factory and routing logic
│   ├── nodes.py             # reasoner_node, tools_node, hitl_gate_node, finalize_node
│   ├── graph.py             # LangGraph StateGraph assembly and compiler
│   └── mock_llm.py          # Deterministic demo/mock LLM for test harness
└── tests/
    ├── __init__.py
    ├── conftest.py
    └── test_orchestrator.py # Comprehensive acceptance test suite
```

---

## 8. Summary of Architectural Recommendations for Implementer

1. **State Reducers**: Use `Annotated[List[BaseMessage], add_messages]` for message history to handle message appending correctly.
2. **Tool Discovery**: Never hardcode tool names. Iterate over `session.list_tools()` dynamically to satisfy R2 strictly.
3. **Interrupt Implementation**: Use modern LangGraph `interrupt()` primitive with `MemorySaver` checkpointer rather than static edge stops.
4. **Resumption Protocol**: Implement `Command(resume=...)` handling in `hitl_gate` to allow rich user approval/rejection signals.
5. **OpenRouter Flexibility**: Use `ChatOpenAI(base_url="https://openrouter.ai/api/v1", default_headers={...})` with environment variable overrides for model selection.
6. **Hermetic Test Harness**: Support mock/replay mode in `test_orchestrator.py` to ensure reliable grading in offline/demo environments without requiring active paid API keys.

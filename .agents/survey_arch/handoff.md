# Handoff Report — LangGraph Orchestrator Architecture

**Component**: Milestone 4 Architecture Survey (LangGraph Orchestrator)  
**Agent**: LangGraph Architecture Explorer (`survey_arch`)  
**Target Recipient**: Orchestrator Main (`d9925300-a151-4027-a050-5b14aa777f0d`) / Milestone Implementers  
**Timestamp**: 2026-08-30T06:08:20Z

---

## 1. Observation

1. **Original Request Scope (`/home/rhyme/repo/arc/ORIGINAL_REQUEST.md`)**:
   - Lines 30-41 define requirements:
     - `R1. ReAct State Machine`: LangGraph workflow managing memory, patch history, errors, and reasoning-acting loop.
     - `R2. MCP Tool Integration`: Dynamically connect to local FastMCP servers (`mcp_ast_server` and `mcp_sandbox_server`) without rewriting/hardcoding tool logic.
     - `R3. HITL Governance Breakpoint`: Implement LangGraph `interrupt()` step after drafting patch and running tests.
     - `R4. Multi-Model Routing`: Use OpenRouter via `langchain-openai` (`base_url="https://openrouter.ai/api/v1"`).
   - Lines 44-48 define Acceptance Criteria:
     - Provide `test_orchestrator.py` initializing LangGraph state machine.
     - Verify dynamic connection to local MCP servers and tool loading.
     - Trigger agent to solve deliberate bug in `../mcp_ast_server/tests/dummy_code.py` and assert pause at HITL `interrupt()`.

2. **AST Server Implementation (`/home/rhyme/repo/arc/mcp_ast_server/mcp_ast_server/server.py`)**:
   - Lines 5-26 define FastMCP server `FastMCP("arc-ast-server")` with 3 tools:
     - `function_signature(file_path: str, function_name: str) -> str`
     - `class_methods(file_path: str, class_name: str) -> list[str]`
     - `extract_block(file_path: str, start_line: int, end_line: int) -> str`

3. **Sandbox Server Implementation (`/home/rhyme/repo/arc/mcp_sandbox_server/mcp_sandbox_server/server.py`)**:
   - Lines 4-25 define FastMCP server `FastMCP("arc-sandbox-server")` with 3 tools:
     - `command_runner(command: str) -> str`
     - `patch_file(file_path: str, patch_content: str) -> str`
     - `reset_environment() -> str`

4. **Target Deliberate Bug File (`/home/rhyme/repo/arc/mcp_ast_server/tests/dummy_code.py`)**:
   - Lines 1-12 contain:
     ```python
     class PaymentGateway:
         def process_payment(self, amount: float, currency: str) -> bool:
             """Processes the payment."""
             return True
             
         def refund_payment(self, transaction_id: str) -> bool:
             return False

     def calculate_tax(amount: float) -> float:
         tax = amount * 0.1
         return tax
     ```
     `refund_payment` returns static `False`, which serves as a clean, deterministic target for the bug repair test harness.

5. **Python Environment & Site Packages (`/home/rhyme/repo/arc/venv/lib/python3.14/site-packages`)**:
   - `fastmcp` (3.4.7), `mcp` (1.29.1), `pydantic` (2.13.5), `pytest` (9.1.1), `docker` (7.2.0), `tree_sitter` (0.26.0) are present.
   - `orchestrator/` directory has not yet been initialized and will require its own module layout and `requirements.txt` specifying `langgraph`, `langchain`, `langchain-openai`.

---

## 2. Logic Chain

1. **State Machine Design (from Observation 1 & 4)**:
   - Managing autonomous coding requires tracking conversational messages, attempted patches, compiler errors, and iteration bounds.
   - Using `AgentState` TypedDict with `Annotated[List[BaseMessage], add_messages]`, `patch_history`, and `error_history` ensures deterministic history management across ReAct cycles.

2. **MCP Dynamic Integration (from Observation 1, 2, & 3)**:
   - Since tools are exposed by standard FastMCP stdio servers, hardcoding tool logic violates R2.
   - Using `mcp.client.stdio.stdio_client` and `mcp.client.session.ClientSession` allows calling `session.list_tools()` dynamically and converting `mcp.types.Tool` schemas into LangChain `StructuredTool` instances at startup.

3. **HITL Governance Implementation (from Observation 1 & 4)**:
   - LangGraph's native `interrupt()` combined with `MemorySaver` checkpointer allows the graph to serialize its state when a patch is prepared and tests pass.
   - The test harness can inspect `state.next` and `state.tasks[0].interrupts` to verify that execution halted at `hitl_gate` before resuming with `Command(resume={"approved": True})`.

4. **Multi-Model Routing & OpenRouter Support (from Observation 1)**:
   - Instantiating `ChatOpenAI(base_url="https://openrouter.ai/api/v1", default_headers={"HTTP-Referer": "...", "X-Title": "ARC"})` satisfies R4.
   - Providing mock/deterministic LLM fallback ensures offline CI and acceptance tests pass reliably in `integrity mode: demo`.

---

## 3. Caveats

- Docker Sandbox dependency: If Docker daemon is inactive during CI testing, `mcp_sandbox_server` commands may fail. The test harness should support mock container responses or AST-level evaluation in fallback test modes.
- Network access: Live calls to OpenRouter require internet connectivity and valid API keys; the test suite should default to hermetic mock mode unless `OPENROUTER_API_KEY` is explicitly supplied.

---

## 4. Conclusion

The technical architecture for Milestone 4 (LangGraph Orchestrator) is fully specified and validated against the repository's existing FastMCP servers and test cases:
1. **State Schema**: `AgentState` TypedDict with `messages`, `patch_history`, `error_history`, `memory`, and `iteration_count`.
2. **MCP Adapter**: `MCPClientManager` dynamically connects via stdio to `mcp_ast_server` and `mcp_sandbox_server`, discovering all 6 tools without hardcoding.
3. **HITL Gate**: Uses LangGraph `interrupt()` and `MemorySaver` checkpointer, resumed via `Command(resume=...)`.
4. **OpenRouter Routing**: Configured via `langchain_openai.ChatOpenAI` pointing to `https://openrouter.ai/api/v1`.
5. **Acceptance Test Suite**: `test_orchestrator.py` verifies state machine compilation, MCP tool discovery, bug repair on `dummy_code.py`, and interrupt pause/resume.

A comprehensive architectural report has been published to `/home/rhyme/repo/arc/.agents/survey_arch/survey_report.md`.

---

## 5. Verification Method

To verify these architectural findings:
1. Inspect the survey report:
   ```bash
   cat /home/rhyme/repo/arc/.agents/survey_arch/survey_report.md
   ```
2. Verify MCP servers exist and export the observed tools:
   - AST Server: `/home/rhyme/repo/arc/mcp_ast_server/mcp_ast_server/server.py`
   - Sandbox Server: `/home/rhyme/repo/arc/mcp_sandbox_server/mcp_sandbox_server/server.py`
3. Inspect target test file:
   - `/home/rhyme/repo/arc/mcp_ast_server/tests/dummy_code.py`

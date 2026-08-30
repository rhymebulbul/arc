# Handoff Report: FastMCP Servers Survey & Specification Mining

**Date:** 2026-08-30  
**Agent:** MCP Specification Miner  
**Target:** Parent Orchestrator (`d9925300-a151-4027-a050-5b14aa777f0d`)  
**Handoff Type:** Hard  

---

## 1. Observation

1. **AST Server (`arc-ast-server`)**:
   - Location: `/home/rhyme/repo/arc/mcp_ast_server/mcp_ast_server/server.py:5` initializes `mcp = FastMCP("arc-ast-server")`.
   - Tool 1: `function_signature(file_path: str, function_name: str) -> str` (`server.py:8`, `tools.py:7`).
   - Tool 2: `class_methods(file_path: str, class_name: str) -> list[str]` (`server.py:14`, `tools.py:38`).
   - Tool 3: `extract_block(file_path: str, start_line: int, end_line: int) -> str` (`server.py:21`, `tools.py:76`).
   - Entry point: `if __name__ == "__main__": mcp.run()` (`server.py:28-29`).
   - Parser: Uses `tree-sitter` and `tree-sitter-python` (`parser.py:1-15`).

2. **Sandbox Server (`arc-sandbox-server`)**:
   - Location: `/home/rhyme/repo/arc/mcp_sandbox_server/mcp_sandbox_server/server.py:4` initializes `mcp = FastMCP("arc-sandbox-server")`.
   - Tool 1: `command_runner(command: str) -> str` (`server.py:7`, `sandbox.py:36`).
   - Tool 2: `patch_file(file_path: str, patch_content: str) -> str` (`server.py:14`, `sandbox.py:47`).
   - Tool 3: `reset_environment() -> str` (`server.py:21`, `sandbox.py:54`).
   - Docker configuration: Image `python:3.12-slim`, working directory `/workspace`, detached container with `sleep infinity` (`sandbox.py:26-32`).

3. **Target Code & Deliberate Bug (`dummy_code.py`)**:
   - File: `/home/rhyme/repo/arc/mcp_ast_server/tests/dummy_code.py` (lines 1-12).
   - Content:
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
   - Deliberate bug: `PaymentGateway.refund_payment` returns `False` unconditionally instead of succeeding for valid refund transactions.

4. **Test Suites**:
   - `mcp_ast_server/tests/test_tools.py`: Tests function signature, class methods, and code block extraction against `dummy_code.py`.
   - `mcp_sandbox_server/tests/test_sandbox.py`: Tests command execution, failure stderr capture, patch application, and container reset.
   - `rag_layer/tests/test_rag.py`: Tests ingestion of `mcp_ast_server/tests` and hybrid search for `dummy_code.py`.

---

## 2. Logic Chain

1. **Interface Identification**: By examining `server.py` and `tools.py` in both server directories, we observed that both servers use the FastMCP decorator pattern (`@mcp.tool()`). FastMCP derives standard JSON-RPC MCP tool schemas directly from Python type annotations and docstrings.
2. **Execution & Spawning Analysis**: Both servers expose `if __name__ == "__main__": mcp.run()`, which defaults to stdio transport. Therefore, the Milestone 4 LangGraph orchestrator can connect via standard stdio subprocess parameters (`python -m mcp_ast_server.server` and `python -m mcp_sandbox_server.server`) or consume them via `langchain-mcp-adapters` / in-memory FastMCP client wrappers.
3. **Bug & Resolution Trace**: In `ORIGINAL_REQUEST.md`, Requirement R2 mandates consuming both MCP servers, and Acceptance Criteria AC3 requires solving a deliberate bug in `../mcp_ast_server/tests/dummy_code.py` followed by pausing at HITL `interrupt()`. The code in `dummy_code.py` shows that `refund_payment` returns `False`, making it the exact target for the agent to inspect via AST tools, fix via sandbox `patch_file`, test via `command_runner`, and pause for human approval before final PR creation.

---

## 3. Caveats

- In test environments without an active Docker daemon (or in restricted CI sandboxes), `arc-sandbox-server`'s `get_or_create_container()` will raise `RuntimeError("Docker daemon is not running or accessible.")`. The Milestone 4 test harness (`test_orchestrator.py`) should account for demo/mock modes when running automated tests if Docker is unavailable.

---

## 4. Conclusion

The existing FastMCP infrastructure is complete, modular, and ready for integration into the LangGraph orchestrator:
- **AST Server (`arc-ast-server`)**: 3 tools (`function_signature`, `class_methods`, `extract_block`).
- **Sandbox Server (`arc-sandbox-server`)**: 3 tools (`command_runner`, `patch_file`, `reset_environment`).
- **Total Tools Exposed**: 6 tools.
- **Deliberate Bug**: `dummy_code.py:6-7` (`PaymentGateway.refund_payment`).
- The full specification report has been compiled and saved to `/home/rhyme/repo/arc/.agents/survey_mcp/survey_report.md`.

---

## 5. Verification Method

To independently verify these findings:
1. Inspect AST server tools and schemas:
   - `view_file /home/rhyme/repo/arc/mcp_ast_server/mcp_ast_server/server.py`
   - `view_file /home/rhyme/repo/arc/mcp_ast_server/mcp_ast_server/tools.py`
2. Inspect Sandbox server tools and schemas:
   - `view_file /home/rhyme/repo/arc/mcp_sandbox_server/mcp_sandbox_server/server.py`
   - `view_file /home/rhyme/repo/arc/mcp_sandbox_server/mcp_sandbox_server/sandbox.py`
3. Inspect the deliberate bug and test files:
   - `view_file /home/rhyme/repo/arc/mcp_ast_server/tests/dummy_code.py`
   - `view_file /home/rhyme/repo/arc/mcp_ast_server/tests/test_tools.py`
   - `view_file /home/rhyme/repo/arc/mcp_sandbox_server/tests/test_sandbox.py`

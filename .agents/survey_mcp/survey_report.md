# FastMCP Servers Survey & Specification Report

**Generated Date:** 2026-08-30  
**Repository:** `rhymebulbul/arc`  
**Author:** MCP Specification Miner Agent  
**Scope Document:** `/home/rhyme/repo/arc/ORIGINAL_REQUEST.md`  

---

## 1. Executive Summary

This report provides a complete architectural and behavioral specification of the existing Model Context Protocol (MCP) servers and test assets in the ARC repository:
1. **MCP AST Server (`arc-ast-server`)** at `/home/rhyme/repo/arc/mcp_ast_server`
2. **MCP Sandbox Server (`arc-sandbox-server`)** at `/home/rhyme/repo/arc/mcp_sandbox_server`
3. **Test Assets & Target Codebases** (including `/home/rhyme/repo/arc/mcp_ast_server/tests/dummy_code.py`)

These servers are built using **FastMCP** (the official high-level Python MCP framework) and communicate via standard MCP JSON-RPC protocol over `stdio`. They provide deterministic AST-level codebase exploration and secure Dockerized command execution for the Milestone 4 LangGraph Orchestrator.

---

## 2. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | AST Server | `function_signature` | Extracts the exact signature line of a Python function from a source file using Tree-sitter. | `file_path: str`, `function_name: str` | `str` (e.g. `def calculate_tax(amount: float) -> float:`) | Returns `"Error: File '...' does not exist."`, `"Error: Failed to parse file: ..."`, or `"Error: Function '...' not found in '...'"` | `mcp_ast_server/mcp_ast_server/server.py:8`, `tools.py:7` |
| 2 | AST Server | `class_methods` | Extracts all method signature strings belonging to a specified class in a source file. | `file_path: str`, `class_name: str` | `list[str]` (e.g. `["def process_payment(...):", "def refund_payment(...):"]`) | Returns `["Error: File '...' does not exist."]`, `["Error: Failed to parse file: ..."]`, or `["Error: Class '...' not found in '...'"]` | `mcp_ast_server/mcp_ast_server/server.py:14`, `tools.py:38` |
| 3 | AST Server | `extract_block` | Reads a specific block of source code based on 1-indexed start and end line numbers. | `file_path: str`, `start_line: int`, `end_line: int` | `str` (exact source code between start and end lines inclusive) | Returns `"Error: File '...' does not exist."` or `"Error: Invalid line range {start}-{end} for file of length {len}."` | `mcp_ast_server/mcp_ast_server/server.py:21`, `tools.py:76` |
| 4 | AST Server | `parse_file` | Internal parser helper loading Tree-sitter Python grammar and parsing binary file contents. | `file_path: str` | `tuple[tree_sitter.Tree, bytes]` | Raises Python `IOError` or `Exception` on file read/parse failure. | `mcp_ast_server/mcp_ast_server/parser.py:9` |
| 5 | Sandbox Server | `command_runner` | Runs an arbitrary shell command inside the ephemeral Docker container via `/bin/bash -c` in `/workspace`. | `command: str` | `str` (stdout string if exit code 0) | Returns `"Error (Exit Code {exit_code}):\n{stderr_stdout}"` on non-zero exit; raises `RuntimeError` if Docker daemon is unavailable. | `mcp_sandbox_server/mcp_sandbox_server/server.py:7`, `sandbox.py:36` |
| 6 | Sandbox Server | `patch_file` | Creates or overwrites a file inside the container by base64-encoding content and executing `echo <b64> \| base64 -d > <file_path>`. | `file_path: str`, `patch_content: str` | `str` (empty string on success, or error trace on failure) | Returns `"Error (Exit Code {exit_code}):\n{stderr}"` if base64 decoding/writing fails. | `mcp_sandbox_server/mcp_sandbox_server/server.py:13`, `sandbox.py:47` |
| 7 | Sandbox Server | `reset_environment` | Stops and destroys the active Docker container, causing a fresh container to be provisioned on next command. | None (empty args) | `str` (`"Sandbox reset successfully. A new container will be created on the next command."`) | Catches exceptions during container stop gracefully and returns success message. | `mcp_sandbox_server/mcp_sandbox_server/server.py:20`, `sandbox.py:54` |
| 8 | Sandbox Server | `get_or_create_container` | Internal lifecycle manager maintaining singleton container instance (`python:3.12-slim` with `sleep infinity`). | None | `docker.models.containers.Container` | Raises `RuntimeError("Docker daemon is not running or accessible.")` if Docker client is None. | `mcp_sandbox_server/mcp_sandbox_server/sandbox.py:13` |

---

## 3. Edge Cases & Observed Behaviors

| # | Feature | Input / Condition | Observed / Code-Specified Behavior |
|---|---------|-------------------|-------------------------------------|
| 1 | `function_signature` | Non-existent file path | Returns `"Error: File '{file_path}' does not exist."` (string, exit code 0 in MCP). |
| 2 | `function_signature` | Non-existent function name | Returns `"Error: Function '{function_name}' not found in '{file_path}'."` |
| 3 | `function_signature` | Multi-line signature or nested function | AST traversal searches depth-first recursively and splits on `":\n"` + `":"`. Returns first matching function node text up to body colon. |
| 4 | `class_methods` | Class without methods / empty class body | Returns empty list `[]`. |
| 5 | `class_methods` | Non-existent class name | Returns single-element list `["Error: Class '{class_name}' not found in '{file_path}'."]`. |
| 6 | `extract_block` | `start_line < 1` or `end_line > total_lines` or `start_line > end_line` | Returns `"Error: Invalid line range {start_line}-{end_line} for file of length {len(lines)}."`. |
| 7 | `extract_block` | Single line extract (`start_line == end_line`) | Returns that single line (1-indexed inclusive, preserves original indentation and newline). |
| 8 | `command_runner` | Command exits with non-zero status (e.g. `ls /nonexistent`) | Returns formatted error string: `"Error (Exit Code 2):\nls: cannot access '/nonexistent': No such file or directory\n"`. |
| 9 | `command_runner` | Docker daemon down / not installed | `get_or_create_container()` raises `RuntimeError("Docker daemon is not running or accessible.")`. |
| 10 | `patch_file` | Content with complex quotes, newlines, special characters | Handled cleanly without shell injection issues due to `base64.b64encode` in Python piped into `base64 -d > file_path`. |
| 11 | `reset_environment` | Called when no container is running | Safe no-op; returns `"Sandbox reset successfully. A new container will be created on the next command."`. |
| 12 | `reset_environment` | Called when active container is running | Stops container with 1s timeout, sets global `current_container = None`, returns confirmation string. |

---

## 4. Deep Dive: `arc-ast-server` (MCP AST Server)

### 4.1 Server Identity & Entry Point
- **Server Name**: `arc-ast-server`
- **File Location**: `/home/rhyme/repo/arc/mcp_ast_server/mcp_ast_server/server.py`
- **Module Structure**:
  - `mcp_ast_server/__init__.py`: Package root
  - `mcp_ast_server/server.py`: FastMCP instance and tool registrations
  - `mcp_ast_server/tools.py`: Core tool functions and AST search
  - `mcp_ast_server/parser.py`: Tree-sitter initialization and file parsing
- **Server Entry Point**:
  ```python
  from fastmcp import FastMCP
  from .tools import get_function_signature, get_class_methods, extract_code_block

  mcp = FastMCP("arc-ast-server")
  ...
  if __name__ == "__main__":
      mcp.run()
  ```

### 4.2 Exposed Tools & Schema Signatures

#### 1. `function_signature`
- **MCP Tool Name**: `function_signature`
- **Description**: `"Extracts the exact string of a function signature from a file. Use this to understand a function's parameters and return types without reading the whole body."`
- **Parameters**:
  - `file_path` (`string`, required): File system path to the target Python file.
  - `function_name` (`string`, required): Name of the function to extract.
- **Return Type**: `string`
- **AST Implementation Detail**: Uses `tree-sitter-python` grammar to find `function_definition` nodes where `node.child_by_field_name('name') == function_name`.

#### 2. `class_methods`
- **MCP Tool Name**: `class_methods`
- **Description**: `"Returns a list of method signatures belonging to the specified class. Use this to understand the interface of a class."`
- **Parameters**:
  - `file_path` (`string`, required): Path to the target Python file.
  - `class_name` (`string`, required): Target class name.
- **Return Type**: `array of strings` (`list[str]`)
- **AST Implementation Detail**: Finds `class_definition` matching `class_name`, accesses `body` field node, iterates over direct child nodes of type `function_definition`, and returns formatted signatures.

#### 3. `extract_block`
- **MCP Tool Name**: `extract_block`
- **Description**: `"Reads a specific block of code based on 1-indexed line numbers. Use this if you know the exact lines from a compiler error trace."`
- **Parameters**:
  - `file_path` (`string`, required): Path to source file.
  - `start_line` (`integer`, required): 1-indexed starting line number.
  - `end_line` (`integer`, required): 1-indexed ending line number.
- **Return Type**: `string`
- **Implementation Detail**: 1-indexed line slice `lines[start_line-1:end_line]`.

---

## 5. Deep Dive: `arc-sandbox-server` (MCP Sandbox Server)

### 5.1 Server Identity & Entry Point
- **Server Name**: `arc-sandbox-server`
- **File Location**: `/home/rhyme/repo/arc/mcp_sandbox_server/mcp_sandbox_server/server.py`
- **Module Structure**:
  - `mcp_sandbox_server/__init__.py`: Package root
  - `mcp_sandbox_server/server.py`: FastMCP instance and tool registrations
  - `mcp_sandbox_server/tools.py`: Tool wrappers delegating to `sandbox.py`
  - `mcp_sandbox_server/sandbox.py`: Docker SDK integration, container lifecycle, command execution
- **Server Entry Point**:
  ```python
  from fastmcp import FastMCP
  from .tools import execute_command, apply_patch, reset_sandbox

  mcp = FastMCP("arc-sandbox-server")
  ...
  if __name__ == "__main__":
      mcp.run()
  ```

### 5.2 Exposed Tools & Schema Signatures

#### 1. `command_runner`
- **MCP Tool Name**: `command_runner`
- **Description**: `"Runs a shell command inside the ephemeral Docker container. Returns stdout. If the command fails, returns stderr and the exit code."`
- **Parameters**:
  - `command` (`string`, required): Shell command string.
- **Return Type**: `string`
- **Execution Mechanism**: Container executes `['/bin/bash', '-c', command]` with `workdir="/workspace"`.

#### 2. `patch_file`
- **MCP Tool Name**: `patch_file`
- **Description**: `"Overwrites or creates a file at file_path inside the container with patch_content. Use this to apply your proposed code changes."`
- **Parameters**:
  - `file_path` (`string`, required): Path inside `/workspace`.
  - `patch_content` (`string`, required): New content for the file.
- **Return Type**: `string`
- **Implementation Detail**: `echo <base64_encoded_content> | base64 -d > <file_path>` inside container.

#### 3. `reset_environment`
- **MCP Tool Name**: `reset_environment`
- **Description**: `"Destroys the current container and provisions a fresh one. Use this if you have completely broken the repository state and need a clean slate."`
- **Parameters**: None
- **Return Type**: `string`
- **Implementation Detail**: `current_container.stop(timeout=1)` followed by container reference invalidation.

---

## 6. MCP Execution & Spawning Mechanisms

The FastMCP framework supports standard stdio communication:

1. **Direct CLI / Subprocess Invocation**:
   ```bash
   # Running AST Server via Python
   python -m mcp_ast_server.server
   # or
   python /path/to/arc/mcp_ast_server/mcp_ast_server/server.py

   # Running Sandbox Server via Python
   python -m mcp_sandbox_server.server
   # or
   python /path/to/arc/mcp_sandbox_server/mcp_sandbox_server/server.py
   ```
   Or using the FastMCP CLI:
   ```bash
   fastmcp run /path/to/server.py
   ```

2. **Integration into LangGraph Orchestrator (Milestone 4)**:
   In LangGraph / LangChain Python, MCP servers over `stdio` are connected via `langchain-mcp-adapters` or standard `mcp` stdio client parameters:
   ```python
   # Example configuration for MCP client session
   server_params = StdioServerParameters(
       command="python",
       args=["-m", "mcp_ast_server.server"],
       env=None
   )
   ```
   Or by converting the FastMCP server tools directly for in-memory orchestration during tests / demo mode.

---

## 7. Analysis of `dummy_code.py` & Deliberate Bug

### 7.1 Source Code Inspection
Located at `/home/rhyme/repo/arc/mcp_ast_server/tests/dummy_code.py`:
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

### 7.2 The Deliberate Bug
- **Bug Location**: `PaymentGateway.refund_payment` (lines 6–7)
- **Defect**: The method `refund_payment` is an unresolved stub that unconditionally returns `False`:
  ```python
  def refund_payment(self, transaction_id: str) -> bool:
      return False
  ```
  Any caller or test expecting a valid refund transaction (e.g. `gateway.refund_payment("txn_123") == True`) will fail.

### 7.3 Expected Agent Resolution Flow
In Milestone 4, the LangGraph ReAct agent is prompted to solve this issue:
1. **AST Discovery & Reading**:
   - Agent uses `class_methods(".../dummy_code.py", "PaymentGateway")` to discover `refund_payment`.
   - Agent uses `extract_block(".../dummy_code.py", 1, 12)` or `function_signature` to inspect the implementation.
2. **Reasoning & Patch Synthesis**:
   - Agent identifies that `refund_payment` must return `True` for valid transactions (or proper refund status).
3. **Execution Sandbox**:
   - Agent calls `patch_file("dummy_code.py", <fixed_code>)` inside `/workspace`.
   - Agent runs test command via `command_runner("pytest ...")` or `python -c "from dummy_code import PaymentGateway; assert PaymentGateway().refund_payment('tx123') is True"`.
4. **HITL Breakpoint**:
   - Upon test verification, the LangGraph state machine hits the `interrupt()` node to wait for user approval before finishing.

---

## 8. Existing Test Suites & Mocking Environments

### 8.1 AST Server Tests (`mcp_ast_server/tests/test_tools.py`)
- Tests `test_get_function_signature_exists`: Asserts `'def calculate_tax(amount: float) -> float:'`.
- Tests `test_get_function_signature_not_exists`: Asserts error string starts with `'Error:'`.
- Tests `test_get_class_methods_exists`: Asserts `PaymentGateway` returns 2 methods.
- Tests `test_get_class_methods_not_exists`: Asserts error string.
- Tests `test_extract_code_block`: Asserts line 1 extracts `class PaymentGateway:`.
- Tests `test_extract_code_block_invalid`: Asserts out-of-range line request returns `'Error:'`.

### 8.2 Sandbox Server Tests (`mcp_sandbox_server/tests/test_sandbox.py`)
- Tests `test_execute_command`: Asserts `echo "hello world"` returns `'hello world'`.
- Tests `test_execute_command_failure`: Asserts non-existent directory command returns exit code error string.
- Tests `test_apply_patch`: Asserts creating and reading back `test_file.py`.
- Tests `test_reset`: Asserts sandbox container reset.

### 8.3 RAG Layer Tests (`rag_layer/tests/test_rag.py`)
- Tests repository skeleton generation and hybrid search for `PaymentGateway` and `calculate_tax` in `dummy_code.py`.

### 8.4 Recommendations for `test_orchestrator.py` (Milestone 4)
- When running in environments where Docker daemon may not be active or during automated CI test suites (Integrity mode: demo), the orchestrator test suite should support both live MCP server connections over stdio and direct/mock MCP tool bindings.
- The test harness should assert:
  1. Successful connection to both `arc-ast-server` and `arc-sandbox-server`.
  2. Loading of all 6 MCP tools (`function_signature`, `class_methods`, `extract_block`, `command_runner`, `patch_file`, `reset_environment`).
  3. Execution of the ReAct state machine resolving `dummy_code.py`.
  4. Proper state interruption at the HITL `interrupt()` step.

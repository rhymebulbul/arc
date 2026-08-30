# Repository & Environment Survey Report (ARC Milestone 4)

**Document Version**: 1.0.0  
**Author**: Environment & Repo Explorer (`survey_repo`)  
**Workspace**: `/home/rhyme/repo/arc`  
**Target Component**: `/home/rhyme/repo/arc/orchestrator`  
**Scope Document**: `/home/rhyme/repo/arc/ORIGINAL_REQUEST.md`  
**Date**: 2026-08-30  

---

## 1. Executive Summary

This report delivers a thorough forensic survey of the repository layout, Python runtime environment, installed packages, environment configurations, and existing codebases across `/home/rhyme/repo/arc` to prepare for the implementation of **Milestone 4: LangGraph Orchestrator**.

### Key Highlights
1. **Repository State**: Prior milestones (M1 MCP AST Server, M2 MCP Sandbox Server, and M3 Prompt Caching/RAG Layer) are fully present and tested. The `orchestrator` directory does not yet exist and must be created at `/home/rhyme/repo/arc/orchestrator`.
2. **Python Environment**: A dedicated virtual environment exists at `/home/rhyme/repo/arc/venv` running **Python 3.14.4**.
3. **Dependency Status**:
   - **Installed & Ready**: `fastmcp (3.4.7)`, `mcp (1.29.1)`, `pytest (9.1.1)`, `docker (7.2.0)`, `tree-sitter (0.26.0)`, `tree-sitter-python (0.25.0)`, `qdrant-client (1.19.0)`, `fastembed (0.8.0)`, `pydantic (2.13.5)`, `python-dotenv (1.2.3)`, `httpx (0.28.1)`.
   - **Missing for Milestone 4**: `langgraph`, `langchain`, `langchain-core`, and `langchain-openai` are not currently installed in `venv/lib/python3.14/site-packages`.
4. **Environment Variables**: No `.env` files currently exist in the repository root or submodules. The system must support `OPENROUTER_API_KEY` loaded via `os.environ` or `.env`, and provide robust demo/mock execution modes when API keys are absent.
5. **Test Assets**: The target test asset `/home/rhyme/repo/arc/mcp_ast_server/tests/dummy_code.py` is present and ready for acceptance test verification (`test_orchestrator.py`).

---

## 2. Repository Layout & Existing Modules

### 2.1 Workspace Tree Structure

```text
/home/rhyme/repo/arc/
├── .agents/                        # Agent coordination & investigation metadata
│   ├── orchestrator_main/          # Root orchestrator state & plans
│   ├── survey_arch/                # LangGraph architecture survey artifacts
│   ├── survey_mcp/                 # FastMCP server survey artifacts
│   └── survey_repo/                # Repo & environment survey artifacts (this agent)
├── .git/                           # Git metadata
├── .gitignore                      # Standard Python gitignore (ignores venv, .env, __pycache__)
├── LICENSE                         # Project license
├── ORIGINAL_REQUEST.md             # Verbatim user specification for Milestone 4
├── README.md                       # High-level ARC architecture & system documentation
├── design.md                       # Hybrid RAG & AST coding agent design proposal
├── mcp_ast_server/                 # [Milestone 1] Context Engine (Tree-sitter AST FastMCP Server)
│   ├── mcp_ast_server/
│   │   ├── __init__.py
│   │   ├── parser.py               # Tree-sitter AST parser
│   │   ├── server.py               # FastMCP server exposing AST tools
│   │   └── tools.py                # Implementation of AST extraction logic
│   ├── requirements.txt            # mcp, fastmcp, tree-sitter, tree-sitter-python, pytest
│   └── tests/
│       ├── __init__.py
│       ├── dummy_code.py           # Acceptance test benchmark file
│       ├── repo_skeleton.txt       # Extracted AST skeleton of tests
│       └── test_tools.py           # Pytest suite for AST tools
├── mcp_sandbox_server/             # [Milestone 2] Execution Sandbox (Docker SDK FastMCP Server)
│   ├── mcp_sandbox_server/
│   │   ├── __init__.py
│   │   ├── sandbox.py              # Docker container management & execution
│   │   ├── server.py               # FastMCP server exposing sandbox tools
│   │   └── tools.py                # Tool bindings for command runner and patching
│   ├── requirements.txt            # mcp, fastmcp, docker, pytest
│   └── tests/
│       ├── __init__.py
│       └── test_sandbox.py         # Pytest suite for container execution
├── rag_layer/                      # [Milestone 3] Prompt Caching & Hybrid RAG Layer
│   ├── rag_layer/
│   │   ├── __init__.py
│   │   ├── ingest.py               # Skeleton generation & Qdrant embedding
│   │   ├── qdrant_db/              # Local disk Qdrant database storage
│   │   └── search.py               # Hybrid search (Dense + BM25) query interface
│   ├── requirements.txt            # qdrant-client, fastembed, pytest
│   └── tests/
│       ├── __init__.py
│       └── test_rag.py             # Pytest suite for ingestion & search
├── scratch/                        # Specification documents for prior milestones
│   ├── AI_PROJECT_PLAN.md
│   ├── IMPLEMENTATION_PHASES.md
│   ├── MILESTONE_1_SPEC.md
│   ├── MILESTONE_2_SPEC.md
│   └── MILESTONE_3_SPEC.md
└── venv/                           # Python 3.14.4 virtual environment
    ├── bin/
    ├── include/
    ├── lib/
    └── pyvenv.cfg
```

### 2.2 Status of `orchestrator/` Directory
- **Existence**: Not yet created.
- **Requirement**: Must be initialized at `/home/rhyme/repo/arc/orchestrator/` with the following expected structure:
  ```text
  orchestrator/
  ├── orchestrator/
  │   ├── __init__.py
  │   ├── agent.py                  # LangGraph ReAct StateGraph builder & compiler
  │   ├── state.py                  # AgentState, PatchRecord, and message reducers
  │   ├── mcp_client.py             # FastMCP / stdio MCP dynamic client tool loader
  │   ├── llm.py                    # Multi-model routing (OpenRouter / demo fallback)
  │   └── hitl.py                   # HITL breakpoint handler & approval state machine
  ├── tests/
  │   ├── __init__.py
  │   └── test_orchestrator.py      # Acceptance test suite (MCP connection, HITL pause, bug solve)
  ├── requirements.txt              # langgraph, langchain, langchain-openai, mcp, fastmcp, pytest
  └── main.py                       # CLI entry point
  ```

---

## 3. Python Runtime & Virtual Environment Analysis

### 3.1 Virtual Environment Details

| Attribute | Value |
|---|---|
| **Location** | `/home/rhyme/repo/arc/venv` |
| **Python Binary** | `/home/rhyme/repo/arc/venv/bin/python` |
| **Pytest Binary** | `/home/rhyme/repo/arc/venv/bin/pytest` |
| **Python Version** | **3.14.4** |
| **Base Python Home** | `/usr/bin` |
| **Include System Site Packages** | `false` |
| **Config File** | `/home/rhyme/repo/arc/venv/pyvenv.cfg` |

### 3.2 pyvenv.cfg Content
```ini
home = /usr/bin
include-system-site-packages = false
version = 3.14.4
executable = /usr/bin/python3.14
command = /usr/bin/python3 -m venv /home/rhyme/repo/arc/venv
```

---

## 4. Package Inventory & Version Matrix

An inspection of `/home/rhyme/repo/arc/venv/lib/python3.14/site-packages/` revealed 99 installed distributions. The table below lists all key project packages and their exact versions:

| Package Name | Installed Version | Status for M4 | Role in ARC System |
|---|---|---|---|
| `fastmcp` | **3.4.7** | Installed | FastMCP server framework & client tool conversion |
| `mcp` | **1.29.1** | Installed | Official Python Model Context Protocol SDK |
| `pytest` | **9.1.1** | Installed | Test framework for unit & acceptance testing |
| `docker` | **7.2.0** | Installed | Docker SDK for sandbox execution |
| `tree-sitter` | **0.26.0** | Installed | Deterministic AST parsing engine |
| `tree-sitter-python`| **0.25.0** | Installed | Python grammar for Tree-sitter |
| `qdrant-client` | **1.19.0** | Installed | Local disk Vector DB for Hybrid RAG |
| `fastembed` | **0.8.0** | Installed | Local dense/sparse embedding generator |
| `pydantic` | **2.13.5** | Installed | Data validation & state schema modeling |
| `pydantic-settings`| **2.15.0** | Installed | Environment configuration management |
| `python-dotenv` | **1.2.3** | Installed | `.env` file loader for API keys |
| `httpx` | **0.28.1** | Installed | Async HTTP client for OpenRouter API |
| `starlette` | **1.6.0** | Installed | ASGI framework for MCP servers |
| `uvicorn` | **0.52.4** | Installed | ASGI web server |
| `pyyaml` | **6.0.3** | Installed | Configuration parsing |
| `requests` | **2.34.2** | Installed | Synchronous HTTP client |
| `rich` | **15.0.0** | Installed | Formatted terminal output & debugging |
| `anyio` | **4.14.2** | Installed | Asynchronous concurrency primitives |
| **`langgraph`** | **NOT INSTALLED** | **MISSING** | StateGraph orchestrator engine (Must install or mock for tests) |
| **`langchain`** | **NOT INSTALLED** | **MISSING** | Base framework for tool abstractions |
| **`langchain-core`** | **NOT INSTALLED** | **MISSING** | Messages (`AIMessage`, `HumanMessage`, `ToolMessage`) & runnables |
| **`langchain-openai`**| **NOT INSTALLED** | **MISSING** | `ChatOpenAI` provider for OpenRouter multi-model routing |

---

## 5. Configuration Files & Environment Variables

### 5.1 Existing `requirements.txt` Files

#### `mcp_ast_server/requirements.txt`
```text
mcp
fastmcp
tree-sitter
tree-sitter-python
pytest
```

#### `mcp_sandbox_server/requirements.txt`
```text
mcp
fastmcp
docker
pytest
```

#### `rag_layer/requirements.txt`
```text
qdrant-client
fastembed
pytest
```

### 5.2 Environment Variables & API Key Handling
- **Current `.env` files**: None present in `/home/rhyme/repo/arc`.
- **`.gitignore` rule**: `.env` and `.envrc` are strictly ignored by `.gitignore` (lines 151-152).
- **Target Key**: `OPENROUTER_API_KEY`.
- **Handling Strategy**:
  1. The orchestrator must load `.env` if present via `python-dotenv` (`load_dotenv()`).
  2. The LLM routing layer must inspect `os.getenv("OPENROUTER_API_KEY")`.
  3. When `OPENROUTER_API_KEY` is present, initialize `ChatOpenAI(api_key=..., base_url="https://openrouter.ai/api/v1", model=...)`.
  4. When `OPENROUTER_API_KEY` is unset or in test/demo mode, instantiate a deterministic mock/demo LLM runner to ensure tests (`test_orchestrator.py`) can execute in offline environments.

---

## 6. Test Assets & Acceptance Criteria Targets

### 6.1 Benchmark Target: `mcp_ast_server/tests/dummy_code.py`

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

### 6.2 Acceptance Criteria Verification Strategy
As specified in `ORIGINAL_REQUEST.md`:
1. **State Machine Initialization**: `test_orchestrator.py` initializes the LangGraph state machine with memory, patch history, and error tracking.
2. **MCP Connectivity**: Connects to `mcp_ast_server` and `mcp_sandbox_server` dynamically over MCP protocol.
3. **Deliberate Bug Fix**: Agents inspects `dummy_code.py` using AST tools (`function_signature` or `extract_block`), applies a fix via sandbox tools (`patch_file` / `command_runner`), runs tests, and pauses at the HITL `interrupt()` state.
4. **State Machine Pause Verification**: Test asserts `state.status == "awaiting_approval"` or LangGraph interrupt snapshot before human approval.

---

## 7. Recommendations for Implementation & Orchestration

1. **Create `orchestrator/requirements.txt`**:
   ```text
   langgraph
   langchain
   langchain-core
   langchain-openai
   mcp>=1.29.0
   fastmcp>=3.4.0
   pydantic>=2.10.0
   python-dotenv>=1.0.0
   pytest>=8.0.0
   ```
2. **Implement Dual-Mode LLM Routing**:
   Ensure `llm.py` provides an OpenRouter client when `OPENROUTER_API_KEY` is available, and an internal simulation/mock engine when running offline acceptance tests.
3. **Direct MCP In-Process / Stdio Tool Loading**:
   Use FastMCP's tool inspection or in-process client / stdio transport to load tools dynamically without hardcoding tool function bodies.
4. **HITL Governance**:
   Implement the interrupt node using LangGraph's native `interrupt()` or state-gate transition mechanism.

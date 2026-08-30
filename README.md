<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/LangGraph-0.2+-FF6B35?style=for-the-badge&logo=langgraph&logoColor=white"/>
  <img src="https://img.shields.io/badge/Protocol-MCP-7B2FBE?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Docker-DooD-2496ED?style=for-the-badge&logo=docker&logoColor=white"/>
  <img src="https://img.shields.io/github/actions/workflow/status/rhymebulbul/arc/ci.yml?style=for-the-badge&label=CI"/>
</p>

<h1 align="center">ARC — Autonomous Resolution Core</h1>

<p align="center">
  An enterprise-grade, autonomous coding agent that resolves GitHub issues end-to-end.<br/>
  Built on a <strong>LangGraph ReAct state machine</strong>, <strong>MCP microservices</strong>, and <strong>Docker sandboxes</strong>.<br/>
  Governed by a Human-in-the-Loop interrupt before any code lands in production.
</p>

---

## Why ARC?

Most agentic coding tools are demos. They call an LLM, hope for the best, and dump code straight to disk.

ARC is architected differently — for production. It separates **perception** (AST parsing), **reasoning** (LangGraph), and **execution** (ephemeral Docker) into isolated, independently-testable microservices connected by the **Model Context Protocol (MCP)**. No code is executed on the host machine. No patch ships without a human approval gate.

> **Architecture principle:** Every component is a first-class service — composable, swappable, and independently observable.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ARC Orchestrator                             │
│                   (LangGraph ReAct State Machine)                   │
│                                                                     │
│   ┌──────────┐    ┌──────────┐    ┌─────────────┐    ┌─────────┐   │
│   │  Reason  │───▶│  Tools   │───▶│ HITL Gate   │───▶│  Done   │   │
│   │  (LLM)   │◀───│  (MCP)   │    │ (interrupt) │    │         │   │
│   └──────────┘    └──────────┘    └─────────────┘    └─────────┘   │
└────────────────────────┬────────────────────────────────────────────┘
                         │ MCP (stdio)
           ┌─────────────┴──────────────┐
           │                            │
  ┌────────▼────────┐          ┌────────▼────────┐
  │  AST MCP Server │          │ Sandbox MCP Server│
  │  (Tree-sitter)  │          │  (Docker-in-DooD) │
  │                 │          │                   │
  │ function_sig    │          │ command_runner    │
  │ class_methods   │          │ patch_file        │
  │ extract_block   │          │ reset_environment │
  └─────────────────┘          └───────────────────┘
```

### Component Breakdown

| Layer | Technology | Role |
|-------|-----------|------|
| **Orchestrator** | LangGraph 0.2 + OpenRouter | ReAct state machine with HITL interrupt |
| **AST Server** | FastMCP + Tree-sitter | Deterministic code extraction over MCP |
| **Sandbox Server** | FastMCP + Docker SDK | Isolated execution in ephemeral containers |
| **LLM Routing** | langchain-openai + OpenRouter | Multi-model routing (default: free tier) |
| **CI/CD** | GitHub Actions + Docker | Automated test pipeline on every push |

---

## Key Design Decisions

### 1. MCP-first Microservice Architecture
Tools are not functions. They are **networked services** communicating over the [Model Context Protocol](https://modelcontextprotocol.io/) via `stdio` transport. This means:
- The AST and Sandbox servers can be swapped, scaled, or replaced without touching the orchestrator
- Tools are type-safe and schema-validated via JSON-RPC
- Zero coupling between reasoning and execution layers

### 2. Tree-sitter AST over Naive RAG
Sending raw file contents to an LLM is expensive and error-prone. Instead, the AST server exposes **surgical extraction tools**: `function_signature`, `class_methods`, `extract_block`. The LLM requests exactly what it needs — no hallucinated context, no wasted tokens.

### 3. Docker-out-of-Docker (DooD) Sandbox
Patches are tested in ephemeral `python:3.12-slim` containers launched by the host's Docker daemon (mounted via `/var/run/docker.sock`). The host repository is bind-mounted read-write into the container. After tests pass, the container is discarded. The host filesystem is never directly mutated until HITL approval.

### 4. Human-in-the-Loop Governance
The LangGraph `interrupt()` primitive pauses execution after the agent drafts and self-validates a patch. A human must explicitly approve before the state machine continues. This is not an afterthought — it is a hard boundary in the state graph.

### 5. Async-native Tool Execution
All tool invocations are `async`/`await` through the full stack. `AsyncExitStack` manages the `stdio` subprocess lifecycle, preventing anyio cancellation scope violations on teardown.

---

## Quickstart

### Prerequisites
- Python 3.12+
- Docker daemon running
- OpenRouter API key (or use free-tier default)

### Install & Run

```bash
# 1. Clone
git clone https://github.com/rhymebulbul/arc.git
cd arc

# 2. Install all dependencies into a local venv
make install

# 3. Run the agent on an issue (uses free OpenRouter model by default)
make run ISSUE="There is a bug in mcp_ast_server/tests/dummy_code.py where \
PaymentGateway.refund_payment always returns False. Fix it and write a test."

# With your own OpenRouter key (enables frontier models)
OPENROUTER_API_KEY=sk-or-... make run ISSUE="..."
```

### Demo Session

```
🚀 Initializing ARC Orchestrator...
🔌 Connecting to local MCP servers (AST & Sandbox)...
✅ Connected! Loaded tools: function_signature, class_methods, extract_block,
                            command_runner, patch_file, reset_environment
🧠 Initializing OpenRouter LLM...
🕸️  Compiling ReAct State Machine with HITL governance...

==========================================
🎯 Objective: Fix PaymentGateway.refund_payment bug...
==========================================

🤖 AI: I will inspect the PaymentGateway class methods to locate the bug.
🤖 AI called tool: class_methods...
🛠️  Tool 'class_methods' completed.
🤖 AI called tool: extract_block...
🛠️  Tool 'extract_block' completed.
🤖 AI called tool: patch_file...
🛠️  Tool 'patch_file' completed.
🤖 AI called tool: command_runner...
🛠️  Tool 'command_runner' completed.

🤖 AI: Patch applied and verified. Submitting for human review.

⚠️  HITL Governance Breakpoint Reached!
Approve patch execution? (y/N): y
✅ Approved. Resuming execution...
🎉 Task Complete!
```

---

## Running Tests

```bash
# Full test suite (orchestrator + AST + sandbox)
make test

# Individual component tests
source venv/bin/activate
PYTHONPATH=. pytest orchestrator/tests/ -v         # 80+ orchestrator tests
PYTHONPATH=. pytest mcp_ast_server/tests/ -v       # AST parsing tests
PYTHONPATH=. pytest mcp_sandbox_server/tests/ -v   # Sandbox execution tests
```

The test suite is structured in four tiers:
- **Tier 1** — Feature coverage (state machine, HITL, tool discovery)
- **Tier 2** — Boundary/corner cases (large payloads, missing tools, empty patches)
- **Tier 3** — Cross-feature interactions (ReAct loop, self-repair, thread isolation)
- **Tier 4** — Real-world end-to-end scenarios (full bug repair benchmark)
- **Adversarial** — Corruption resilience (bad state types, exploding tools, concurrent threads)

---

## Docker Deployment

```bash
# Build the agent container
make docker-build

# Run — mounts host Docker socket for DooD sandbox creation
make docker-run ISSUE="Fix the null pointer in payment_service.py" \
                OPENROUTER_API_KEY=sk-or-...
```

The `Dockerfile` uses a multi-stage build and mounts `/var/run/docker.sock` so the agent container can spawn sibling sandbox containers on the host daemon — a production-proven pattern used in CI/CD systems like GitHub Actions and Jenkins.

---

## Repository Structure

```
arc/
├── main.py                          # CLI entrypoint
├── Makefile                         # install / test / run / docker-*
├── Dockerfile                       # DooD container for the orchestrator
├── .github/workflows/ci.yml         # GitHub Actions CI pipeline
│
├── orchestrator/                    # LangGraph brain
│   ├── graph.py                     # ReAct state machine + HITL interrupt
│   ├── mcp_client.py                # AsyncExitStack MCP connection manager
│   ├── llm.py                       # OpenRouter multi-model router
│   ├── state.py                     # AgentState TypedDict + reducers
│   ├── agent.py                     # High-level OrchestratorAgent facade
│   └── tests/
│       ├── test_orchestrator.py     # 60 tests across 4 tiers
│       └── test_adversarial.py      # 20 adversarial resilience tests
│
├── mcp_ast_server/                  # Tree-sitter AST parsing microservice
│   ├── mcp_ast_server/
│   │   ├── server.py                # FastMCP server entrypoint
│   │   ├── tools.py                 # function_sig / class_methods / extract_block
│   │   └── parser.py                # Tree-sitter Python grammar integration
│   └── tests/
│       ├── dummy_code.py            # Deliberate bug fixture (return False)
│       └── test_ast_tools.py        # AST extraction tests
│
└── mcp_sandbox_server/              # Docker execution microservice
    ├── mcp_sandbox_server/
    │   ├── server.py                # FastMCP server entrypoint
    │   └── sandbox.py               # Docker SDK: run / patch / reset
    └── tests/
        └── test_sandbox.py          # Sandbox command execution tests
```

---

## CI/CD Pipeline

Every push triggers the GitHub Actions pipeline:

```yaml
1. Install dependencies (pip + venv)
2. Run full test suite (pytest --import-mode=importlib)
3. Docker image build validation
```

Status: ![CI](https://img.shields.io/github/actions/workflow/status/rhymebulbul/arc/ci.yml)

---

## Design Tradeoffs & Future Work

| Decision | Rationale | Future Evolution |
|----------|-----------|-----------------|
| **stdio MCP transport** | Zero infrastructure — runs locally without a server | HTTP/SSE transport for distributed multi-agent deployments |
| **OpenRouter free tier** | Zero-cost local development | Route to Claude 3.5 Sonnet / GPT-4o for production quality |
| **Synchronous HITL via `input()`** | Simple CLI UX | Slack/webhook approval with async polling |
| **Bind-mount sandbox volumes** | Full codebase access for the agent | Per-PR ephemeral workspaces via git worktrees |
| **MemorySaver checkpointer** | In-process state for local dev | Redis/PostgreSQL checkpointer for distributed runs |

---

## License

MIT

# Original User Request

## Initial Request — 2026-08-30T16:04:58+10:00

You are the Project Orchestrator.
Original request file: /home/rhyme/.gemini/antigravity-cli/brain/7cc3b472-4ef3-49eb-8b90-ced0846a08c8/ORIGINAL_REQUEST.md
Project workspace: /home/rhyme/repo/arc
Working directory for orchestrator component: /home/rhyme/repo/arc/orchestrator
Integrity mode: demo

Please read ORIGINAL_REQUEST.md, formulate your execution plan, coordinate the team, and implement the LangGraph orchestrator (Milestone 4 of ARC) with all requirements (R1 ReAct State Machine, R2 MCP Tool Integration, R3 HITL Governance Breakpoint, R4 Multi-Model Routing) and Acceptance Criteria (test_orchestrator.py verifying connection, tool loading, and HITL pause).
Maintain your progress in your working directory and report back with your findings and completion status.

---
Contents of /home/rhyme/.gemini/antigravity-cli/brain/7cc3b472-4ef3-49eb-8b90-ced0846a08c8/ORIGINAL_REQUEST.md:

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: [Full team]

Build the LangGraph orchestrator (Milestone 4 of ARC) that acts as the "Brain" of the autonomous coding agent. It must connect to two existing local FastMCP servers (AST Parser and Docker Sandbox) and implement a ReAct state machine with a Human-in-the-Loop (HITL) interrupt before final execution.

Working directory: /home/rhyme/repo/arc/orchestrator
Integrity mode: demo

## Requirements

### R1. ReAct State Machine
Build a LangGraph workflow that manages the agent state (memory, patch history, errors). The agent should loop between reasoning and acting.

### R2. MCP Tool Integration
The orchestrator must dynamically load and connect to the existing local FastMCP servers (`mcp_ast_server` and `mcp_sandbox_server`). Do not rewrite or hardcode the tool logic; consume them via the MCP protocol.

### R3. HITL Governance Breakpoint
Implement a LangGraph `interrupt()` step. After the agent drafts a patch and runs tests, execution must pause and yield to the user for approval before continuing.

### R4. Multi-Model Routing
Use OpenRouter via `langchain-openai` as the LLM provider for the agent.

## Acceptance Criteria

### Programmatic Verification
- [ ] A test script (`test_orchestrator.py`) is provided that initializes the LangGraph state machine.
- [ ] The test script verifies that the agent successfully connects to the local MCP servers and loads their tools.
- [ ] The test script triggers the agent to solve a deliberate bug in `../mcp_ast_server/tests/dummy_code.py` and asserts that the state machine successfully pauses at the HITL `interrupt()` state.

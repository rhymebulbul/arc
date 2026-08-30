# BRIEFING — 2026-08-30T16:05:35+10:00

## Mission
Build the LangGraph orchestrator (Milestone 4 of ARC) connecting to FastMCP servers (AST Parser and Docker Sandbox) with ReAct state machine, MCP tool integration, HITL governance breakpoint, and multi-model routing via OpenRouter, verified by test_orchestrator.py.

## 🔒 My Identity
- Archetype: orchestrator
- Roles: [orchestrator, user_liaison, human_reporter, successor]
- Working directory: /home/rhyme/repo/arc/.agents/orchestrator_main
- Original parent: parent
- Original parent conversation ID: 7cc3b472-4ef3-49eb-8b90-ced0846a08c8

## 🔒 My Workflow
- **Pattern**: Project Pattern
- **Scope document**: /home/rhyme/repo/arc/PROJECT.md
1. **Decompose**: Survey codebase, create PROJECT.md with feature inventory, milestones, and interface contracts.
2. **Dispatch & Execute**:
   - Survey: Spawn 3 Explorers (codebase survey, MCP servers/tools, testing & dependencies).
   - Milestones: Sub-orchestrators / Worker / Reviewers / Challengers / Auditor.
   - E2E Testing Track: Design & run test_orchestrator.py covering all acceptance criteria.
3. **On failure**: Retry -> Replace -> Skip -> Redistribute -> Redesign
4. **Succession**: Self-succeed when spawn count >= 16 and subagents complete.
- **Work items**:
  1. Survey and Scope Formulation [in-progress]
  2. Orchestrator Implementation (ReAct, MCP client, HITL, OpenRouter LLM) [pending]
  3. Acceptance Testing & Verification (test_orchestrator.py) [pending]
  4. Forensic Audit and Quality Hardening [pending]
- **Current phase**: 0 (Survey)
- **Current focus**: Survey codebase, MCP servers, and environment

## 🔒 Key Constraints
- NEVER write, modify, or create source code files directly.
- NEVER run build/test commands yourself — require workers to do so.
- NEVER investigate or explore the problem at the code level — dispatch Explorers for technical investigation.
- Subagents MUST read ORIGINAL_REQUEST.md.
- Never reuse a subagent after it has delivered its handoff — always spawn fresh.
- Zero tolerance for integrity violations. Auditor verdict is a binary veto.

## Current Parent
- Conversation ID: 7cc3b472-4ef3-49eb-8b90-ced0846a08c8
- Updated: 2026-08-30T16:05:00+10:00

## Key Decisions Made
- Starting survey phase with 3 parallel explorers to investigate repo layout, existing FastMCP servers, and LangGraph/MCP dependencies.

## Team Roster
| Agent | Type | Work Item | Status | Conv ID |
|-------|------|-----------|--------|---------|
| spec_miner_mcp | teamwork_preview_spec_miner | Survey MCP Servers & Dummy Code | running | 71f7814c-3dfa-48fd-9522-7d9fdfd0150b |
| explorer_repo | teamwork_preview_explorer | Survey Repo & Python Env | running | bb52ff77-5f30-4a9c-876b-4821a7a25067 |
| explorer_arch | teamwork_preview_explorer | Survey LangGraph & MCP Arch | running | 75f0c6bb-1034-4594-95ba-ca2e64e2d571 |

## Succession Status
- Succession required: no
- Spawn count: 3 / 16
- Pending subagents: 71f7814c-3dfa-48fd-9522-7d9fdfd0150b, bb52ff77-5f30-4a9c-876b-4821a7a25067, 75f0c6bb-1034-4594-95ba-ca2e64e2d571
- Predecessor: none
- Successor: not yet spawned

## Active Timers
- Heartbeat cron: task-14 (*/10 * * * *)
- Safety timer: none

## Artifact Index
- /home/rhyme/repo/arc/ORIGINAL_REQUEST.md — Verbatim user request
- /home/rhyme/repo/arc/.agents/orchestrator_main/DISPATCH.md — Dispatch log
- /home/rhyme/repo/arc/.agents/orchestrator_main/progress.md — Liveness & progress tracking

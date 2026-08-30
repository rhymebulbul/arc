## 2026-08-30T06:05:33Z

Your identity: MCP Specification Miner
Your working directory: /home/rhyme/repo/arc/.agents/survey_mcp
Scope document: /home/rhyme/repo/arc/ORIGINAL_REQUEST.md

You MUST read /home/rhyme/repo/arc/ORIGINAL_REQUEST.md first.

Objective:
Investigate the existing FastMCP servers in the ARC repository:
1. /home/rhyme/repo/arc/mcp_ast_server
2. /home/rhyme/repo/arc/mcp_sandbox_server
3. Any test files, notably /home/rhyme/repo/arc/mcp_ast_server/tests/dummy_code.py and other tests.

Analyze and document:
- How each FastMCP server is implemented (entry points, server names, tools exposed, argument types, return values).
- How the MCP servers are executed/spawned (e.g. `python server.py`, stdio transport, fastmcp CLI, etc.).
- Inspect `dummy_code.py` and understand what deliberate bug it contains and how the agent is expected to solve it.
- Inspect any existing test suites or mock environments in those servers.

Output:
Write a detailed report to `/home/rhyme/repo/arc/.agents/survey_mcp/survey_report.md` and write a handoff report `/home/rhyme/repo/arc/.agents/survey_mcp/handoff.md`.
Update `progress.md` with timestamps.
When complete, notify the parent orchestrator via `send_message` with your summary and report path.

# DISPATCH LOG

## 2026-08-30T16:09:55+10:00
Implement the LangGraph Orchestrator (Milestone 4 of ARC):
Scope & Write Ownership:
- /home/rhyme/repo/arc/orchestrator/__init__.py
- /home/rhyme/repo/arc/orchestrator/requirements.txt
- /home/rhyme/repo/arc/orchestrator/pyproject.toml
- /home/rhyme/repo/arc/orchestrator/state.py
- /home/rhyme/repo/arc/orchestrator/mcp_client.py
- /home/rhyme/repo/arc/orchestrator/llm.py
- /home/rhyme/repo/arc/orchestrator/graph.py
- /home/rhyme/repo/arc/orchestrator/agent.py

Objectives:
1. Virtual environment: In `/home/rhyme/repo/arc/venv`, install necessary packages (`langgraph`, `langchain`, `langchain-core`, `langchain-openai`, `pytest-asyncio`, etc.) and ensure `requirements.txt` is updated.
2. R1 ReAct State Machine (`state.py`, `graph.py`): Implement `AgentState` schema tracking `messages`, `patch_history`, `error_history`, `memory`, `iteration_count`, `hitl_approved`. Implement ReAct cycle with reasoning node, dynamic tool calling, and state updates.
3. R2 MCP Tool Integration (`mcp_client.py`): Dynamic connection to FastMCP servers (`mcp_ast_server` and `mcp_sandbox_server`) using standard MCP stdio protocol (`mcp.client.stdio` / `mcp.client.session`). Dynamically discover all tools via `list_tools()` and convert them to LangChain `StructuredTool` instances. DO NOT hardcode tool definitions.
4. R3 HITL Governance Breakpoint (`graph.py`): Implement LangGraph `interrupt()` step after drafting a patch and running tests. Pause execution and yield to user for approval before continuing. Use `MemorySaver` checkpointer and support `Command(resume=...)`.
5. R4 Multi-Model Routing (`llm.py`): Connect to OpenRouter via `langchain_openai.ChatOpenAI` (`base_url="https://openrouter.ai/api/v1"`). Provide demo/mock LLM router for deterministic/offline test runs when `OPENROUTER_API_KEY` is not set or in demo mode.
6. Verification: Run build/test verification using `/home/rhyme/repo/arc/venv/bin/python` and `/home/rhyme/repo/arc/venv/bin/pytest`.

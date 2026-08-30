"""
ARC — Autonomous Resolution Core
CLI entrypoint for the LangGraph orchestrator.

Usage:
    python main.py "<issue description>"
    OPENROUTER_API_KEY=sk-or-... make run ISSUE="Fix the null pointer in..."

Environment variables:
    OPENROUTER_API_KEY   OpenRouter key (falls back to MockLLM if absent)
    LANGCHAIN_API_KEY    LangSmith key (tracing disabled if absent)
    LANGCHAIN_PROJECT    LangSmith project name (default: arc)
    LOG_FORMAT           'json' for newline-delimited JSON logs (default: pretty)
    LOG_LEVEL            Minimum log level (default: INFO)
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# ── project root on sys.path ──────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))

# ── observability — configure before any other ARC imports ───────────────────
from orchestrator.logging_setup import configure_logging, configure_langsmith, get_logger

configure_logging(log_level="INFO")
langsmith_enabled = configure_langsmith(project="arc")

log = get_logger("arc.main")

# ── application imports ───────────────────────────────────────────────────────
from orchestrator.mcp_client import MCPClientManager, get_default_mcp_server_params
from orchestrator.llm import create_openrouter_llm
from orchestrator.graph import create_orchestrator_graph, MemorySaver
from orchestrator.state import HumanMessage
from langgraph.types import Command


async def main(issue_description: str) -> None:
    log.info("arc.startup", langsmith_tracing=langsmith_enabled)

    # 1. Connect to local MCP servers ─────────────────────────────────────────
    log.info("mcp.connecting")
    repo_root = str(Path(__file__).resolve().parent)
    server_configs = get_default_mcp_server_params(repo_root=repo_root)
    manager = MCPClientManager(server_configs=server_configs)

    try:
        tools = await manager.connect_all()
        tool_names = [t.name for t in tools]
        log.info("mcp.connected", tools=tool_names, count=len(tool_names))
        print(f"✅ Connected! Loaded tools: {', '.join(tool_names)}")
    except Exception as exc:
        log.error("mcp.connect_failed", error=str(exc))
        print(f"❌ Failed to connect to MCP servers: {exc}")
        return

    # 2. Initialise LLM ────────────────────────────────────────────────────────
    log.info("llm.initializing", model="openrouter/free")
    llm = create_openrouter_llm(model_name="openrouter/free")

    # 3. Compile LangGraph ────────────────────────────────────────────────────
    log.info("graph.compiling")
    checkpointer = MemorySaver()
    app = create_orchestrator_graph(llm=llm, tools=tools, checkpointer=checkpointer)

    print("\n==========================================")
    print(f"🎯 Objective: {issue_description}")
    print("==========================================\n")

    config = {"configurable": {"thread_id": "cli_session_1"}}
    state_input = {"messages": [HumanMessage(content=issue_description)]}

    # 4. Stream graph execution ───────────────────────────────────────────────
    iteration = 0
    try:
        if hasattr(app, "native_compiled") and app.native_compiled:
            async for event in app.native_compiled.astream(
                state_input, config=config, stream_mode="values"
            ):
                messages = event.get("messages", [])
                if not messages:
                    continue
                msg = messages[-1]
                if msg.type == "ai":
                    if msg.content:
                        log.debug("agent.thought", content=msg.content[:200])
                        print(f"\n🤖 AI: {msg.content}")
                    if getattr(msg, "tool_calls", None):
                        for call in msg.tool_calls:
                            tool_name = call.get("name")
                            log.info(
                                "agent.tool_call",
                                tool=tool_name,
                                iteration=iteration,
                                args=list(call.get("args", {}).keys()),
                            )
                            print(f"\n🤖 AI called tool: {tool_name}...")
                elif msg.type == "tool":
                    log.info("agent.tool_result", tool=msg.name)
                    print(f"🛠️  Tool '{msg.name}' completed.")
                    iteration += 1
        else:
            result = await app.ainvoke(state_input, config=config)
            for msg in result.get("messages", []):
                if msg.type == "ai" and msg.content:
                    print(f"\n🤖 AI: {msg.content}")

        # 5. HITL approval gate ───────────────────────────────────────────────
        state = app.get_state(config)
        if state.next:
            log.info("hitl.awaiting_approval")
            print("\n⚠️  HITL Governance Breakpoint Reached! ⚠️")
            print("The agent is requesting human approval to proceed.")
            user_input = input("Approve patch execution? (y/N): ")
            if user_input.lower().strip() == "y":
                log.info("hitl.approved")
                print("✅ Approved. Resuming execution...")
                await app.ainvoke(Command(resume=True), config=config)
                log.info("arc.complete", status="approved")
                print("🎉 Task Complete!")
            else:
                log.warning("hitl.rejected")
                print("❌ Patch rejected by Human-in-the-Loop.")
        else:
            log.info("arc.complete", status="completed", iterations=iteration)
            print("\n🎉 Task Complete!")

    except Exception as exc:
        log.exception("arc.runtime_error", error=str(exc))
        print(f"\n❌ Error during execution: {exc}")
        import traceback
        traceback.print_exc()
    finally:
        await manager.close()
        log.info("arc.shutdown")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py \"<issue description>\"")
        print("       make run ISSUE=\"<issue description>\"")
        sys.exit(1)

    asyncio.run(main(sys.argv[1]))

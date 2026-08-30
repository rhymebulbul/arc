import sys
import asyncio
from pathlib import Path

# Add project root to path so we can import orchestrator
sys.path.append(str(Path(__file__).resolve().parent))

from orchestrator.mcp_client import MCPClientManager, get_default_mcp_server_params
from orchestrator.llm import create_openrouter_llm
from orchestrator.graph import create_orchestrator_graph, MemorySaver
from orchestrator.state import HumanMessage
from langgraph.types import Command

async def main(issue_description: str):
    print("🚀 Initializing ARC Orchestrator (Milestone 5)...")
    
    # 1. Connect to local MCP Servers (AST + Sandbox)
    print("🔌 Connecting to local MCP servers (AST & Sandbox)...")
    repo_root = str(Path(__file__).resolve().parent)
    server_configs = get_default_mcp_server_params(repo_root=repo_root)
    manager = MCPClientManager(server_configs=server_configs)
    
    try:
        tools = await manager.connect_all()
        tool_names = [t.name for t in tools]
        print(f"✅ Connected! Loaded tools: {', '.join(tool_names)}")
    except Exception as e:
        print(f"❌ Failed to connect to MCP servers: {e}")
        return

    # 2. Setup LLM
    print("🧠 Initializing OpenRouter LLM...")
    llm = create_openrouter_llm(model_name="openrouter/free")

    # 3. Compile LangGraph
    print("🕸️ Compiling ReAct State Machine with HITL governance...")
    checkpointer = MemorySaver()
    app = create_orchestrator_graph(llm=llm, tools=tools, checkpointer=checkpointer)

    print("\n==========================================")
    print(f"🎯 Objective: {issue_description}")
    print("==========================================\n")

    # 4. Invoke graph
    config = {"configurable": {"thread_id": "cli_session_1"}}
    state_input = {"messages": [HumanMessage(content=issue_description)]}

    try:
        # Run graph until completion or HITL
        event = await app.ainvoke(state_input, config=config)
        messages = event.get("messages", [])
        if messages:
            for msg in messages:
                if msg.type == "ai":
                    if msg.content:
                        print(f"\n🤖 AI: {msg.content}")
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for call in msg.tool_calls:
                            print(f"\n🤖 AI called tool: {call.get('name')}...")
                elif msg.type == "tool":
                    print(f"🛠️  Tool '{msg.name}' completed.")
                    
        # Check if we hit the interrupt
        state = app.get_state(config)
        if state.next:
            print("\n⚠️  HITL Governance Breakpoint Reached! ⚠️")
            print("The agent is requesting human approval to proceed.")
            user_input = input("Approve patch execution? (y/N): ")
            if user_input.lower().strip() == 'y':
                print("✅ Approved. Resuming execution...")
                await app.ainvoke(Command(resume=True), config=config)
                print("🎉 Task Complete!")
            else:
                print("❌ Patch rejected by Human-in-the-Loop.")
        else:
            print("\n🎉 Task Complete!")
    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await manager.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py \"<issue_description>\"")
        sys.exit(1)
        
    issue = sys.argv[1]
    asyncio.run(main(issue))

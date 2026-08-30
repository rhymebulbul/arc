"""High-level OrchestratorAgent API and runner for Autonomous Repository Contributor."""

from __future__ import annotations
import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .state import AgentState, create_initial_state
from .mcp_client import MCPClientManager, get_default_mcp_server_params
from .llm import MockLLM, OpenRouterModelRouter, create_openrouter_llm, get_model_router
from .graph import (
    Command,
    MemorySaver,
    OrchestratorCompiledGraph,
    create_orchestrator_graph,
)

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """Autonomous Repository Contributor Orchestrator Agent."""

    def __init__(
        self,
        llm: Optional[Any] = None,
        mcp_manager: Optional[MCPClientManager] = None,
        checkpointer: Optional[Any] = None,
        max_iterations: int = 10,
        mode: str = "auto",
        demo_mode: bool = False,
        repo_root: Optional[Union[str, Path]] = None,
    ) -> None:
        self.mode = "demo" if demo_mode else mode
        self.demo_mode = demo_mode
        self.max_iterations = max_iterations
        self.repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parent.parent
        self.mcp_manager = mcp_manager or MCPClientManager()
        self.checkpointer = checkpointer or MemorySaver()
        if llm is not None:
            self.llm = llm
        elif demo_mode or self.mode in ("demo", "mock"):
            self.llm = MockLLM()
        else:
            self.llm = get_model_router(mode=self.mode)
        self.app: Optional[OrchestratorCompiledGraph] = None
        self.graph: Optional[OrchestratorCompiledGraph] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Discovers MCP tools, connects servers, and compiles the LangGraph workflow."""
        if self._initialized:
            return

        if not self.mcp_manager.server_configs and not self.mcp_manager.direct_servers:
            params = get_default_mcp_server_params(str(self.repo_root))
            self.mcp_manager.server_configs = params

        await self.mcp_manager.connect_all()
        tools = self.mcp_manager.to_langchain_tools()

        self.app = create_orchestrator_graph(
            llm=self.llm,
            tools=tools,
            checkpointer=self.checkpointer,
            max_iterations=self.max_iterations,
        )
        self.graph = self.app
        self._initialized = True

    def initialize_sync(self) -> None:
        """Synchronous initialization helper."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    pool.submit(asyncio.run, self.initialize()).result()
            else:
                loop.run_until_complete(self.initialize())
        except RuntimeError:
            asyncio.run(self.initialize())

    def create_graph(self, tools: Optional[List[Any]] = None) -> OrchestratorCompiledGraph:
        """Creates and returns compiled orchestrator graph."""
        active_tools = tools if tools is not None else self.mcp_manager.to_langchain_tools()
        self.app = create_orchestrator_graph(
            llm=self.llm,
            tools=active_tools,
            checkpointer=self.checkpointer,
            max_iterations=self.max_iterations,
        )
        self.graph = self.app
        return self.app

    def run(
        self,
        prompt: str,
        thread_id: str = "default",
        memory: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Executes the agent workflow synchronously from a human prompt."""
        if not self._initialized or self.app is None:
            self.initialize_sync()

        initial_state = create_initial_state(
            prompt=prompt,
            memory=memory,
            max_iterations=self.max_iterations,
        )
        config = {"configurable": {"thread_id": thread_id}}
        return self.app.invoke(initial_state, config=config)

    async def arun(
        self,
        prompt: str,
        thread_id: str = "default",
        memory: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Executes the agent workflow asynchronously from a human prompt."""
        if not self._initialized or self.app is None:
            await self.initialize()

        initial_state = create_initial_state(
            prompt=prompt,
            memory=memory,
            max_iterations=self.max_iterations,
        )
        config = {"configurable": {"thread_id": thread_id}}
        return await self.app.ainvoke(initial_state, config=config)

    def resume(
        self,
        thread_id: str = "default",
        approved: bool = True,
        feedback: str = "",
    ) -> Dict[str, Any]:
        """Resumes the agent workflow after hitting a Human-in-the-loop (HITL) interrupt."""
        if not self._initialized or not self.app:
            self.initialize_sync()

        resume_payload = {"approved": approved, "feedback": feedback}
        cmd = Command(resume=resume_payload)
        config = {"configurable": {"thread_id": thread_id}}
        return self.app.invoke(cmd, config=config)

    async def aresume(
        self,
        thread_id: str = "default",
        approved: bool = True,
        feedback: str = "",
    ) -> Dict[str, Any]:
        """Asynchronously resumes the agent workflow after hitting an HITL interrupt."""
        if not self._initialized or not self.app:
            await self.initialize()

        resume_payload = {"approved": approved, "feedback": feedback}
        cmd = Command(resume=resume_payload)
        config = {"configurable": {"thread_id": thread_id}}
        return await self.app.ainvoke(cmd, config=config)

    def get_state(self, thread_id: str = "default") -> Any:
        """Returns the current state snapshot and any pending interrupts."""
        if not self.app:
            self.initialize_sync()
        config = {"configurable": {"thread_id": thread_id}}
        return self.app.get_state(config)


def run_orchestrator(
    prompt: str,
    repo_root: Optional[Union[str, Path]] = None,
    demo_mode: bool = True,
    thread_id: str = "default",
) -> Dict[str, Any]:
    """Convenience functional entry point for executing orchestrator tasks."""
    agent = OrchestratorAgent(demo_mode=demo_mode, repo_root=repo_root)
    return agent.run(prompt=prompt, thread_id=thread_id)

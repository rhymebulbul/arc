"""Multi-model routing and OpenRouter integration for ARC Orchestrator.

Provides OpenRouter ChatOpenAI routing and a deterministic Mock/Demo LLM router
for offline CI runs, deterministic benchmarks, and acceptance testing.
"""

from __future__ import annotations
import json
import logging
import os
import uuid
from typing import Any, Callable, Dict, List, Optional, Sequence, Union
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Import or fallback for messages and chat models
try:
    from langchain_core.messages import (
        BaseMessage,
        HumanMessage,
        AIMessage,
        ToolMessage,
        SystemMessage,
    )
except ImportError:
    from .state import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage

try:
    from langchain_openai import ChatOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    ChatOpenAI = Any


class MockBoundLLM:
    """Runnable wrapper for MockLLM with bound tools."""

    def __init__(self, router: MockLLM, tools: Sequence[Any]) -> None:
        self.router = router
        self.tools = list(tools)
        self.tool_map = {
            getattr(t, "name", str(t)): t for t in self.tools
        }

    def invoke(self, messages: Sequence[Union[BaseMessage, Dict[str, Any]]], **kwargs: Any) -> AIMessage:
        return self.router.generate_response(messages, self.tools)

    async def ainvoke(self, messages: Sequence[Union[BaseMessage, Dict[str, Any]]], **kwargs: Any) -> AIMessage:
        return self.invoke(messages, **kwargs)

    def __call__(self, messages: Sequence[Union[BaseMessage, Dict[str, Any]]], **kwargs: Any) -> AIMessage:
        return self.invoke(messages, **kwargs)


class MockLLM:
    """Deterministic ReAct reasoning simulator for offline test suites and benchmarks."""

    def __init__(
        self,
        responses: Optional[Sequence[Union[AIMessage, Dict[str, Any], str]]] = None,
        handler: Optional[Callable[[Sequence[Any], Sequence[Any]], AIMessage]] = None,
    ) -> None:
        self.responses: List[AIMessage] = []
        if responses:
            for item in responses:
                if isinstance(item, AIMessage):
                    self.responses.append(item)
                elif isinstance(item, dict):
                    self.responses.append(
                        AIMessage(
                            content=item.get("content", ""),
                            tool_calls=item.get("tool_calls", []),
                            additional_kwargs=item.get("additional_kwargs", {}),
                        )
                    )
                elif isinstance(item, str):
                    self.responses.append(AIMessage(content=item))

        self.handler = handler
        self._script_index = 0
        self.call_history: List[List[Any]] = []
        self.model_name = "mock-react-llm"
        self.model = "mock-react-llm"
        self.base_url = "mock://openrouter.ai/api/v1"
        self.openai_api_base = "mock://openrouter.ai/api/v1"

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> MockBoundLLM:
        """Binds tool definitions to the mock router matching LangChain model interface."""
        return MockBoundLLM(self, tools)

    def invoke(self, messages: Sequence[Union[BaseMessage, Dict[str, Any]]], **kwargs: Any) -> AIMessage:
        return self.generate_response(messages, [])

    async def ainvoke(self, messages: Sequence[Union[BaseMessage, Dict[str, Any]]], **kwargs: Any) -> AIMessage:
        return self.invoke(messages, **kwargs)

    def generate_response(
        self,
        messages: Sequence[Union[BaseMessage, Dict[str, Any]]],
        tools: Sequence[Any],
    ) -> AIMessage:
        """Generates a deterministic ReAct step based on message history and target scenario."""
        self.call_history.append(list(messages))

        # 1. Check custom handler
        if self.handler:
            return self.handler(messages, tools)

        # 2. Check scripted responses queue
        if self.responses and self._script_index < len(self.responses):
            resp = self.responses[self._script_index]
            self._script_index += 1
            return resp

        # 3. Dynamic ReAct solver logic for dummy_code bug repair scenario
        norm_messages = list(messages)
        target_file = self._extract_target_file(norm_messages)

        tool_messages = [m for m in norm_messages if getattr(m, "type", "") == "tool" or isinstance(m, ToolMessage) or (isinstance(m, dict) and m.get("role") == "tool")]
        ai_messages = [m for m in norm_messages if getattr(m, "type", "") == "ai" or isinstance(m, AIMessage) or (isinstance(m, dict) and m.get("role") == "assistant")]

        # Stage 0: Initial prompt -> Discover class methods
        if not tool_messages:
            return AIMessage(
                content="I will inspect the PaymentGateway class methods in the target file to locate the bug.",
                tool_calls=[
                    {
                        "name": "class_methods",
                        "args": {
                            "file_path": target_file,
                            "class_name": "PaymentGateway",
                        },
                        "id": f"call_{uuid.uuid4().hex[:8]}",
                    }
                ],
            )

        last_tool = tool_messages[-1]
        last_tool_content = getattr(last_tool, "content", "") if not isinstance(last_tool, dict) else last_tool.get("content", "")

        # Stage 1: Discovered methods -> Extract code block to read implementation
        if "refund_payment" in last_tool_content and "def " in last_tool_content and "extract_block" not in str([getattr(m, 'tool_calls', []) for m in ai_messages]):
            return AIMessage(
                content="The class contains `refund_payment`. I will extract the source block to inspect its implementation.",
                tool_calls=[
                    {
                        "name": "extract_block",
                        "args": {
                            "file_path": target_file,
                            "start_line": 1,
                            "end_line": 12,
                        },
                        "id": f"call_{uuid.uuid4().hex[:8]}",
                    }
                ],
            )

        has_extracted = any("extract_block" in str(getattr(m, 'tool_calls', [])) for m in ai_messages)
        has_patched = any("patch_file" in str(getattr(m, 'tool_calls', [])) for m in ai_messages)

        # Stage 2: Apply patch
        if has_extracted and not has_patched:
            fixed_code = (
                "class PaymentGateway:\n"
                "    def process_payment(self, amount: float, currency: str) -> bool:\n"
                "        \"\"\"Processes the payment.\"\"\"\n"
                "        return True\n"
                "        \n"
                "    def refund_payment(self, transaction_id: str) -> bool:\n"
                "        return True\n\n"
                "def calculate_tax(amount: float) -> float:\n"
                "    tax = amount * 0.1\n"
                "    return tax\n"
            )
            return AIMessage(
                content="I found that `refund_payment` returns `False` unconditionally. I will apply a patch to fix it to return `True`.",
                tool_calls=[
                    {
                        "name": "patch_file",
                        "args": {
                            "file_path": target_file,
                            "patch_content": fixed_code,
                        },
                        "id": f"call_{uuid.uuid4().hex[:8]}",
                    }
                ],
            )

        # Stage 3: Test verification
        has_run_test = any("command_runner" in str(getattr(m, 'tool_calls', [])) for m in ai_messages)
        if has_patched and not has_run_test:
            test_cmd = (
                f"python3 -c \"import sys; sys.path.insert(0, '.'); from pathlib import Path; "
                f"import importlib.util; spec = importlib.util.spec_from_file_location('dummy_mod', '{target_file}'); "
                f"mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); "
                f"gateway = mod.PaymentGateway(); assert gateway.refund_payment('tx_test') is True; print('TEST_VERIFIED_SUCCESS')\""
            )
            return AIMessage(
                content="Patch applied. Now running test verification in the environment to validate the fix.",
                tool_calls=[
                    {
                        "name": "command_runner",
                        "args": {
                            "command": test_cmd,
                        },
                        "id": f"call_{uuid.uuid4().hex[:8]}",
                    }
                ],
            )

        # Stage 4: Final synthesis
        return AIMessage(
            content=(
                "Bug Repair Complete:\n"
                f"1. Identified defective stub in `{target_file}` (`PaymentGateway.refund_payment` returning False).\n"
                "2. Applied patch updating `refund_payment` to return True upon valid transaction.\n"
                "3. Verified behavior via automated test runner (exit code 0, TEST_VERIFIED_SUCCESS).\n"
                "Patch is verified and submitted for Human-in-the-Loop governance approval."
            ),
            tool_calls=[],
        )

    def _extract_target_file(self, messages: Sequence[Any]) -> str:
        for msg in messages:
            content = getattr(msg, "content", "") if not isinstance(msg, dict) else msg.get("content", "")
            if "dummy_code.py" in content:
                for token in content.split():
                    if token.endswith("dummy_code.py"):
                        return token.strip("\"'`:,()")
        return "dummy_code.py"


# Aliases for compatibility
MockLLMRouter = MockLLM


class OpenRouterModelRouter:
    """Configures and provides OpenRouter ChatOpenAI instances with model routing."""

    def __init__(
        self,
        default_model: str = "anthropic/claude-3.5-sonnet",
        api_key: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
        temperature: float = 0.0,
    ) -> None:
        self.default_model = default_model
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.base_url = base_url
        self.openai_api_base = base_url
        self.temperature = temperature
        self.model_name = default_model
        self.model = default_model

    def get_chat_model(self, model_name: Optional[str] = None, **kwargs: Any) -> Any:
        """Returns a configured ChatOpenAI model pointing to OpenRouter."""
        chosen_model = model_name or self.default_model
        key = self.api_key or os.environ.get("OPENROUTER_API_KEY", "")

        if not key or not OPENAI_AVAILABLE:
            logger.warning(
                "OPENROUTER_API_KEY not set or langchain-openai not available; falling back to MockLLM."
            )
            mock = MockLLM()
            mock.model_name = chosen_model
            mock.model = chosen_model
            mock.base_url = self.base_url
            mock.openai_api_base = self.base_url
            return mock

        merged_kwargs = {
            "model": chosen_model,
            "api_key": key,
            "base_url": self.base_url,
            "temperature": self.temperature,
        }
        merged_kwargs.update(kwargs)
        chat = ChatOpenAI(**merged_kwargs)
        return chat


def create_openrouter_llm(
    model_name: str = "anthropic/claude-3.5-sonnet",
    temperature: float = 0.0,
    api_key: Optional[str] = None,
    **kwargs: Any,
) -> Any:
    """Factory function creating ChatOpenAI targeting OpenRouter or fallback MockLLM."""
    key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
    router = OpenRouterModelRouter(default_model=model_name, api_key=key, temperature=temperature)
    return router.get_chat_model(model_name=model_name, **kwargs)


def get_model_router(
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    mode: str = "auto",
) -> Union[OpenRouterModelRouter, MockLLM]:
    """Factory creating appropriate model router (OpenRouter or Mock)."""
    key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
    if mode in ("mock", "demo") or (mode == "auto" and not key):
        return MockLLM()
    return OpenRouterModelRouter(default_model=model_name or "anthropic/claude-3.5-sonnet", api_key=key)

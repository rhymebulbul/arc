"""Dynamic Model Context Protocol (MCP) client manager and LangChain tool converter.

Supports connecting to FastMCP servers over standard stdio transport as well as
direct FastMCP server instances, discovering tools dynamically, and converting
them to LangChain StructuredTool instances without hardcoding schemas.
"""

from __future__ import annotations
import asyncio
import inspect
import json
import os
import sys
from pathlib import Path
import contextlib
from typing import Any, Callable, Coroutine, Dict, List, Optional, Sequence, Tuple, Type, Union
from pydantic import BaseModel, Field, create_model
import structlog

logger = structlog.get_logger(__name__)

# Attempt to import standard MCP SDK
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.types import Tool as MCPTool, CallToolResult
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    ClientSession = Any
    StdioServerParameters = Any
    MCPTool = Any
    CallToolResult = Any

# Attempt to import LangChain core tools
try:
    from langchain_core.tools import BaseTool, StructuredTool
    LANGCHAIN_CORE_AVAILABLE = True
except ImportError:
    LANGCHAIN_CORE_AVAILABLE = False

    class BaseTool:
        """Base tool interface matching LangChain Core."""
        name: str = ""
        description: str = ""
        args_schema: Optional[Type[BaseModel]] = None

        def __init__(
            self,
            name: str = "",
            description: str = "",
            args_schema: Optional[Type[BaseModel]] = None,
            **kwargs: Any,
        ):
            self.name = name or self.name
            self.description = description or self.description
            self.args_schema = args_schema or self.args_schema

        def invoke(self, input: Union[Dict[str, Any], BaseModel, str], **kwargs: Any) -> Any:
            raise NotImplementedError

        async def ainvoke(self, input: Union[Dict[str, Any], BaseModel, str], **kwargs: Any) -> Any:
            return self.invoke(input, **kwargs)

        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            if args and isinstance(args[0], (dict, BaseModel, str)):
                return self.invoke(args[0])
            return self.invoke(kwargs)

    class StructuredTool(BaseTool):
        """StructuredTool interface matching LangChain Core StructuredTool."""
        def __init__(
            self,
            name: str,
            description: str,
            args_schema: Type[BaseModel],
            func: Optional[Callable[..., Any]] = None,
            coroutine: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None,
            **kwargs: Any,
        ):
            super().__init__(name=name, description=description, args_schema=args_schema, **kwargs)
            self.func = func
            self.coroutine = coroutine

        def invoke(self, input: Union[Dict[str, Any], BaseModel, str], **kwargs: Any) -> Any:
            parsed_args = self._normalize_input(input)
            if self.func is not None:
                return self.func(**parsed_args)
            if self.coroutine is not None:
                # Run async coroutine in sync context
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as pool:
                            return pool.submit(asyncio.run, self.coroutine(**parsed_args)).result()
                    else:
                        return loop.run_until_complete(self.coroutine(**parsed_args))
                except RuntimeError:
                    return asyncio.run(self.coroutine(**parsed_args))
            raise NotImplementedError(f"No execution function provided for tool {self.name}")

        async def ainvoke(self, input: Union[Dict[str, Any], BaseModel, str], **kwargs: Any) -> Any:
            parsed_args = self._normalize_input(input)
            if self.coroutine is not None:
                return await self.coroutine(**parsed_args)
            if self.func is not None:
                return self.func(**parsed_args)
            raise NotImplementedError(f"No execution function provided for tool {self.name}")

        def _normalize_input(self, input: Union[Dict[str, Any], BaseModel, str]) -> Dict[str, Any]:
            if isinstance(input, BaseModel):
                return input.model_dump()
            if isinstance(input, dict):
                return input
            if isinstance(input, str):
                try:
                    data = json.loads(input)
                    if isinstance(data, dict):
                        return data
                except Exception:
                    pass
                if self.args_schema:
                    first_field = next(iter(self.args_schema.model_fields.keys()), "input")
                    return {first_field: input}
                return {"input": input}
            return {}

        @classmethod
        def from_function(
            cls,
            func: Optional[Callable[..., Any]] = None,
            coroutine: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None,
            name: Optional[str] = None,
            description: Optional[str] = None,
            args_schema: Optional[Type[BaseModel]] = None,
            **kwargs: Any,
        ) -> StructuredTool:
            tool_name = name or (func.__name__ if func else (coroutine.__name__ if coroutine else "unnamed_tool"))
            tool_desc = description or (func.__doc__ if func else (coroutine.__doc__ if coroutine else ""))
            return cls(
                name=tool_name,
                description=tool_desc or "",
                args_schema=args_schema or BaseModel,
                func=func,
                coroutine=coroutine,
                **kwargs,
            )


class ServerParams:
    """Config container for standard MCP stdio server parameters."""

    def __init__(
        self,
        command: str,
        args: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> None:
        self.command = command
        self.args = args
        self.cwd = cwd
        self.env = env or os.environ.copy()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "args": self.args,
            "cwd": self.cwd,
            "env": self.env,
        }


def get_default_mcp_server_params(repo_root: Optional[str] = None) -> Dict[str, ServerParams]:
    """Generates standard StdioServerParameters configs for AST and Sandbox MCP servers."""
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parent.parent
    python_bin = sys.executable or "python3"

    ast_dir = root / "mcp_ast_server"
    sandbox_dir = root / "mcp_sandbox_server"

    env = os.environ.copy()
    current_pythonpath = env.get("PYTHONPATH", "")
    new_pythonpath = f"{str(root)}:{str(ast_dir)}:{str(sandbox_dir)}"
    if current_pythonpath:
        new_pythonpath = f"{new_pythonpath}:{current_pythonpath}"
    env["PYTHONPATH"] = new_pythonpath

    return {
        "ast_server": ServerParams(
            command=python_bin,
            args=["-m", "mcp_ast_server.server"],
            cwd=str(ast_dir),
            env=env,
        ),
        "sandbox_server": ServerParams(
            command=python_bin,
            args=["-m", "mcp_sandbox_server.server"],
            cwd=str(sandbox_dir),
            env=env,
        ),
    }


def schema_to_pydantic_model(tool_name: str, input_schema: Dict[str, Any]) -> Type[BaseModel]:
    """Dynamically construct a Pydantic BaseModel from an MCP inputSchema dictionary."""
    properties = input_schema.get("properties", {})
    required_fields = set(input_schema.get("required", []))

    type_mapping: Dict[str, Type[Any]] = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    fields: Dict[str, Tuple[Type[Any], Any]] = {}
    for field_name, field_def in properties.items():
        json_type = field_def.get("type", "string")
        py_type = type_mapping.get(json_type, Any)
        description = field_def.get("description", "")
        default_val = field_def.get("default", ... if field_name in required_fields else None)

        if field_name not in required_fields and default_val is ...:
            py_type = Optional[py_type]
            default_val = None

        fields[field_name] = (
            py_type,
            Field(default=default_val, description=description),
        )

    clean_name = "".join(part.capitalize() for part in tool_name.replace("-", "_").split("_")) + "Input"
    return create_model(clean_name, **fields)


class MCPClientManager:
    """Manages connections to multiple MCP servers and exposes them as LangChain tools."""

    def __init__(
        self,
        server_configs: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.server_configs: Dict[str, Any] = server_configs or {}
        self.direct_servers: Dict[str, Any] = {}
        self.sessions: Dict[str, Any] = {}
        self.exit_stack = contextlib.AsyncExitStack()
        self._discovered_tools: Dict[str, Dict[str, Any]] = {}
        self._tool_to_server: Dict[str, str] = {}

    def register_stdio_server(
        self,
        name: str,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
    ) -> None:
        """Registers an MCP server config to be launched via stdio subprocess."""
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        self.server_configs[name] = ServerParams(
            command=command,
            args=args,
            cwd=cwd,
            env=merged_env,
        )

    def register_direct_fastmcp(self, name: str, fastmcp_instance: Any) -> None:
        """Registers a direct FastMCP server instance (in-process / test mode)."""
        self.direct_servers[name] = fastmcp_instance

    async def connect_all(self) -> List[StructuredTool]:
        """Connects to all registered servers, discovers tools, and returns LangChain StructuredTool list."""
        # 1. Connect stdio servers if MCP SDK is available
        if MCP_AVAILABLE:
            for name, config_item in list(self.server_configs.items()):
                cmd = getattr(config_item, "command", None) or config_item.get("command")
                args = getattr(config_item, "args", None) or config_item.get("args")
                env = getattr(config_item, "env", None) or config_item.get("env")
                cwd = getattr(config_item, "cwd", None) or config_item.get("cwd")

                try:
                    if hasattr(StdioServerParameters, "__init__"):
                        try:
                            server_params = StdioServerParameters(command=cmd, args=args, env=env, cwd=cwd)
                        except TypeError:
                            server_params = StdioServerParameters(command=cmd, args=args, env=env)
                    else:
                        server_params = None

                    if server_params is not None:
                        stdio_transport = stdio_client(server_params)
                        read, write = await self.exit_stack.enter_async_context(stdio_transport)
                        session = ClientSession(read, write)
                        await self.exit_stack.enter_async_context(session)
                        await session.initialize()
                        self.sessions[name] = {
                            "session": session,
                        }
                except Exception as e:
                    logger.debug(f"Stdio connection to MCP server '{name}' skipped or failed: {e}")

        # 2. If direct servers were not provided, attempt to import local fastmcp server modules
        if not self.direct_servers and not self.sessions:
            try:
                from mcp_ast_server.server import mcp as ast_mcp
                self.register_direct_fastmcp("ast_server", ast_mcp)
            except Exception as e:
                logger.debug(f"Could not load local direct ast_server: {e}")

            try:
                from mcp_sandbox_server.server import mcp as sandbox_mcp
                self.register_direct_fastmcp("sandbox_server", sandbox_mcp)
            except Exception as e:
                logger.debug(f"Could not load local direct sandbox_server: {e}")

        # 3. Discover all tools dynamically
        await self.discover_tools()
        return self.to_langchain_tools()

    async def discover_tools(self) -> List[Dict[str, Any]]:
        """Queries all active servers dynamically via list_tools() without hardcoding."""
        tools_list: List[Dict[str, Any]] = []

        # 1. Discover from direct FastMCP servers
        for server_name, server in self.direct_servers.items():
            try:
                # Inspect FastMCP tools
                if hasattr(server, "_tool_manager") and hasattr(server._tool_manager, "_tools"):
                    for t_name, tool_obj in server._tool_manager._tools.items():
                        desc = getattr(tool_obj, "description", "") or (tool_obj.fn.__doc__ if hasattr(tool_obj, "fn") else "")
                        schema = self._extract_fastmcp_tool_schema(tool_obj)
                        tool_info = {
                            "name": t_name,
                            "description": desc or "",
                            "inputSchema": schema,
                            "server_name": server_name,
                            "type": "direct",
                            "handler": tool_obj,
                        }
                        self._discovered_tools[t_name] = tool_info
                        self._tool_to_server[t_name] = server_name
                        tools_list.append(tool_info)
                elif hasattr(server, "get_tools"):
                    fastmcp_tools = await server.get_tools() if inspect.iscoroutinefunction(server.get_tools) else server.get_tools()
                    for tool_obj in fastmcp_tools:
                        t_name = getattr(tool_obj, "name", str(tool_obj))
                        desc = getattr(tool_obj, "description", "")
                        schema = getattr(tool_obj, "parameters", getattr(tool_obj, "inputSchema", {}))
                        tool_info = {
                            "name": t_name,
                            "description": desc,
                            "inputSchema": schema,
                            "server_name": server_name,
                            "type": "direct",
                            "handler": tool_obj,
                        }
                        self._discovered_tools[t_name] = tool_info
                        self._tool_to_server[t_name] = server_name
                        tools_list.append(tool_info)
            except Exception as e:
                logger.error(f"Failed to discover tools from direct server '{server_name}': {e}")

        # 2. Discover from connected stdio MCP sessions
        for server_name, session_entry in self.sessions.items():
            session: ClientSession = session_entry["session"]
            try:
                result = await session.list_tools()
                for tool in result.tools:
                    tool_info = {
                        "name": tool.name,
                        "description": tool.description or "",
                        "inputSchema": tool.inputSchema if isinstance(tool.inputSchema, dict) else {},
                        "server_name": server_name,
                        "type": "stdio",
                        "handler": tool,
                    }
                    self._discovered_tools[tool.name] = tool_info
                    self._tool_to_server[tool.name] = server_name
                    tools_list.append(tool_info)
            except Exception as e:
                logger.error(f"Failed to list tools from stdio session '{server_name}': {e}")

        return tools_list

    def _extract_fastmcp_tool_schema(self, tool_obj: Any) -> Dict[str, Any]:
        """Extracts JSON schema properties and required list from a FastMCP tool object."""
        if hasattr(tool_obj, "parameters") and isinstance(tool_obj.parameters, dict):
            return tool_obj.parameters
        if hasattr(tool_obj, "inputSchema") and isinstance(tool_obj.inputSchema, dict):
            return tool_obj.inputSchema

        fn = getattr(tool_obj, "fn", tool_obj)
        if callable(fn):
            sig = inspect.signature(fn)
            props: Dict[str, Any] = {}
            req: List[str] = []
            type_names = {str: "string", int: "integer", float: "number", bool: "boolean", list: "array", dict: "object"}

            for param_name, param in sig.parameters.items():
                if param_name in ("self", "cls"):
                    continue
                p_type = param.annotation
                json_type = type_names.get(p_type, "string") if p_type != inspect.Parameter.empty else "string"
                props[param_name] = {"type": json_type, "description": f"Parameter {param_name}"}
                if param.default == inspect.Parameter.empty:
                    req.append(param_name)

            return {"type": "object", "properties": props, "required": req}
        return {"type": "object", "properties": {}, "required": []}

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Executes a tool on the responsible server and returns string response."""
        if tool_name not in self._discovered_tools:
            return f"Error: Tool '{tool_name}' not found on any connected MCP server."

        tool_meta = self._discovered_tools[tool_name]
        server_name = tool_meta["server_name"]
        tool_type = tool_meta["type"]

        try:
            if tool_type == "direct":
                handler = tool_meta["handler"]
                fn = getattr(handler, "fn", handler)
                if callable(fn):
                    if inspect.iscoroutinefunction(fn):
                        res = await fn(**arguments)
                    else:
                        res = fn(**arguments)
                    if isinstance(res, list):
                        return json.dumps(res) if any(isinstance(x, (dict, list)) for x in res) else "\n".join(str(x) for x in res)
                    return str(res) if res is not None else ""
                elif hasattr(handler, "run"):
                    res = await handler.run(arguments) if inspect.iscoroutinefunction(handler.run) else handler.run(arguments)
                    return str(res)

            elif tool_type == "stdio":
                session_entry = self.sessions.get(server_name)
                if not session_entry:
                    return f"Error: Session for server '{server_name}' is not active."
                session: ClientSession = session_entry["session"]
                result: CallToolResult = await session.call_tool(tool_name, arguments)
                text_parts = []
                for item in result.content:
                    if hasattr(item, "text"):
                        text_parts.append(item.text)
                    else:
                        text_parts.append(str(item))
                output = "\n".join(text_parts)
                if getattr(result, "isError", False):
                    return f"Error:\n{output}"
                return output

        except Exception as e:
            return f"Error executing tool '{tool_name}': {str(e)}"

        return f"Error: Unable to invoke tool '{tool_name}'"

    def call_tool_sync(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Synchronous wrapper for call_tool."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, self.call_tool(tool_name, arguments)).result()
            return loop.run_until_complete(self.call_tool(tool_name, arguments))
        except RuntimeError:
            return asyncio.run(self.call_tool(tool_name, arguments))

    def to_langchain_tools(self) -> List[StructuredTool]:
        """Converts all discovered MCP tools into LangChain StructuredTool instances."""
        langchain_tools: List[StructuredTool] = []

        for tool_name, tool_meta in self._discovered_tools.items():
            description = tool_meta.get("description", "")
            schema = tool_meta.get("inputSchema", {})
            args_model = schema_to_pydantic_model(tool_name, schema)

            def make_sync_fn(name: str):
                def _sync_fn(**kwargs: Any) -> str:
                    return self.call_tool_sync(name, kwargs)
                return _sync_fn

            def make_async_fn(name: str):
                async def _async_fn(**kwargs: Any) -> str:
                    return await self.call_tool(name, kwargs)
                return _async_fn

            structured_tool = StructuredTool(
                name=tool_name,
                description=description or f"MCP tool {tool_name}",
                args_schema=args_model,
                func=make_sync_fn(tool_name),
                coroutine=make_async_fn(tool_name),
            )
            langchain_tools.append(structured_tool)

        return langchain_tools

    async def close(self) -> None:
        """Closes all active sessions and transports cleanly."""
        try:
            await self.exit_stack.aclose()
        except Exception as e:
            logger.debug(f"Exception during close: {e}")
        self.sessions.clear()

    async def __aenter__(self) -> MCPClientManager:
        await self.connect_all()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

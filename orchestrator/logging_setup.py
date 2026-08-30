"""
ARC Observability Stack
=======================
Configures structured logging (structlog) and LangSmith tracing for the
entire orchestrator. Import ``configure_logging()`` once at process startup.

Design:
- Development: human-readable coloured console output (structlog ConsoleRenderer)
- Production (LOG_FORMAT=json): newline-delimited JSON for log aggregators
  (Datadog, Splunk, CloudWatch)
- LangSmith: opt-in via LANGCHAIN_API_KEY env var; zero-cost when absent.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

import structlog


def configure_logging(log_level: str = "INFO", json_logs: bool | None = None) -> None:
    """
    Configure structlog + stdlib logging for the ARC process.

    Args:
        log_level: Minimum log level (DEBUG / INFO / WARNING / ERROR).
        json_logs: If True, emit newline-delimited JSON. Defaults to
                   True when LOG_FORMAT=json env var is set, else False.
    """
    _level = getattr(logging, log_level.upper(), logging.INFO)

    if json_logs is None:
        json_logs = os.getenv("LOG_FORMAT", "").lower() == "json"

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_logs:
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty())

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(_level)

    # Suppress noisy third-party loggers
    for noisy in ("httpx", "httpcore", "urllib3", "anyio", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # FastMCP logs to 'mcp' — keep at WARNING so INFO banners are silent
    logging.getLogger("mcp").setLevel(logging.WARNING)
    logging.getLogger("fastmcp").setLevel(logging.WARNING)


def configure_langsmith(project: str = "arc") -> bool:
    """
    Enable LangSmith tracing if LANGCHAIN_API_KEY is present in the environment.

    LangSmith automatically wraps every LangChain / LangGraph invocation with
    distributed traces — no code changes required beyond setting env vars.

    Returns:
        True if tracing was enabled, False if the API key is absent.
    """
    api_key = os.getenv("LANGCHAIN_API_KEY")
    if not api_key:
        return False

    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_PROJECT", project)
    os.environ.setdefault("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")

    return True


def get_logger(name: str = "arc") -> Any:
    """Return a bound structlog logger for the given module name."""
    return structlog.get_logger(name)

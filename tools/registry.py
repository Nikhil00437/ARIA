"""Tool registry for the ARIA agent harness.

A thin, typed layer over the existing tool implementations in
``tools.file_ops`` and ``tools.tool_manager``. Each tool is described by:

* ``name``        — unique identifier (matches the OpenAI tool-call name)
* ``schema``      — OpenAI function-calling spec (the dict sent to the LLM)
* ``risk_level``  — "read" | "workspace_write" | "destructive"
* ``execute``     — callable(args, ctx) -> dict result

The registry does NOT re-implement tools — it imports the existing functions
from ``tools.tool_manager`` so there is one execution path. The agent
harness (``agent/runner.py``) and the permission policy
(``tools/permissions.py``) consume this registry; the legacy single-turn
chat path continues to use ``execute_tool`` / ``ToolManager`` unchanged.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .tool_manager import (
    TOOL_DEFINITIONS,
    TOOL_FUNCTIONS,
    TOOL_RISK_LEVELS,
    REQUIRES_CONFIRMATION,
    get_risk_level,
)
from .safety import PathSafety


# ── Types ────────────────────────────────────────────────────────────────────

@dataclass
class ToolContext:
    """Per-task execution context passed to every tool call.

    Carries the workspace root the tool is scoped to, the originating task /
    session ids, and an opaque slot for the runner to attach anything else
    (e.g. a cancel token the tool may consult for long operations).
    """

    task_id: str
    session_id: str
    workspace_root: str = field(default_factory=PathSafety.get_workspace_root)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Tool:
    """A single registered tool."""

    name: str
    schema: Dict[str, Any]
    risk_level: str
    requires_confirmation: bool
    execute: Callable[[Dict[str, Any], ToolContext], Dict[str, Any]]

    def __post_init__(self) -> None:
        if self.risk_level not in ("read", "workspace_write", "destructive"):
            raise ValueError(f"Invalid risk_level for {self.name}: {self.risk_level}")


# ── Adapter ──────────────────────────────────────────────────────────────────

def _wrap(func: Callable) -> Callable[[Dict[str, Any], ToolContext], Dict[str, Any]]:
    """Adapt a legacy tool function ``func(**args) -> dict`` to the
    ``(args, ctx) -> dict`` signature. The context is currently advisory —
    existing tools don't take it — but it lets future tools scope themselves
    to ``ctx.workspace_root`` without changing the registry protocol."""

    def wrapped(args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
        # Ensure file tools resolve against the task workspace by default.
        # We do NOT override an explicit `path` argument the model provided.
        try:
            return func(**args)
        except TypeError:
            # Argument mismatch (e.g. model sent an unexpected key) — surface
            # a clean error dict instead of crashing the agent loop.
            return {"success": False,
                    "error": f"Invalid arguments for tool call: {args}"}

    return wrapped


# ── Registry ─────────────────────────────────────────────────────────────────

class ToolRegistry:
    """Holds the set of tools available to the agent, indexed by name."""

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register the existing 7 tools from TOOL_DEFINITIONS / TOOL_FUNCTIONS."""
        index = {d["function"]["name"]: d for d in TOOL_DEFINITIONS}
        for name, func in TOOL_FUNCTIONS.items():
            if name not in index:
                continue
            self.register(
                name=name,
                schema=index[name],
                risk_level=get_risk_level(name),
                requires_confirmation=name in REQUIRES_CONFIRMATION,
                execute=_wrap(func),
            )

    def register(
        self,
        name: str,
        schema: Dict[str, Any],
        risk_level: str,
        execute: Callable[[Dict[str, Any], ToolContext], Dict[str, Any]],
        requires_confirmation: Optional[bool] = None,
    ) -> Tool:
        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")
        if requires_confirmation is None:
            requires_confirmation = risk_level in ("workspace_write", "destructive")
        tool = Tool(
            name=name,
            schema=schema,
            risk_level=risk_level,
            requires_confirmation=requires_confirmation,
            execute=execute,
        )
        self._tools[name] = tool
        return tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        return name in self._tools

    def all(self) -> List[Tool]:
        return list(self._tools.values())

    def names(self) -> List[str]:
        return list(self._tools.keys())

    def schemas(self) -> List[Dict[str, Any]]:
        """OpenAI-compatible tool spec list, ready for ``chat_with_tools``."""
        return [t.schema for t in self._tools.values()]

    def execute(self, name: str, args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            return {"success": False, "error": f"Unknown tool: {name}"}
        return tool.execute(args, ctx)

    def set_workspace_root(self, path: str) -> None:
        """Scope all path-based tools to ``path``."""
        PathSafety.set_workspace_root(os.path.abspath(path))


# ── Singleton ────────────────────────────────────────────────────────────────

_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry

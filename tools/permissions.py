"""Unified permission policy for the ARIA agent harness.

This is the single safety boundary the ``AgentRunner`` consults before every
tool call. It WRAPS the existing primitives rather than duplicating them:

* ``extract.is_blocked`` / ``extract.needs_confirmation`` — shell-command
  safety (kept as-is for the existing single-turn chat path).
* ``tools.safety.PathSafety`` — path scoping and blocked dirs/extensions.

A ``Decision`` tells the runner one of three things:

* ``auto``           — safe to run now (read-only tools).
* ``needs_approval`` — may run, but a human must approve first (writes/edits
                       inside the workspace in plan_apply mode; anything
                       destructive or out-of-workspace).
* ``blocked``        — never run (hard block-list match, protected path,
                       blocked extension, or unknown tool).

The policy is mode-aware:

* ``plan_apply`` (default): every mutating tool asks for approval, even inside
  the workspace. This matches the user's chosen default autonomy.
* ``auto_workspace``: writes/edits inside the workspace root run automatically;
  everything else still asks. The upgrade path to more autonomy, no rewrite.
"""

from __future__ import annotations

import os
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .safety import PathSafety
from .registry import Tool, ToolContext

# Imported lazily inside _shell_decision to avoid a circular import
# (extract.py has no dependency on tools/, so this is safe, but we keep the
# import local to make the boundary explicit).


@dataclass
class Decision:
    """The verdict for a proposed tool call."""

    verdict: str  # "auto" | "needs_approval" | "blocked"
    reason: str
    risk_level: str = "unknown"
    tool: str = ""
    args: Dict[str, Any] = field(default_factory=dict)
    # For needs_approval: a human-readable description of the action to show
    # the user in the approval dialog.
    action_summary: str = ""

    @property
    def is_auto(self) -> bool:
        return self.verdict == "auto"

    @property
    def needs_approval(self) -> bool:
        return self.verdict == "needs_approval"

    @property
    def is_blocked(self) -> bool:
        return self.verdict == "blocked"


class PermissionPolicy:
    """Decide whether a proposed tool call may execute."""

    def __init__(
        self,
        mode: str = "plan_apply",
        workspace_root: Optional[str] = None,
    ) -> None:
        if mode not in ("plan_apply", "auto_workspace"):
            raise ValueError(f"Unknown agent mode: {mode}")
        self.mode = mode
        self.workspace_root = os.path.abspath(
            workspace_root or PathSafety.get_workspace_root()
        )
        # Keep PathSafety in sync so the underlying file tools enforce the
        # same root we reason about here.
        PathSafety.set_workspace_root(self.workspace_root)

    # ── Public API ─────────────────────────────────────────────────────────

    def decide(self, tool: Tool, args: Dict[str, Any], ctx: ToolContext) -> Decision:
        """Return the verdict for executing ``tool`` with ``args``."""
        if tool.risk_level == "read":
            return Decision(
                verdict="auto",
                reason=f"read-only tool '{tool.name}'",
                risk_level=tool.risk_level,
                tool=tool.name,
                args=args,
                action_summary=f"Read: {tool.name}",
            )

        # Destructive tools are gated first — even inside the workspace.
        if tool.risk_level == "destructive":
            return self._gate_destructive(tool, args)

        # workspace_write: depends on whether the target path is inside the
        # workspace root and on the active mode.
        return self._gate_write(tool, args)

    # ── Internal rules ─────────────────────────────────────────────────────

    def _gate_destructive(self, tool: Tool, args: Dict[str, Any]) -> Decision:
        path = args.get("path", "")
        # Hard-block protected paths/extensions regardless of confirmation.
        if path:
            safe, msg = PathSafety.is_safe_path(path)
            if not safe:
                return Decision(
                    verdict="blocked", reason=msg,
                    risk_level=tool.risk_level, tool=tool.name, args=args,
                    action_summary=f"BLOCKED delete: {path}",
                )
        # delete_file on an inside-workspace path: needs approval (never auto).
        return Decision(
            verdict="needs_approval",
            reason=(f"'{tool.name}' is destructive and requires explicit "
                    f"approval"),
            risk_level=tool.risk_level, tool=tool.name, args=args,
            action_summary=f"Delete file: {path}",
        )

    def _gate_write(self, tool: Tool, args: Dict[str, Any]) -> Decision:
        path = args.get("path", "")
        inside = self._is_inside_workspace(path) if path else True

        if not inside:
            return Decision(
                verdict="needs_approval",
                reason=(f"'{tool.name}' targets a path outside the workspace "
                        f"root: {path}"),
                risk_level=tool.risk_level, tool=tool.name, args=args,
                action_summary=f"Write OUTSIDE workspace: {path}",
            )

        # Hard-block protected paths/extensions even inside the workspace
        # (e.g. an attempt to write a .bat into the workspace).
        if path:
            safe, msg = PathSafety.is_safe_path(path)
            if not safe:
                return Decision(
                    verdict="blocked", reason=msg,
                    risk_level=tool.risk_level, tool=tool.name, args=args,
                    action_summary=f"BLOCKED write: {path}",
                )

        if self.mode == "auto_workspace":
            return Decision(
                verdict="auto",
                reason=(f"'{tool.name}' inside workspace (auto_workspace "
                        f"mode)"),
                risk_level=tool.risk_level, tool=tool.name, args=args,
                action_summary=f"Write: {path}",
            )
        # plan_apply: writes inside the workspace still ask.
        verb = "Edit" if tool.name == "edit_file" else "Write"
        return Decision(
            verdict="needs_approval",
            reason=(f"'{tool.name}' modifies a file and requires approval "
                    f"(plan_apply mode)"),
            risk_level=tool.risk_level, tool=tool.name, args=args,
            action_summary=f"{verb} file: {path}",
        )

    def _is_inside_workspace(self, path: str) -> bool:
        try:
            abs_path = os.path.abspath(path)
            rel = os.path.relpath(abs_path, self.workspace_root)
            return not rel.startswith("..")
        except ValueError:
            # Different drive on Windows.
            return False

    # ── Shell decisions (for a future run_shell tool) ──────────────────────
    # Kept here so all permission logic lives in one place. Not yet wired into
    # the registry because the current tool set is file-only; the agent's
    # shell actions today still go through chat_engine's confirmation flow.

    def decide_shell(self, command: str) -> Decision:
        """Verdict for a proposed shell command."""
        from extract import is_blocked, needs_confirmation  # local import
        if is_blocked(command):
            return Decision(
                verdict="blocked",
                reason="Command matched the hard block-list",
                risk_level="destructive",
                tool="shell",
                args={"command": command},
                action_summary=f"BLOCKED shell: {command[:80]}",
            )
        if needs_confirmation(command):
            return Decision(
                verdict="needs_approval",
                reason="Command matched a confirmation pattern",
                risk_level="destructive",
                tool="shell",
                args={"command": command},
                action_summary=f"Run shell: {command[:80]}",
            )
        # Non-confirmed, non-blocked shell — still treat as needing approval
        # in plan_apply mode; auto in auto_workspace. Shell is inherently
        # higher-risk than file writes, so plan_apply always asks.
        if self.mode == "auto_workspace":
            return Decision(
                verdict="auto",
                reason="shell command (auto_workspace mode)",
                risk_level="workspace_write",
                tool="shell",
                args={"command": command},
                action_summary=f"Run shell: {command[:80]}",
            )
        return Decision(
            verdict="needs_approval",
            reason="shell command requires approval (plan_apply mode)",
            risk_level="workspace_write",
            tool="shell",
            args={"command": command},
            action_summary=f"Run shell: {command[:80]}",
        )


def summarize_args(args: Dict[str, Any], limit: int = 200) -> str:
    """Compact one-line summary of tool args for the UI / logs."""
    try:
        s = json.dumps(args, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        s = str(args)
    return s if len(s) <= limit else s[: limit - 3] + "..."

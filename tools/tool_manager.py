import os
import psutil
import datetime
from typing import Dict, Any, Callable, Optional, List
from .safety import PathSafety
from .file_ops import (
    read_file,
    write_file,
    edit_file,
    delete_file,
    list_files,
    search_files,
)


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a text file. Use this when you need to see what's in a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The absolute path to the file to read"},
                    "offset": {"type": "integer", "description": "Line number to start reading from (default: 0)", "default": 0},
                    "limit": {"type": "integer", "description": "Maximum lines to read (default: 1000)", "default": 1000},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create a new file or overwrite an existing file with new content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The absolute path for the new file"},
                    "content": {"type": "string", "description": "The content to write to the file"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace a specific section of text in an existing file. Use this for making targeted changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The absolute path to the file to edit"},
                    "oldString": {"type": "string", "description": "The exact text to find and replace (must match exactly)"},
                    "newString": {"type": "string", "description": "The replacement text"},
                },
                "required": ["path", "oldString", "newString"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Permanently delete a file. Use with caution.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The absolute path to the file to delete"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories matching a glob pattern. Use to explore the file system.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern (e.g., '*.py', '**/*.txt')", "default": "*"},
                    "path": {"type": "string", "description": "Directory to search in (defaults to workspace root)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search for text content within files. Returns matching lines with file and line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern to search for in file contents"},
                    "path": {"type": "string", "description": "Directory to search in (defaults to workspace root)"},
                    "include": {"type": "string", "description": "File extensions to include (e.g., 'py,txt,md')"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "Get current system information including CPU, memory, disk, and time.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]


TOOL_FUNCTIONS: Dict[str, Callable] = {}

# Risk levels classify tools so callers (the agent loop, the chat tool path)
# can decide whether a tool may run automatically or needs human approval.
#   "read"            — side-effect-free; safe to auto-run
#   "workspace_write" — mutates files inside the workspace; confirm by default
#   "destructive"     — irreversible / deletions; always confirm
TOOL_RISK_LEVELS: Dict[str, str] = {
    "read_file":        "read",
    "list_files":       "read",
    "search_files":     "read",
    "get_system_info":  "read",
    "write_file":       "workspace_write",
    "edit_file":        "workspace_write",
    "delete_file":      "destructive",
}

# Tools that require explicit confirmation before they execute.
REQUIRES_CONFIRMATION = {"write_file", "edit_file", "delete_file"}


def _register_tools():
    """Populate TOOL_FUNCTIONS. Idempotent — safe to call at import and again
    from ToolManager.__init__. Also called once at the bottom of this module
    so the ToolRegistry can build itself without first constructing a
    ToolManager."""
    TOOL_FUNCTIONS["read_file"] = read_file
    TOOL_FUNCTIONS["write_file"] = write_file
    TOOL_FUNCTIONS["edit_file"] = edit_file
    TOOL_FUNCTIONS["delete_file"] = delete_file
    TOOL_FUNCTIONS["list_files"] = list_files
    TOOL_FUNCTIONS["search_files"] = search_files
    TOOL_FUNCTIONS["get_system_info"] = _get_system_info


def get_risk_level(name: str) -> str:
    """Return the risk level for a tool, defaulting to 'destructive' (safe)."""
    return TOOL_RISK_LEVELS.get(name, "destructive")


def _get_system_info() -> Dict[str, Any]:
    try:
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=None)
        disk = psutil.disk_usage("C:\\")
        now = datetime.datetime.now().astimezone()
        return {
            "success": True,
            "cpu_percent": cpu,
            "memory_percent": mem.percent,
            "memory_used_gb": mem.used / (1024**3),
            "memory_total_gb": mem.total / (1024**3),
            "disk_free_gb": disk.free / (1024**3),
            "disk_total_gb": disk.total / (1024**3),
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "working_directory": os.getcwd(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


class ToolManager:
    def __init__(self):
        _register_tools()
        self._enabled = True
        self._pending_confirmations: Dict[str, Dict] = {}

    def set_enabled(self, enabled: bool):
        self._enabled = enabled

    def is_enabled(self) -> bool:
        return self._enabled

    def get_tool_definitions(self) -> List[Dict]:
        if not self._enabled:
            return []
        return TOOL_DEFINITIONS

    def check_permission(self, name: str, arguments: Dict) -> Dict[str, Any]:
        """Inspect a tool call WITHOUT executing it.

        Returns a decision dict describing whether the tool may run
        automatically, needs human approval, or is blocked. Destructive and
        workspace-write tools return ``needs_approval=True`` here instead of
        executing — this closes the previous gap where ``execute_tool``
        registered a pending confirmation and then ran the tool anyway.
        """
        if not self._enabled:
            return {"decision": "blocked", "reason": "Tool use is disabled",
                    "needs_approval": False}
        if name not in TOOL_FUNCTIONS:
            return {"decision": "blocked", "reason": f"Unknown tool: {name}",
                    "needs_approval": False}

        risk = get_risk_level(name)
        if name in REQUIRES_CONFIRMATION:
            self._pending_confirmations[name] = {
                "func": name, "args": arguments, "status": "pending",
                "risk_level": risk,
            }
            return {
                "decision": "needs_approval",
                "needs_approval": True,
                "risk_level": risk,
                "tool": name,
                "args": arguments,
                "reason": f"{name} is a {risk} operation and requires confirmation",
            }
        return {
            "decision": "auto",
            "needs_approval": False,
            "risk_level": risk,
            "tool": name,
            "args": arguments,
            "reason": "auto-approved (read-only)",
        }

    def execute_tool(self, name: str, arguments: Dict) -> Dict[str, Any]:
        """Execute a tool call.

        Safety gate: tools in :data:`REQUIRES_CONFIRMATION` are NOT executed
        here unless they have a recorded approval. Callers that want the
        legacy "run immediately" behavior should use :meth:`confirm_and_execute`
        or call :meth:`check_permission` first and then :meth:`run_tool`.
        """
        if not self._enabled:
            return {"success": False, "error": "Tool use is disabled"}
        if name not in TOOL_FUNCTIONS:
            return {"success": False, "error": f"Unknown tool: {name}"}

        if name in REQUIRES_CONFIRMATION:
            pending = self._pending_confirmations.get(name)
            approved = (pending and pending.get("status") == "approved"
                        and pending.get("args") == arguments)
            if not approved:
                # Do NOT execute — return the decision so the caller can prompt.
                self._pending_confirmations[name] = {
                    "func": name, "args": arguments, "status": "pending",
                    "risk_level": get_risk_level(name),
                }
                return {
                    "success": False,
                    "needs_approval": True,
                    "decision": "needs_approval",
                    "risk_level": get_risk_level(name),
                    "error": (f"{name} requires confirmation before execution. "
                              f"Call approve(name) or confirm_and_execute()."),
                }

        return self.run_tool(name, arguments)

    def approve(self, name: str, arguments: Optional[Dict] = None) -> bool:
        """Mark a pending confirmation as approved (caller-supplied human OK)."""
        if name not in REQUIRES_CONFIRMATION:
            return True
        pending = self._pending_confirmations.get(name)
        if not pending:
            # No prior check — record the approval so execute_tool accepts it.
            self._pending_confirmations[name] = {
                "func": name, "args": arguments or {}, "status": "approved",
                "risk_level": get_risk_level(name),
            }
            return True
        pending["status"] = "approved"
        return True

    def run_tool(self, name: str, arguments: Dict) -> Dict[str, Any]:
        """Execute the tool function directly, with no confirmation gate.

        Only call this for pre-approved or read-only tools.
        """
        if name not in TOOL_FUNCTIONS:
            return {"success": False, "error": f"Unknown tool: {name}"}
        func = TOOL_FUNCTIONS[name]
        try:
            result = func(**arguments)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    def confirm_and_execute(self, name: str, arguments: Dict) -> Dict[str, Any]:
        """Legacy convenience: auto-approve then execute in one step.

        Preserves the prior behavior of the chat tool path
        (``chat_engine._handle_chat``) where tool calls ran immediately.
        The agent harness does NOT use this — it goes through
        ``check_permission`` → human approval → ``run_tool``.
        """
        if name in REQUIRES_CONFIRMATION:
            self.approve(name, arguments)
        return self.execute_tool(name, arguments)

    def get_pending_confirmation(self, tool_name: str) -> Optional[Dict]:
        return self._pending_confirmations.get(tool_name)

    def clear_confirmation(self, tool_name: str):
        self._pending_confirmations.pop(tool_name, None)

    def set_workspace_root(self, path: str):
        PathSafety.set_workspace_root(path)


_tool_manager: Optional[ToolManager] = None


def get_tool_manager() -> ToolManager:
    global _tool_manager
    if _tool_manager is None:
        _tool_manager = ToolManager()
        _tool_manager.set_workspace_root(os.getcwd())
    return _tool_manager


# Populate TOOL_FUNCTIONS at import (after _get_system_info is defined) so the
# ToolRegistry can build itself without first instantiating a ToolManager.
_register_tools()

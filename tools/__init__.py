from .tool_manager import (
    ToolManager,
    get_tool_manager,
    TOOL_DEFINITIONS,
    TOOL_FUNCTIONS,
    TOOL_RISK_LEVELS,
    REQUIRES_CONFIRMATION,
    get_risk_level,
)
from .file_ops import (
    read_file,
    write_file,
    edit_file,
    delete_file,
    list_files,
    search_files,
)
from .safety import PathSafety
from .registry import Tool, ToolContext, ToolRegistry, get_registry
from .permissions import Decision, PermissionPolicy

AVAILABLE_TOOLS = TOOL_DEFINITIONS


def execute_tool(name: str, arguments: dict):
    """Execute a tool call.

    This is the legacy entry point used by the single-turn chat tool path
    (``chat_engine._handle_chat``). It auto-approves and runs immediately,
    preserving prior behavior. The agent harness does NOT use this — it goes
    through ``ToolManager.check_permission`` → human approval → ``run_tool``
    so destructive tools never execute without explicit consent.
    """
    manager = get_tool_manager()
    return manager.confirm_and_execute(name, arguments)


__all__ = [
    "ToolManager",
    "get_tool_manager",
    "AVAILABLE_TOOLS",
    "execute_tool",
    "TOOL_RISK_LEVELS",
    "REQUIRES_CONFIRMATION",
    "get_risk_level",
    "read_file",
    "write_file",
    "edit_file",
    "delete_file",
    "list_files",
    "search_files",
    "PathSafety",
    # Agent harness registry
    "Tool",
    "ToolContext",
    "ToolRegistry",
    "get_registry",
    # Agent harness permissions
    "Decision",
    "PermissionPolicy",
]

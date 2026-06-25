import os
from typing import Tuple, Optional
from pathlib import Path

BLOCKED_PATHS = [
    r"C:\Windows",
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    r"C:\System32",
    r"C:\boot",
    r"/etc",
    r"/bin",
    r"/sbin",
    r"/usr/bin",
    r"/usr/sbin",
    r"/root",
]

BLOCKED_EXTENSIONS = [
    ".exe",
    ".dll",
    ".sys",
    ".bat",
    ".cmd",
    ".ps1",
    ".sh",
    ".jar",
    ".node",
]


class PathSafety:
    _workspace_root: Optional[str] = None

    @classmethod
    def set_workspace_root(cls, path: str):
        cls._workspace_root = os.path.abspath(path)

    @classmethod
    def get_workspace_root(cls) -> str:
        if cls._workspace_root:
            return cls._workspace_root
        return os.getcwd()

    @classmethod
    def is_safe_path(cls, path: str) -> Tuple[bool, str]:
        if not path:
            return False, "Empty path provided"

        abs_path = os.path.abspath(path)

        for blocked in BLOCKED_PATHS:
            if abs_path.lower().startswith(blocked.lower()):
                return False, f"Path is in protected directory: {blocked}"

        ext = os.path.splitext(path)[1].lower()
        if ext in BLOCKED_EXTENSIONS:
            return False, f"File extension {ext} is not allowed"

        workspace = cls.get_workspace_root()
        try:
            rel = os.path.relpath(abs_path, workspace)
            if rel.startswith(".."):
                return False, f"Path escapes workspace: {rel}"
        except ValueError:
            return False, "Path is on different drive than workspace"

        return True, "OK"

    @classmethod
    def validate_delete(cls, path: str) -> Tuple[bool, str]:
        safe, msg = cls.is_safe_path(path)
        if not safe:
            return False, msg

        if not os.path.exists(path):
            return False, "File does not exist"

        if os.path.isdir(path):
            return False, "Cannot delete directories"

        return True, "OK"

    @classmethod
    def validate_write(cls, path: str) -> Tuple[bool, str]:
        safe, msg = cls.is_safe_path(path)
        if not safe:
            return False, msg
        return True, "OK"

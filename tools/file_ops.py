import os
import glob as _glob
import re
from typing import Dict, Any, List, Optional, Tuple
from .safety import PathSafety


def read_file(path: str, offset: int = 0, limit: int = 1000) -> Dict[str, Any]:
    safe, msg = PathSafety.is_safe_path(path)
    if not safe:
        return {"success": False, "error": msg}

    if not os.path.isfile(path):
        return {"success": False, "error": "Not a file"}

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            if offset > 0:
                lines = f.readlines()
                total_lines = len(lines)
                content = "".join(lines[offset : offset + limit])
            else:
                content = f.read()
                total_lines = content.count("\n") + 1

            if limit and len(content) > limit * 100:
                content = content[: limit * 100] + f"\n... [truncated, showing first {limit * 100} chars]"

        return {
            "success": True,
            "path": path,
            "content": content,
            "total_lines": total_lines,
            "show_offset": offset,
            "show_limit": limit,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def write_file(path: str, content: str) -> Dict[str, Any]:
    safe, msg = PathSafety.validate_write(path)
    if not safe:
        return {"success": False, "error": msg}

    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "success": True,
            "path": path,
            "bytes_written": len(content.encode("utf-8")),
            "lines_written": content.count("\n") + 1,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def edit_file(path: str, oldString: str, newString: str) -> Dict[str, Any]:
    safe, msg = PathSafety.is_safe_path(path)
    if not safe:
        return {"success": False, "error": msg}

    if not os.path.isfile(path):
        return {"success": False, "error": "Not a file"}

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            original = f.read()

        if oldString not in original:
            return {"success": False, "error": "String not found in file"}

        new_content = original.replace(oldString, newString, 1)

        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return {
            "success": True,
            "path": path,
            "changes_made": 1,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_file(path: str) -> Dict[str, Any]:
    safe, msg = PathSafety.validate_delete(path)
    if not safe:
        return {"success": False, "error": msg}

    try:
        os.remove(path)
        return {"success": True, "path": path, "deleted": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_files(pattern: str = "*", path: Optional[str] = None) -> Dict[str, Any]:
    if path:
        safe, msg = PathSafety.is_safe_path(path)
        if not safe:
            return {"success": False, "error": msg}
        search_dir = path
    else:
        search_dir = PathSafety.get_workspace_root()

    try:
        full_pattern = os.path.join(search_dir, pattern)
        matches = _glob.glob(full_pattern, recursive=True)

        files = []
        dirs = []
        for m in matches[:100]:
            if os.path.isfile(m):
                files.append(
                    {
                        "name": os.path.basename(m),
                        "path": m,
                        "size": os.path.getsize(m),
                    }
                )
            elif os.path.isdir(m):
                dirs.append({"name": os.path.basename(m), "path": m})

        return {
            "success": True,
            "pattern": pattern,
            "path": search_dir,
            "files": files,
            "directories": dirs,
            "total": len(files) + len(dirs),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def search_files(pattern: str, path: Optional[str] = None, include: Optional[str] = None) -> Dict[str, Any]:
    search_dir = path or PathSafety.get_workspace_root()

    safe, msg = PathSafety.is_safe_path(search_dir)
    if not safe:
        return {"success": False, "error": msg}

    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return {"success": False, "error": f"Invalid regex: {e}"}

    results = []
    try:
        for root, dirs, files in os.walk(search_dir):
            if include:
                files = [f for f in files if any(f.endswith(ext.strip()) for ext in include.split(","))]
            for fname in files:
                fpath = os.path.join(root, fname)
                safe, _ = PathSafety.is_safe_path(fpath)
                if not safe:
                    continue
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        for lineno, line in enumerate(f, 1):
                            if regex.search(line):
                                results.append(
                                    {
                                        "file": fpath,
                                        "line": lineno,
                                        "match": line.strip()[:200],
                                    }
                                )
                                if len(results) >= 50:
                                    break
                except (UnicodeDecodeError, OSError):
                    continue
                if len(results) >= 50:
                    break
            if len(results) >= 50:
                break
    except Exception as e:
        return {"success": False, "error": str(e)}

    return {
        "success": True,
        "pattern": pattern,
        "path": search_dir,
        "results": results,
        "total": len(results),
    }

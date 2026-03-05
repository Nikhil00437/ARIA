import subprocess, os, re
from typing import Optional
try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False

BLOCKED_PATTERNS = [
    r"rm\s+-rf",
    r"mkfs",
    r":\(\)\{",
    r"shutdown\s+/[srh]",
    r"shutdown\s+-[srh]",
    r"reboot",
    r"format\s+[a-z]:",
    r"del\s+/f\s+/s\s+/q\s+[a-z]:\\",
    r"rd\s+/s\s+/q\s+[a-z]:\\",
    r"rmdir\s+/s\s+/q\s+[a-z]:\\",
    r"reg\s+delete\s+hklm",
    r"powershell.*remove-item.*recurse.*c:\\",
]

KNOWN_APP_DIRS = [
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    r"C:\Windows\System32",
    r"C:\Windows",
]

def is_blocked(command: str) -> Optional[str]:
    lower = command.lower()
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, lower): return pattern
    return None

def find_app(app_name: str) -> Optional[str]:
    exe = app_name if app_name.lower().endswith(".exe") else f"{app_name}.exe"
    try:
        result = subprocess.run(
            ["where", exe], 
            capture_output=True, 
            text=True, 
            check=False, 
            timeout=5
        )
        if result.stdout.strip():
            return result.stdout.strip().splitlines()[0]
    except Exception: pass
    if HAS_WINREG:
        for hive in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
            try:
                key = winreg.OpenKey(
                    hive,
                    rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe}",
                )
                path, _ = winreg.QueryValueEx(key, "")
                if path and os.path.exists(path):
                    return path
            except Exception: pass
    start_menus = [
        os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
    ]
    base_name = os.path.splitext(exe)[0].lower()
    for start_menu in start_menus:
        try:
            for root, _, files in os.walk(start_menu):
                for f in files:
                    if f.lower().startswith(base_name) and f.endswith(".lnk"):
                        return os.path.join(root, f)
        except Exception: pass
    for dir_path in KNOWN_APP_DIRS:
        candidate = os.path.join(dir_path, exe)
        if os.path.exists(candidate): return candidate
    return None

def find_file(filename: str, search_root: str = r"C:\Users") -> Optional[str]:
    try:
        result = subprocess.run(
            ["where", "/r", search_root, filename],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if result.stdout.strip():
            return result.stdout.strip().splitlines()[0]
    except Exception: pass
    return None

def resolve_command(command: str) -> str:
    def resolve_exe(match):
        exe_name = match.group(0)
        # Don't try to resolve system32 paths that are already absolute
        if "\\" in exe_name: return exe_name
        full_path = find_app(exe_name)
        return f'"{full_path}"' if full_path else exe_name
    # Resolve bare .exe names (not already quoted or path-prefixed)
    command = re.sub(r'(?<!["\\/])\b[\w.-]+\.exe\b', resolve_exe, command, flags=re.IGNORECASE)
    # Verify absolute file paths and search if missing
    paths = re.findall(r'[A-Za-z]:\\[^\s"]+', command)
    for path in paths:
        clean_path = path.strip('"')
        if not os.path.exists(clean_path):
            filename = os.path.basename(clean_path)
            found = find_file(filename)
            if found:
                command = command.replace(path, f'"{found}"')
    return command

def execute_command(command: str, timeout: int = 20) -> str:
    command = command.strip()
    # Safety check
    if is_blocked(command):
        return f"⛔ Blocked: command matches dangerous pattern `{is_blocked(command)}`"
    # Resolve executable paths
    command = resolve_command(command)
    if command.lower().startswith("start "):
        if not command.lower().startswith('start ""'):
            command = re.sub(r'^start\s+', 'start "" ', command, count=1, flags=re.IGNORECASE)
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        output = ""
        if result.stdout.strip():
            output += result.stdout.strip()
        if result.stderr.strip():
            if output:
                output += "\n"
            output += result.stderr.strip()
        return output if output else "(command ran, no output)"
    except subprocess.TimeoutExpired:
        return f"⏱️ Command timed out after {timeout}s"
    except FileNotFoundError:
        return "❌ Command not found — check the executable name"
    except Exception as e:
        return f"❌ Execution error: {e}"

def get_system_snapshot() -> dict:
    snapshot = {}
    try:
        result = subprocess.run("wmic os get Caption,Version /value", shell=True,
                               capture_output=True, text=True, timeout=5)
        for line in result.stdout.strip().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                snapshot[k.strip()] = v.strip()
    except Exception: pass
    try:
        result = subprocess.run("hostname", shell=True, capture_output=True, text=True, timeout=3)
        snapshot["Hostname"] = result.stdout.strip()
    except Exception: pass
    return snapshot
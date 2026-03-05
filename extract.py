import subprocess, os, re
from typing import Optional
from datetime import datetime
try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False

# Dangerous command patterns requiring confirmation
CONFIRMATION_PATTERNS = [
    (r"\bdel\b",      "delete files"),
    (r"\brmdir\b",    "remove directory"),
    (r"\brd\b",       "remove directory"),
    (r"\btaskkill\b", "kill a process"),
    (r"\bformat\b",   "format a drive"),
    (r"\bshutdown\b", "shutdown/restart system"),
    (r"\bpowershell.*remove-item\b", "delete files via PowerShell"),
]

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

# Natural Language → PowerShell mapping
NL_TO_POWERSHELL = {
    r"(show|list|top)\s+(memory|ram)\s*(apps?|processes?|usage)?": (
        "Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 10 Name, @{N='Memory(MB)';E={[math]::Round($_.WorkingSet64/1MB,2)}} | Format-Table -AutoSize"
    ),
    r"(show|list|running)?\s*services?\s*(not\s*running|stopped)": (
        "Get-Service | Where-Object {$_.Status -eq 'Stopped'} | Select-Object Name, DisplayName, Status | Format-Table -AutoSize"
    ),
    r"(show|list|running)\s*services?": (
        "Get-Service | Where-Object {$_.Status -eq 'Running'} | Select-Object Name, DisplayName | Format-Table -AutoSize"
    ),
    r"(show|disk|drive)\s*(space|usage|free)?": (
        "Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{N='Used(GB)';E={[math]::Round(($_.Used)/1GB,2)}}, @{N='Free(GB)';E={[math]::Round(($_.Free)/1GB,2)}} | Format-Table -AutoSize"
    ),
    r"(top|high)\s*(cpu|processor)\s*(processes?|apps?)?": (
        "Get-Process | Sort-Object CPU -Descending | Select-Object -First 10 Name, CPU, @{N='Memory(MB)';E={[math]::Round($_.WorkingSet64/1MB,2)}} | Format-Table -AutoSize"
    ),
    r"(show|list)\s*(startup|boot)\s*(items?|programs?|apps?)?": (
        "Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location | Format-Table -AutoSize"
    ),
    r"(show|list)\s*(open|active|listening)\s*ports?": (
        "Get-NetTCPConnection | Where-Object {$_.State -eq 'Listen'} | Select-Object LocalAddress, LocalPort, State | Sort-Object LocalPort | Format-Table -AutoSize"
    ),
    r"(show|list)\s*(environment|env)\s*(variables?)?": (
        "Get-ChildItem Env: | Select-Object Name, Value | Format-Table -AutoSize"
    ),
    r"(show|list)\s*(recent|last)\s*(events?|errors?|logs?)": (
        "Get-EventLog -LogName System -Newest 20 -EntryType Error | Select-Object TimeGenerated, Source, Message | Format-Table -AutoSize"
    ),
    r"(show|list)\s*(users?|accounts?)": (
        "Get-LocalUser | Select-Object Name, Enabled, LastLogon | Format-Table -AutoSize"
    ),
    r"(show|list)\s*(wifi|wireless)\s*(profiles?|networks?|passwords?)?": (
        "netsh wlan show profiles"
    ),
    r"flush\s*(dns|cache)": (
        "ipconfig /flushdns"
    ),
    r"(show|list)\s*(installed|apps?|programs?|software)": (
        "Get-ItemProperty HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | Select-Object DisplayName, DisplayVersion, Publisher | Where-Object {$_.DisplayName} | Sort-Object DisplayName | Format-Table -AutoSize"
    ),
}

# Offline fallback rules (Feature 14) 
OFFLINE_RULES = {
    r"\btime\b":                              ("time", None, "Get current time"),
    r"\bopen\s+notepad\b":                    ("command", "start notepad.exe", "Open Notepad"),
    r"\bopen\s+calc(ulator)?\b":              ("command", "start calc.exe", "Open Calculator"),
    r"\bopen\s+(explorer|file\s*explorer)\b": ("command", "start explorer.exe", "Open File Explorer"),
    r"\bopen\s+cmd\b":                        ("command", "start cmd", "Open Command Prompt"),
    r"\bopen\s+(vs\s*code|code)\b":           ("quick_open", "vscode", "Open VS Code"),
    r"\bopen\s+youtube\b":                    ("quick_open", "youtube", "Open YouTube"),
    r"\bopen\s+google\b":                     ("quick_open", "google", "Open Google"),
    r"\bdir\b|\blist\s+files?\b":             ("command", "dir %USERPROFILE%", "List files"),
    r"\bip\s*(config|address)?\b":            ("command", "ipconfig", "Show network info"),
    r"\btask\s*list\b|\bprocesses?\b":        ("command", "tasklist", "List processes"),
    r"\bsearch\s+pdf\b":                      ("search", "pdf", "Search PDF files"),
    r"\bsearch\s+py\b":                       ("search", "py", "Search Python files"),
    r"\bplay\s+music\b":                      ("music", "play", "Play music"),
    r"\bshow\s+apps?\b":                      ("show_apps", None, "Show installed apps"),
    r"\bsystem\s*info\b":                     ("command", "systeminfo", "Show system information"),
}

# Error diagnosis patterns
ERROR_DIAGNOSES = {
    r"access\s+is\s+denied":             {
        "cause": "Insufficient permissions",
        "suggestions": ["Run the application as Administrator", "Check file/folder permissions", "Disable UAC temporarily if safe"]
    },
    r"the\s+system\s+cannot\s+find":     {
        "cause": "File or path not found",
        "suggestions": ["Verify the file/path exists", "Check for typos in the path", "Use full absolute path"]
    },
    r"is\s+not\s+recognized":            {
        "cause": "Command or executable not found in PATH",
        "suggestions": ["Install the application", "Add its folder to system PATH", "Use the full path to the executable"]
    },
    r"the\s+process\s+cannot\s+access":  {
        "cause": "File locked by another process",
        "suggestions": ["Close other apps using the file", "Restart the locking process", "Use Resource Monitor to identify the lock"]
    },
    r"not\s+enough\s+memory|out\s+of\s+memory": {
        "cause": "Insufficient RAM or virtual memory",
        "suggestions": ["Close memory-heavy applications", "Increase virtual memory size", "Restart the system to free memory"]
    },
    r"timed\s+out":                      {
        "cause": "Operation exceeded time limit",
        "suggestions": ["Try again with a longer timeout", "Check if the target service is running", "Verify network connectivity"]
    },
    r"already\s+exists":                 {
        "cause": "File or folder already exists at target",
        "suggestions": ["Delete or rename the existing item first", "Use /Y flag to force overwrite (if safe)"]
    },
    r"syntax\s+(is\s+)?incorrect":       {
        "cause": "Invalid command syntax",
        "suggestions": ["Check command spelling and flags", "Run `command /?` for help", "Verify all required arguments are present"]
    },
}

KNOWN_APP_DIRS = [
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    r"C:\Windows\System32",
    r"C:\Windows",
]


# Safety helpers

def requires_confirmation(command: str) -> Optional[str]:
    lower = command.lower()
    for pattern, description in CONFIRMATION_PATTERNS:
        if re.search(pattern, lower):
            return description
    return None


def is_blocked(command: str) -> Optional[str]:
    lower = command.lower()
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, lower):
            return pattern
    return None


# PowerShell translator
def translate_to_powershell(user_input: str) -> Optional[str]:
    lower = user_input.lower().strip()
    for pattern, ps_cmd in NL_TO_POWERSHELL.items():
        if re.search(pattern, lower):
            return ps_cmd
    return None

def run_powershell(ps_command: str, timeout: int = 20) -> str:
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_command],
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace"
        )
        output = ""
        if result.stdout.strip():
            output += result.stdout.strip()
        if result.stderr.strip():
            output += ("\n" if output else "") + result.stderr.strip()
        return output if output else "(no output)"
    except subprocess.TimeoutExpired:
        return f"⏱️ PowerShell command timed out after {timeout}s"
    except Exception as e:
        return f"❌ PowerShell error: {e}"

# Offline fallback classifier
def offline_classify(user_input: str) -> Optional[dict]:
    """Fast regex-based intent classifier — no LLM needed."""
    lower = user_input.lower().strip()
    for pattern, (mode, action, reason) in OFFLINE_RULES.items():
        if re.search(pattern, lower):
            return {
                "mode": mode,
                "confidence": 0.85,
                "reason": reason,
                "action": action,
                "offline": True
            }
    return None

# Error diagnosis
def diagnose_error(output: str) -> Optional[dict]:
    lower = output.lower()
    for pattern, diagnosis in ERROR_DIAGNOSES.items():
        if re.search(pattern, lower):
            return diagnosis
    return None

def format_error_diagnosis(output: str, command: str = "") -> str:
    diagnosis = diagnose_error(output)
    if not diagnosis:
        return output
    lines = [output, "", "🔍 Error Diagnosis:"]
    lines.append(f"  Likely cause: {diagnosis['cause']}")
    lines.append("  Suggestions:")
    for s in diagnosis["suggestions"]:
        lines.append(f"    • {s}")
    return "\n".join(lines)

# App/file resolution
def find_app(app_name: str) -> Optional[str]:
    exe = app_name if app_name.lower().endswith(".exe") else f"{app_name}.exe"
    try:
        result = subprocess.run(
            ["where", exe], capture_output=True, text=True, check=False, timeout=5
        )
        if result.stdout.strip():
            return result.stdout.strip().splitlines()[0]
    except Exception:
        pass
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
            except Exception:
                pass
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
        except Exception:
            pass
    for dir_path in KNOWN_APP_DIRS:
        candidate = os.path.join(dir_path, exe)
        if os.path.exists(candidate):
            return candidate
    return None

def find_file(filename: str, search_root: str = r"C:\Users") -> Optional[str]:
    try:
        result = subprocess.run(
            ["where", "/r", search_root, filename],
            capture_output=True, text=True, timeout=20,
        )
        if result.stdout.strip():
            return result.stdout.strip().splitlines()[0]
    except Exception:
        pass
    return None

def resolve_command(command: str) -> str:
    def resolve_exe(match):
        exe_name = match.group(0)
        if "\\" in exe_name:
            return exe_name
        full_path = find_app(exe_name)
        return f'"{full_path}"' if full_path else exe_name

    command = re.sub(r'(?<!["\\/])\b[\w.-]+\.exe\b', resolve_exe, command, flags=re.IGNORECASE)
    paths = re.findall(r'[A-Za-z]:\\[^\s"]+', command)
    for path in paths:
        clean_path = path.strip('"')
        if not os.path.exists(clean_path):
            filename = os.path.basename(clean_path)
            found = find_file(filename)
            if found:
                command = command.replace(path, f'"{found}"')
    return command

# Main executor
def execute_command(command: str, timeout: int = 20, skip_confirmation_check: bool = False) -> str:
    command = command.strip()
    # Safety check
    blocked = is_blocked(command)
    if blocked:
        return f"⛔ Blocked: command matches dangerous pattern `{blocked}`"

    # Confirmation check (caller handles the actual confirmation flow)
    if not skip_confirmation_check:
        needs_confirm = requires_confirmation(command)
        if needs_confirm:
            return f"__NEEDS_CONFIRMATION__:{needs_confirm}"

    command = resolve_command(command)
    if command.lower().startswith("start "):
        if not command.lower().startswith('start ""'):
            command = re.sub(r'^start\s+', 'start "" ', command, count=1, flags=re.IGNORECASE)

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace",
        )
        output = ""
        if result.stdout.strip():
            output += result.stdout.strip()
        if result.stderr.strip():
            output += ("\n" if output else "") + result.stderr.strip()
        raw = output if output else "(command ran, no output)"

        # Auto-diagnose errors
        if result.returncode != 0 or any(kw in raw.lower() for kw in ("error", "denied", "cannot", "not recognized", "failed")):
            return format_error_diagnosis(raw, command)
        return raw

    except subprocess.TimeoutExpired:
        return f"⏱️ Command timed out after {timeout}s"
    except FileNotFoundError:
        return "❌ Command not found — check the executable name"
    except Exception as e:
        return f"❌ Execution error: {e}"

def get_system_snapshot() -> dict:
    snapshot = {}
    try:
        result = subprocess.run(
            "wmic os get Caption,Version /value",
            shell=True, capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.strip().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                snapshot[k.strip()] = v.strip()
    except Exception:
        pass
    try:
        result = subprocess.run("hostname", shell=True, capture_output=True, text=True, timeout=3)
        snapshot["Hostname"] = result.stdout.strip()
    except Exception:
        pass
    return snapshot


# ── System health monitor helper (Feature 11) ─────────────────────────────────

def get_health_alerts() -> list[dict]:
    """Return list of health alerts for CPU, RAM, disk. Called by background thread."""
    alerts = []
    try:
        # RAM
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 1 Name, @{N='MB';E={[math]::Round($_.WorkingSet64/1MB,1)}} | ConvertTo-Json"],
            capture_output=True, text=True, timeout=8
        )
        if result.stdout.strip():
            import json
            data = json.loads(result.stdout.strip())
            if data.get("MB", 0) > 800:
                alerts.append({
                    "type": "memory",
                    "message": f"⚠ {data['Name']} using {data['MB']} MB memory",
                    "severity": "warning" if data["MB"] < 1500 else "critical"
                })
    except Exception:
        pass

    try:
        # Disk space
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "Get-PSDrive C | Select-Object @{N='FreePct';E={[math]::Round($_.Free/($_.Used+$_.Free)*100,1)}} | ConvertTo-Json"],
            capture_output=True, text=True, timeout=8
        )
        if result.stdout.strip():
            import json
            data = json.loads(result.stdout.strip())
            pct = data.get("FreePct", 100)
            if pct < 15:
                alerts.append({
                    "type": "disk",
                    "message": f"⚠ C: drive only {pct}% free",
                    "severity": "warning" if pct > 5 else "critical"
                })
    except Exception:
        pass

    return alerts
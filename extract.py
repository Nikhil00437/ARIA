import re, os, subprocess, winreg, psutil, datetime, webbrowser, urllib.parse
from typing import Optional, Tuple
from constants import BLOCKED_PATTERNS, CONFIRM_PATTERNS, POWERSHELL_PATTERNS
# Command Safety
def is_blocked(command: str) -> bool:
    cmd_lower = command.lower().strip()
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, cmd_lower, re.I): return True
    return False

def needs_confirmation(command: str) -> bool:
    cmd_lower = command.lower().strip()
    for pattern in CONFIRM_PATTERNS:
        if re.search(pattern, cmd_lower, re.I): return True
    return False
# NL → PowerShell
def nl_to_powershell(text: str) -> Optional[str]:
    text_lower = text.lower().strip()
    for pattern, cmd in POWERSHELL_PATTERNS.items():
        if re.search(pattern, text_lower): return cmd
    return None
# App / File Resolver
_COMMON_APPS = {
    "notepad":    "notepad.exe",
    "calc":       "calc.exe",
    "calculator": "calc.exe",
    "paint":      "mspaint.exe",
    "wordpad":    "wordpad.exe",
    "explorer":   "explorer.exe",
    "terminal":   "wt.exe",
    "cmd":        "cmd.exe",
    "powershell": "powershell.exe",
    "task manager": "taskmgr.exe",
    "taskmgr":    "taskmgr.exe",
    "chrome":     "chrome.exe",
    "firefox":    "firefox.exe",
    "edge":       "msedge.exe",
    "vlc":        "vlc.exe",
    "code":       "code.exe",
    "vscode":     "code.exe",
    "spotify":    "spotify.exe",
    "discord":    "discord.exe",
    "slack":      "slack.exe",
    "obs":        "obs64.exe",
    "steam":      "steam.exe",
}
_COMMON_PATHS = [
    os.environ.get("PROGRAMFILES", "C:\\Program Files"),
    os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"),
    os.environ.get("LOCALAPPDATA", ""),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
    os.environ.get("APPDATA", ""),
]
def resolve_app(name: str) -> Optional[str]:
    name_lower = name.lower().strip()
    # Known map
    if name_lower in _COMMON_APPS: return _COMMON_APPS[name_lower]
    # Search Program Files
    for base in _COMMON_PATHS:
        if not base: continue
        for root, dirs, files in os.walk(base):
            for f in files:
                if f.lower().startswith(name_lower) and f.endswith(".exe"): return os.path.join(root, f)
            # Limit depth for performance
            if root.count(os.sep) - base.count(os.sep) > 3:
                del dirs[:]
    # Windows Registry App Paths
    try:
        reg_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
            for candidate in [name_lower, name_lower + ".exe"]:
                try:
                    with winreg.OpenKey(key, candidate) as app_key:
                        path, _ = winreg.QueryValueEx(app_key, "")
                        if path: return path
                except FileNotFoundError: continue
    except Exception: pass
    # Start Menu search
    start_menu_dirs = [
        os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
    ]
    for smd in start_menu_dirs:
        for root, _, files in os.walk(smd):
            for f in files:
                if name_lower in f.lower() and f.endswith(".lnk"): return os.path.join(root, f)
    return None
# Error Diagnosis
_ERROR_DIAGNOSES = [
    (r"access is denied",         "Insufficient permissions. Try running as administrator."),
    (r"file not found|no such file", "The file or path doesn't exist. Check spelling or location."),
    (r"is not recognized",        "Command not found. The program may not be installed or not in PATH."),
    (r"cannot find the path",     "Path doesn't exist. Verify the directory structure."),
    (r"out of memory",            "System is low on RAM. Close other applications."),
    (r"permission denied",        "Insufficient permissions. Try running as administrator."),
    (r"the process cannot access", "File is locked by another process."),
    (r"network path was not found", "Network share is unavailable. Check connection."),
    (r"disk is full|not enough space", "Disk is full. Free up space before retrying."),
    (r"syntax error|unexpected token", "Command syntax error. Check the command format."),
    (r"execution policy",         "PowerShell execution policy blocked the script. Run: Set-ExecutionPolicy RemoteSigned -Scope CurrentUser"),
    (r"cannot be loaded because running scripts is disabled", "Enable scripts: Set-ExecutionPolicy RemoteSigned -Scope CurrentUser"),
]
def diagnose_error(output: str) -> Optional[str]:
    output_lower = output.lower()
    for pattern, diagnosis in _ERROR_DIAGNOSES:
        if re.search(pattern, output_lower): return diagnosis
    return None
# System Snapshot
def system_snapshot() -> dict:
    try:
        cpu    = psutil.cpu_percent(interval=0.5)
        mem    = psutil.virtual_memory()
        disk   = psutil.disk_usage("C:\\") if os.name == "nt" else psutil.disk_usage("/")
        boot   = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.datetime.now() - boot
        return {
            "cpu_percent":      cpu,
            "ram_used_gb":      round(mem.used  / 1e9, 2),
            "ram_total_gb":     round(mem.total / 1e9, 2),
            "ram_percent":      mem.percent,
            "disk_used_gb":     round(disk.used / 1e9, 2),
            "disk_total_gb":    round(disk.total/ 1e9, 2),
            "disk_percent":     disk.percent,
            "uptime_hours":     round(uptime.total_seconds() / 3600, 1),
            "process_count":    len(psutil.pids()),
        }
    except Exception as e: return {"error": str(e)}

def format_snapshot(snap: dict) -> str:
    if "error" in snap: return f"System snapshot unavailable: {snap['error']}"
    return (
        f"**System Status**\n"
        f"• CPU: {snap['cpu_percent']}%\n"
        f"• RAM: {snap['ram_used_gb']} / {snap['ram_total_gb']} GB ({snap['ram_percent']}%)\n"
        f"• Disk (C:): {snap['disk_used_gb']} / {snap['disk_total_gb']} GB ({snap['disk_percent']}%)\n"
        f"• Uptime: {snap['uptime_hours']}h | Processes: {snap['process_count']}"
    )
# Health Alert Generator
def generate_health_alerts(snap: dict) -> list:
    alerts = []
    if snap.get("cpu_percent", 0) > 90: alerts.append(("error",   f"CPU critical: {snap['cpu_percent']}%"))
    elif snap.get("cpu_percent", 0) > 75: alerts.append(("warning", f"CPU high: {snap['cpu_percent']}%"))
    if snap.get("ram_percent", 0) > 90: alerts.append(("error",   f"RAM critical: {snap['ram_percent']}%"))
    elif snap.get("ram_percent", 0) > 80: alerts.append(("warning", f"RAM high: {snap['ram_percent']}%"))
    if snap.get("disk_percent", 0) > 90: alerts.append(("error",   f"Disk almost full: {snap['disk_percent']}%"))
    elif snap.get("disk_percent", 0) > 80: alerts.append(("warning", f"Disk usage high: {snap['disk_percent']}%"))
    return alerts
# Music playback (via default player)
def play_music(query: str) -> Tuple[bool, str]:
    music_dir = r"C:\Users\Nikhil\Music\Music"
    if not os.path.isdir(music_dir): return False, f"Music directory not found: {music_dir}"
    audio_ext = (".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".wma")
    matched = []
    query_lower = query.lower()
    for root, dirs, files in os.walk(music_dir):
        for f in files:
            if f.lower().endswith(audio_ext):
                if query_lower in f.lower(): matched.append(os.path.join(root, f))
    if not matched:
        all_files = []
        for root, dirs, files in os.walk(music_dir):
            for f in files:
                if f.lower().endswith(audio_ext): all_files.append(os.path.join(root, f))
        if not all_files: return False, "No music files found in your library."
        file_to_play = all_files[0]
        subprocess.Popen(["start", "", file_to_play], shell=True)
        return True, f"No match for '{query}', playing: {os.path.basename(file_to_play)}"
    file_to_play = matched[0]
    subprocess.Popen(["start", "", file_to_play], shell=True)
    return True, f"Playing: {os.path.basename(file_to_play)}"
import os, subprocess, re, webbrowser
from typing import Tuple
from extract import is_blocked, resolve_app, diagnose_error

class CommandExecutor:
    def __init__(self): self._shell = os.name == "nt"

    def execute(self, command: str, use_powershell: bool = False) -> Tuple[bool, str]:
        if is_blocked(command): return False, "❌ Command blocked: This operation is restricted for safety."
        try:
            if use_powershell: result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", command],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    shell=False,
                )
            else: result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    shell=self._shell,
                )
            output = result.stdout.strip() or result.stderr.strip()
            success = result.returncode == 0
            # Error diagnosis
            if not success and output:
                diagnosis = diagnose_error(output)
                if diagnosis: output += f"\n\n💡 **Likely cause:** {diagnosis}"
            return success, output or ("Command completed successfully." if success else "Command failed with no output.")
        except subprocess.TimeoutExpired: return False, "❌ Command timed out (30s limit)."
        except FileNotFoundError as e: return False, f"❌ Executable not found: {e}"
        except Exception as e: return False, f"❌ Execution error: {e}"

    def open_app(self, name: str) -> Tuple[bool, str]:
        path = resolve_app(name)
        if path:
            try:
                if path.endswith(".lnk"): os.startfile(path)
                else: subprocess.Popen([path], shell=False)
                return True, f"✅ Opened: {name}"
            except Exception as e: return False, f"❌ Failed to open {name}: {e}"
        # Last resort: try the name directly
        try:
            subprocess.Popen([name], shell=True)
            return True, f"✅ Launched: {name}"
        except Exception: return False, f"❌ Could not find or open: {name}"

    def open_url(self, url: str) -> Tuple[bool, str]:
        try:
            webbrowser.open(url)
            return True, f"✅ Opened: {url}"
        except Exception as e: return False, f"❌ Failed to open URL: {e}"

    def run_powershell(self, command: str) -> Tuple[bool, str]: return self.execute(command, use_powershell=True)

    def extract_app_name(self, text: str) -> str:
        patterns = [
            r"(?:open|launch|start|run)\s+(.+)",
            r"(?:start)\s+(.+)",
        ]
        for p in patterns:
            m = re.search(p, text, re.I)
            if m: return m.group(1).strip().strip("'\"")
        return text.strip()
import subprocess, shutil, os, json, threading
from typing import Optional, Generator, Callable
from constants import FABRIC_SEARCH_PATHS

# Well-known Fabric patterns grouped by use case
FABRIC_PATTERNS: dict[str, list[str]] = {
    "analysis": [
        "analyze_claims",
        "analyze_debate",
        "analyze_incident",
        "analyze_paper",
        "analyze_prose",
        "analyze_tech_impact",
        "analyze_threat_report",
        "analyze_email_headers",
        "analyze_logs",
    ],
    "extraction": [
        "extract_wisdom",
        "extract_ideas",
        "extract_insights",
        "extract_main_idea",
        "extract_article_wisdom",
        "extract_patterns",
        "extract_recommendations",
        "extract_references",
        "extract_sponsors",
        "extract_controversial_ideas",
    ],
    "summarization": [
        "summarize",
        "summarize_debate",
        "summarize_git_changes",
        "summarize_meeting",
        "summarize_paper",
        "summarize_prompt",
        "summarize_rpg_session",
        "tldr_rlhf",
        "create_5_sentence_summary",
        "create_micro_summary",
    ],
    "writing": [
        "write_essay",
        "improve_writing",
        "improve_prompt",
        "create_outline",
        "create_report_finding",
        "create_tags",
        "create_quiz",
        "rewrite_take",
    ],
    "security": [
        "create_threat_scenarios",
        "create_security_update",
        "analyze_malware",
        "create_stride_threat_model",
        "create_cyber_summary",
    ],
    "coding": [
        "create_coding_project",
        "explain_code",
        "create_git_diff_commit",
        "review_design",
    ],
    "content": [
        "create_video_chapters",
        "create_show_intro",
        "create_keynote",
        "create_markmap_visualization",
        "create_mermaid_visualization",
        "rate_content",
        "get_wow_per_minute",
    ],
    "ai & prompts": [
        "create_ai_jobs_analysis",
        "create_aphorisms",
        "create_better_frame",
        "create_investigation_visualization",
        "ask_secure_by_design_questions",
    ],
}

# Flat list for quick lookup
ALL_PATTERNS: list[str] = [p for group in FABRIC_PATTERNS.values() for p in group]


class FabricClient:
    def __init__(self):
        self._fabric_path: Optional[str] = self._find_fabric()
        self._available_patterns: Optional[list[str]] = None
    # Discovery
    def _find_fabric(self) -> Optional[str]:
        # Standard PATH lookup
        found = shutil.which("fabric")
        if found: return found
        # Common install locations from centralized constants
        candidates = [os.path.expandvars(os.path.expanduser(c)) for c in FABRIC_SEARCH_PATHS]
        for c in candidates:
            if os.path.isfile(c): return c
        return None

    @property
    def available(self) -> bool: return self._fabric_path is not None

    def get_fabric_path(self) -> Optional[str]: return self._fabric_path

    def set_fabric_path(self, path: str):
        if os.path.isfile(path):
            self._fabric_path = path
            self._available_patterns = None  # invalidate cache so it re-discovers patterns

    def list_patterns(self) -> list[str]:
        if self._available_patterns is not None: return self._available_patterns
        if not self.available: return ALL_PATTERNS  # fall back to known list
        try:
            result = subprocess.run(
                [self._fabric_path, "--list"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                patterns = [
                    line.strip()
                    for line in result.stdout.splitlines()
                    if line.strip() and not line.startswith("#")
                ]
                self._available_patterns = patterns if patterns else ALL_PATTERNS
            else: self._available_patterns = ALL_PATTERNS
        except Exception: self._available_patterns = ALL_PATTERNS
        return self._available_patterns

    def pattern_exists(self, pattern: str) -> bool: return pattern in self.list_patterns()

    # Core run
    def run(self, pattern: str, text: str, extra_args: list[str] = None) -> tuple[bool, str]:
        if not self.available: return False, (
                "❌ Fabric not found. Install it from https://github.com/danielmiessler/fabric "
                "or set the path manually with `/fabric path <path>`."
            )
        if not self.pattern_exists(pattern):
            close = self._closest_pattern(pattern)
            hint = f" Did you mean `{close}`?" if close else ""
            return False, f"❌ Unknown Fabric pattern: `{pattern}`.{hint}"

        args = [self._fabric_path, "--pattern", pattern]
        if extra_args: args.extend(extra_args)

        try:
            result = subprocess.run(
                args,
                input=text,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                output = result.stdout.strip()
                return True, output if output else "✅ Pattern ran but returned no output."
            else:
                err = result.stderr.strip() or "Unknown error"
                return False, f"❌ Fabric error: {err}"
        except subprocess.TimeoutExpired: return False, "❌ Fabric timed out (120s). Try a shorter input."
        except Exception as e: return False, f"❌ Fabric execution failed: {e}"

    def run_stream(
        self,
        pattern: str,
        text: str,
        chunk_callback: Callable[[str], None],
        done_callback: Callable[[], None],
        error_callback: Callable[[str], None],
        extra_args: list[str] = None,
        timeout: int = 120,
    ):
        # Run a Fabric pattern and stream output chunks to chunk_callback.
        # Runs in a background thread.
        import time, sys
        def _run():
            if not self.available:
                error_callback(
                    "Fabric not found. Install from https://github.com/danielmiessler/fabric"
                )
                return
            if not self.pattern_exists(pattern):
                close = self._closest_pattern(pattern)
                hint = f" Did you mean `{close}`?" if close else ""
                error_callback(f"Unknown pattern: `{pattern}`.{hint}")
                return

            args = [self._fabric_path, "--pattern", pattern, "--stream"]
            if extra_args: args.extend(extra_args)

            start_time = time.time()
            try:
                proc = subprocess.Popen(
                    args,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                )
                # Write input and close stdin
                proc.stdin.write(text)
                proc.stdin.close()

                stderr_output = []

                # Read stderr in a separate thread to avoid pipe deadlock
                def _read_stderr():
                    for line in proc.stderr:
                        stderr_output.append(line)
                stderr_thread = threading.Thread(target=_read_stderr, daemon=True)
                stderr_thread.start()

                # Stream stdout with timeout
                while True:
                    elapsed = time.time() - start_time
                    if elapsed > timeout:
                        proc.kill()
                        error_callback(f"Fabric timed out ({timeout}s). Try a shorter input.")
                        return

                    # Non-blocking readline with a short timeout via polling
                    line = proc.stdout.readline()
                    if line:
                        chunk_callback(line)
                    elif proc.poll() is not None:
                        # Process ended, drain remaining stdout
                        for remaining in proc.stdout:
                            chunk_callback(remaining)
                        break
                    else:
                        time.sleep(0.05)  # small sleep to avoid busy-wait

                stderr_thread.join(timeout=5)
                proc.wait()

                if proc.returncode != 0:
                    err = "".join(stderr_output).strip() or "Unknown error"
                    error_callback(f"Fabric error: {err}")
                else:
                    done_callback()
            except subprocess.TimeoutExpired:
                proc.kill()
                error_callback(f"Fabric timed out ({timeout}s). Try a shorter input.")
            except Exception as e:
                error_callback(f"Fabric execution failed: {e}")

        threading.Thread(target=_run, daemon=True).start()

    # Convenience wrappers
    def summarize(self, text: str) -> tuple[bool, str]: return self.run("summarize", text)

    def extract_wisdom(self, text: str) -> tuple[bool, str]: return self.run("extract_wisdom", text)

    def extract_ideas(self, text: str) -> tuple[bool, str]: return self.run("extract_ideas", text)

    def improve_writing(self, text: str) -> tuple[bool, str]: return self.run("improve_writing", text)

    def analyze_claims(self, text: str) -> tuple[bool, str]: return self.run("analyze_claims", text)

    def explain_code(self, text: str) -> tuple[bool, str]: return self.run("explain_code", text)

    def create_outline(self, text: str) -> tuple[bool, str]: return self.run("create_outline", text)

    def rate_content(self, text: str) -> tuple[bool, str]: return self.run("rate_content", text)

    def create_quiz(self, text: str) -> tuple[bool, str]: return self.run("create_quiz", text)

    def create_tags(self, text: str) -> tuple[bool, str]: return self.run("create_tags", text)

    # Pattern suggestion
    def suggest_pattern(self, user_text: str) -> Optional[str]:
        # Heuristically suggest the best Fabric pattern for the user's text.
        # Used by the intent classifier fallback.
        text_lower = user_text.lower()

        hints = [
            (["summarize", "summary", "tldr", "brief"], "summarize"),
            (["wisdom", "insights", "takeaways", "learn"], "extract_wisdom"),
            (["ideas", "key points", "main points"], "extract_ideas"),
            (["improve", "rewrite", "fix writing", "better writing"], "improve_writing"),
            (["claims", "fact check", "argument", "debate"], "analyze_claims"),
            (["explain code", "what does this code", "review code"], "explain_code"),
            (["outline", "structure", "organize"], "create_outline"),
            (["rate", "score", "evaluate", "quality"], "rate_content"),
            (["quiz", "questions", "test"], "create_quiz"),
            (["tags", "keywords", "labels"], "create_tags"),
            (["threat", "security", "vulnerability"], "create_threat_scenarios"),
            (["meeting", "transcript", "notes"], "summarize_meeting"),
            (["paper", "research", "academic"], "analyze_paper"),
        ]
        for keywords, pattern in hints:
            if any(k in text_lower for k in keywords): return pattern
        return None

    def _closest_pattern(self, name: str) -> Optional[str]:
        # Simple prefix/substring match for typo correction.
        patterns = self.list_patterns()
        name_lower = name.lower()
        for p in patterns:
            if p.startswith(name_lower) or name_lower in p: return p
        return None

    # Status
    def status(self) -> dict: return {
            "available": self.available,
            "path": self._fabric_path,
            "pattern_count": len(self.list_patterns()),
        }
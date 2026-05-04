import re, datetime, threading, random, uuid, time, os, json
from typing import Optional
from tools import AVAILABLE_TOOLS, execute_tool
from extract import nl_to_powershell, system_snapshot, format_snapshot, play_music, needs_confirmation
from executor import CommandExecutor
from image_generation import generate_image_async
from constants import SUGGESTION_POOLS, FABRIC_QUICK_PATTERNS
from fabric_client import FabricClient, FABRIC_PATTERNS
from pattern_engine import load_pattern, list_patterns, run_pattern_stream
from security import InputSanitizer, OutputFormatter, get_rate_limiter

class ChatEngine:
    def __init__(self, db, llm_client, signals, selfmod_controller=None, voice_engine=None):
        self._db         = db
        self._llm        = llm_client
        self._signals    = signals
        self._selfmod    = selfmod_controller
        self._voice      = voice_engine
        self._executor   = CommandExecutor()
        self._fabric     = FabricClient()
        self._confirm_pending: Optional[dict] = None
        self._message_count = 0
        self._gen = 0
        self._recent_suggestions: set = set()
        self._last_command_time: float = 0
        self._command_cooldown: float = 0.5  # seconds between commands
        self._context_cache: dict = {}
        self._context_cache_time: float = 0
        self._rate_limiter = get_rate_limiter()
        self._sanitizer = InputSanitizer()
        self._last_summary_time: float = 0
        self._summary_cooldown: float = 300  # 5 minutes between summaries
        self._message_count_for_summary = 30  # Summarize after this many messages

    # Public: Process Input
    def process(self, user_input: str, session_id: str, history: list):
        # Rate limiting check
        if not self._rate_limiter.is_allowed(session_id):
            self._emit("⚠️ Rate limit exceeded. Please wait before sending more messages.")
            return

        self._message_count += 1
        text = user_input.strip()

        # Sanitize user input
        sanitized = self._sanitizer.sanitize_user_input(text)
        if sanitized.was_modified:
            self._signals.warning_added.emit("warning", f"Input modified: {', '.join(sanitized.warnings)}")
        text = sanitized.text

        if not text:
            return

        # Confirmation flow
        if self._confirm_pending:
            self._handle_confirmation(text, session_id)
            return
        # Slash commands
        if text.startswith("/"):
            self._handle_slash(text, session_id, history)
            return
        # Classify intent
        intent = self._llm.classify_intent(text)
        mode   = intent.get("mode", "chat")
        conf   = intent.get("confidence", 0.5)

        self._signals.timeline_event.emit("intent", f"{mode} ({conf:.0%}) \u2014 {text[:60]}")
        # Route
        {
            "chat":         self._handle_chat,
            "command":      self._handle_command,
            "wikipedia":    self._handle_wikipedia,
            "browser":      self._handle_browser,
            "music":        self._handle_music,
            "search":       self._handle_search,
            "show_apps":    self._handle_show_apps,
            "time":         self._handle_time,
            "quick_open":   self._handle_command,
            "smart_search": self._handle_smart_search,
            "powershell":   self._handle_powershell,
            "explain":      self._handle_explain,
            "image_gen":    self._handle_image_gen,
            "fabric":       self._handle_fabric,
            "history":      self._handle_history_intent,
            "rerun":        self._handle_rerun_intent,
        }.get(mode, self._handle_chat)(text, session_id, history)
        # Selfmod milestone check
        if self._selfmod and self._message_count % 15 == 0:
            self._selfmod.analyze_async(session_id)

        # Auto-summarize check
        self._check_auto_summarize(session_id, history)

    def _check_auto_summarize(self, session_id: str, history: list):
        """Check if conversation needs auto-summarization."""
        import time

        # Check cooldown
        current_time = time.time()
        if current_time - self._last_summary_time < self._summary_cooldown:
            return

        # Check message count
        if len(history) < self._message_count_for_summary:
            return

        # Only summarize if output mode is set to verbose
        output_mode = self._selfmod.get("output_mode", "verbose") if self._selfmod else "verbose"
        if output_mode != "verbose":
            return

        # Summarize the conversation
        self._last_summary_time = current_time
        self._signals.status_update.emit("Summarizing conversation...")

        def _summarize():
            try:
                # Get last N messages to summarize
                recent_history = history[-20:]
                conversation_text = "\n".join(
                    f"{m['role']}: {m['content'][:200]}" for m in recent_history
                )

                summary = self._llm.summarize(conversation_text)
                self._signals.chat_response.emit("assistant",
                    f"📝 **Conversation Summary**\n\n{summary}\n\n"
                    f"_This summary was auto-generated after {len(history)} messages._"
                )
                self._signals.status_update.emit("Ready")
            except Exception as e:
                print(f"[Auto-summarize] Error: {e}")

        threading.Thread(target=_summarize, daemon=True).start()

    # Context injection
    def _build_system_prompt(self, session_id: str) -> str:
        base = self._selfmod.get("system_prompt_safety", "") if self._selfmod else ""
        if not base:
            from constants import SYSTEM_PROMPT
            base = SYSTEM_PROMPT

        now = datetime.datetime.now().astimezone()
        time_str = now.strftime("%A, %B %d, %Y at %I:%M %p %Z")

        # Cache context for 30 seconds
        current_time = time.time()
        if current_time - self._context_cache_time > 30:
            import psutil
            try:
                mem = psutil.virtual_memory()
                cpu = psutil.cpu_percent(interval=None)
                disk = psutil.disk_usage("C:\\")
                self._context_cache = {
                    "cpu": f"{cpu:.0f}%",
                    "ram_pct": f"{mem.percent:.0f}%",
                    "ram_gb": f"{mem.used/1024**3:.1f}/{mem.total/1024**3:.1f} GB",
                    "disk_free": f"{disk.free/1024**3:.1f} GB free",
                }
            except Exception:
                self._context_cache = {}
            self._context_cache_time = current_time

        ctx = self._context_cache
        context_header = (
            f"\n\nCURRENT CONTEXT:\n"
            f"- Time: {time_str}\n"
            f"- Working directory: {os.getcwd()}\n"
            f"- CPU: {ctx.get('cpu', 'N/A')} | RAM: {ctx.get('ram_pct', 'N/A')} ({ctx.get('ram_gb', 'N/A')})\n"
            f"- Disk: {ctx.get('disk_free', 'N/A')} on C:\n"
            f"- Session ID: {session_id[:8]}...\n"
            f"- Messages in this session: {self._message_count}"
        )

        return base + context_header

    # Slash Commands
    def _handle_slash(self, text: str, session_id: str, history: list):
        cmd = text.lower().strip()

        if cmd == "/history":
            cmds = self._db.get_command_history(session_id, limit=10)
            if not cmds:
                self._emit("No command history for this session.")
                return
            lines = [f"`{i+1}.` `{c['command']}` \u2014 {'\u2705' if c['success'] else '\u274c'} {str(c['timestamp'])[:16]}" for i, c in enumerate(cmds)]
            self._emit("**Recent commands:**\n\n" + "\n\n".join(lines))
            return

        if cmd == "/sessions":
            sessions = self._db.list_sessions(limit=10000)
            if not sessions:
                self._emit("No previous sessions found.")
                return
            lines = []
            for i, s in enumerate(sessions):
                ts = str(s.get("created", ""))[:16]
                sid = s.get("session_id", "")[:8]
                title = s.get("title") or self._db.generate_session_title(s.get("session_id", ""))
                prefix = "1." if sid == session_id[:8] else f"{i+1}."
                lines.append(f"`{prefix}` `{sid}...` \u2014 {ts} \u2014 {title}")
            self._emit("**Previous Sessions:**\n\n" + "\n\n".join(lines) + "\n\n\n\nType `/session N` to switch to a session.")
            return

        if cmd == "/new":
            new_id = str(uuid.uuid4())
            self._signals.session_loaded.emit(new_id)
            self._emit(f"\u2728 Started new session `{new_id[:8]}...`")
            return

        if cmd == "/resume":
            last_id = self._db.get_last_session()
            if not last_id or last_id == session_id:
                self._emit("No previous session to resume. This is already the latest session.")
                return
            self._signals.session_loaded.emit(last_id)
            title = self._db.generate_session_title(last_id)
            self._emit(f"\U0001f504 Resumed session `{last_id[:8]}...` \u2014 {title}")
            return

        m = re.match(r"/session\s+(\d+)", cmd)
        if m:
            n = int(m.group(1))
            sessions = self._db.list_sessions(limit=20)
            if n < 1 or n > len(sessions):
                self._emit(f"Invalid session number. Use 1-{len(sessions)}.")
                return
            target = sessions[n - 1]
            target_id = target.get("session_id", "")
            self._signals.session_loaded.emit(target_id)
            self._db.save_last_session(target_id)
            title = self._db.generate_session_title(target_id)
            self._emit(f"\U0001f504 Switched to session `{target_id[:8]}...` \u2014 {title}")
            return

        m = re.match(r"/rerun\s+(\d+)", cmd)
        if m:
            n = int(m.group(1))
            entry = self._db.get_nth_command(session_id, n)
            if not entry:
                self._emit(f"No command #{n} in history.")
                return
            self._signals.status_update.emit(f"Re-running: {entry['command']}")
            self._run_command(entry["command"], session_id, use_ps=False)
            return

        if cmd == "/snapshot":
            snap = system_snapshot()
            self._emit(format_snapshot(snap))
            return

        if cmd == "/context":
            sys_prompt = self._build_system_prompt(session_id)
            msg_count = len(history)
            total_tokens = sum(self._llm.estimate_tokens(m.get("content", "")) for m in history[-20:])
            self._emit(
                f"**Current Context:**\n\n"
                f"```\n{sys_prompt}\n```\n\n"
                f"**Conversation:** {msg_count} messages, ~{total_tokens} tokens in context window\n\n"
                f"Max context: {self._llm._max_context_tokens} tokens"
            )
            return

        if cmd == "/selfmod":
            if self._selfmod:
                proposals = self._selfmod.analyze_sync(session_id)
                if proposals:
                    self._signals.selfmod_proposal.emit(proposals)
                    self._emit(f"\U0001f50d Found {len(proposals)} behavioral pattern(s). Check the **Self-Mod** panel.")
                else: self._emit("No significant behavioral patterns detected yet. Keep using ARIA and check back.")
            else: self._emit("Self-Modification system not initialized.")
            return

        if cmd == "/mods":
            if self._selfmod:
                mods = self._selfmod.get_active_modifications()
                if not mods:
                    self._emit("No active modifications. All settings are at defaults.")
                    return
                lines = [f"\u2022 **{m['param_label']}**: `{m['new_value']}` (since {str(m['timestamp'])[:16]})" for m in mods]
                self._emit("**Active Modifications:**\n" + "\n".join(lines))
            return

        # /fabric
        if cmd.startswith("/fabric"):
            self._handle_fabric_slash(text, session_id)
            return

        if cmd == "/help":
            self._emit(
                "**ARIA Commands:**\n\n"
                "`/history` \u2014 Show recent command history\n\n"
                "`/rerun N` \u2014 Re-run command #N from history\n\n"
                "`/sessions` \u2014 List previous sessions with titles\n\n"
                "`/session N` \u2014 Switch to session #N\n\n"
                "`/resume` \u2014 Resume your last session\n\n"
                "`/new` \u2014 Start a fresh session\n\n"
                "`/snapshot` \u2014 System health snapshot\n\n"
                "`/context` \u2014 Show what context the LLM sees\n\n"
                "`/selfmod` \u2014 Run behavioral analysis now\n\n"
                "`/mods` \u2014 Show active self-modifications\n\n"
                "`/export json` \u2014 Export current session as JSON\n\n"
                "`/export md` \u2014 Export current session as Markdown\n\n"
                "`/fabric <pattern> <text>` \u2014 Run a Fabric AI pattern\n\n"
                "`/fabric list` \u2014 List all available Fabric patterns\n\n"
                "`/fabric list <group>` \u2014 List patterns in a group\n\n"
                "`/fabric status` \u2014 Check if Fabric is installed\n\n"
                "`/fabric path <path>` \u2014 Set Fabric binary path manually\n\n"
                "`/pattern list` \u2014 List local pattern files\n\n"
                "`/pattern <name> <text>` \u2014 Run a local pattern\n\n"
                "`/help` \u2014 This message"
            )
            return
        # Export commands
        if cmd.startswith("/export"):
            self._handle_export(cmd, session_id)
            return
        if cmd == "/pattern list" or cmd == "/patterns":
            patterns = list_patterns()
            if not patterns:
                self._emit("No patterns found. Make sure the `patterns/` folder is in the ARIA directory.")
                return
            lines = [f"`{p['name']}` \u2014 {p['preview']}" for p in patterns[:30]]
            self._emit("**Available Patterns** (use `/pattern <n> <input>`):\n" + "\n".join(lines))
            if len(patterns) > 30: self._emit(f"\u2026and {len(patterns) - 30} more. Use the **Patterns** page to browse all.")
            return
        m = re.match(r"/pattern\s+(\S+)(?:\s+(.+))?", text, re.DOTALL)
        if m:
            pattern_name = m.group(1)
            user_input   = (m.group(2) or "").strip()
            self._run_pattern(pattern_name, user_input, session_id)
            return
        self._emit(f"Unknown command: `{text}`. Try `/help`.")

    def _handle_export(self, cmd: str, session_id: str):
        """Handle export commands."""
        import os
        import json

        parts = cmd.split()
        if len(parts) < 2:
            self._emit("Usage: `/export json` or `/export md`")
            return

        export_type = parts[1].lower()

        try:
            if export_type == "json":
                content = self._db.export_session_json(session_id)
                filename = f"aria_session_{session_id[:8]}.json"
            elif export_type == "md" or export_type == "markdown":
                content = self._db.export_session_markdown(session_id)
                filename = f"aria_session_{session_id[:8]}.md"
            else:
                self._emit(f"Unknown export type: `{export_type}`. Use `json` or `md`.")
                return

            # Save to downloads folder
            downloads = os.path.expanduser("~/Downloads")
            filepath = os.path.join(downloads, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            self._emit(f"✅ Session exported to:\n`{filepath}`")

        except Exception as e:
            self._emit(f"❌ Export failed: {e}")

    def _run_pattern(self, name: str, user_input: str, session_id: str):
        self._signals.typing_indicator.emit(True)
        self._gen = getattr(self, '_gen', 0) + 1
        my_gen = self._gen
        def _run():
            try:
                full = ""
                for chunk in run_pattern_stream(name, user_input, self._llm):
                    if getattr(self, '_gen', my_gen) != my_gen:
                        return
                    self._signals.chat_stream_chunk.emit(chunk)
                    full += chunk
                self._signals.chat_stream_done.emit()
                self._signals.chat_response.emit("assistant", f"**Pattern: {name}**\n\n{full}")
                self._db.log_command(session_id, f"/pattern {name}", full[:500], True)
            except Exception as e:
                self._emit(f"\u274c Pattern error: {e}")
            finally:
                self._signals.typing_indicator.emit(False)
        threading.Thread(target=_run, daemon=True).start()

    # Intent Handlers
    def _handle_chat(self, text: str, session_id: str, history: list):
        self._signals.typing_indicator.emit(True)
        try:
            system_prompt = self._build_system_prompt(session_id)
            messages = [{"role": m["role"], "content": m["content"]} for m in history[-20:]]

            response_data = self._llm.chat_with_tools(messages, AVAILABLE_TOOLS, system_prompt)
            tool_calls = response_data.get("tool_calls", [])
            content = response_data.get("content", "")

            full_response = ""
            if tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls
                })

                if content:
                    self._signals.chat_stream_chunk.emit(content + "\n\n")
                    full_response += content + "\n\n"

                for tool_call in tool_calls:
                    tool_name = tool_call["function"]["name"]
                    tool_args = tool_call["function"]["arguments"]
                    self._signals.status_update.emit(f"Running tool: {tool_name}...")

                    tool_result = execute_tool(tool_name, tool_args)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "name": tool_name,
                        "content": tool_result
                    })

                self._signals.status_update.emit("Evaluating result...")

                for chunk in self._llm.chat_stream(messages, system_prompt):
                    self._signals.chat_stream_chunk.emit(chunk)
                    full_response += chunk

                self._signals.chat_stream_done.emit()
                self._signals.status_update.emit("Ready")
            else:
                if content:
                    self._signals.chat_stream_chunk.emit(content)
                    full_response = content
                self._signals.chat_stream_done.emit()

            # Apply output mode
            output_mode = self._selfmod.get("output_mode", "verbose") if self._selfmod else "verbose"
            if output_mode == "summary" and len(full_response) > 400:
                summarized = self._llm.summarize(full_response)
                self._signals.chat_response.emit("assistant", summarized)
            else: self._signals.chat_response.emit("assistant", full_response)
            if self._voice: self._voice.speak(full_response)
        except Exception as e: self._emit(f"\u274c LLM error: {e}")
        finally: self._signals.typing_indicator.emit(False)

    def _handle_command(self, text: str, session_id: str, history: list):
        # Rate limiting
        now = time.time()
        if now - self._last_command_time < self._command_cooldown:
            self._emit("\u23f3 Please wait a moment before sending another command.")
            return
        self._last_command_time = now

        app_name = self._executor.extract_app_name(text)
        # Check if it looks like a system command vs app open
        if re.search(r"^(open|launch|start)\s+", text, re.I):
            success, output = self._executor.open_app(app_name)
            self._emit(output)
            self._db.log_command(session_id, f"open {app_name}", output, success)
            self._signals.terminal_output.emit(output, not success)
            return
        # It's a shell command \u2014 check for confirmation
        if needs_confirmation(text):
            self._confirm_pending = {"cmd": text, "session_id": session_id}
            verbosity = self._selfmod.get("confirmation_verbosity", "full") if self._selfmod else "full"
            if verbosity == "full": msg = f"\u26a0\ufe0f This command requires confirmation:\n```\n{text}\n```\nType **yes** to execute or **no** to cancel."
            else: msg = f"\u26a0\ufe0f Confirm: `{text[:60]}` \u2014 **yes** / **no**"
            self._signals.confirm_request.emit(text, msg)
            self._emit(msg, force_speak=True)
            return
        self._run_command(text, session_id)

    def _handle_confirmation(self, text: str, session_id: str):
        pending = self._confirm_pending
        self._confirm_pending = None
        if text.lower().strip() in ("yes", "y", "confirm", "ok"):
            self._emit("\u2705 Executing...")
            self._run_command(pending["cmd"], pending["session_id"])
        else: self._emit("\u274c Cancelled.")

    def _run_command(self, cmd: str, session_id: str, use_ps: bool = False):
        def _run():
            self._signals.status_update.emit("Running command...")
            success, output = self._executor.execute(cmd, use_powershell=use_ps)
            self._signals.terminal_output.emit(output, not success)
            self._signals.timeline_event.emit("command", f"{'\u2705' if success else '\u274c'} {cmd[:60]}")
            self._db.log_command(session_id, cmd, output, success)

            output_mode = self._selfmod.get("output_mode", "verbose") if self._selfmod else "verbose"
            if output_mode == "summary" and len(output) > 300: display = self._llm.summarize(output)
            else: display = output
            self._emit(display)
            self._signals.status_update.emit("Ready")
        threading.Thread(target=_run, daemon=True).start()

    def _handle_wikipedia(self, text: str, session_id: str, history: list):
        def _run():
            self._signals.status_update.emit("Looking up Wikipedia...")
            result = self._llm.wikipedia_lookup(text)
            # If Wikipedia found nothing, fall back to LLM chat
            if "No article found" in result or "lookup failed" in result:
                self._emit("No Wikipedia article found. Here's what I know:\n\n")
                system_prompt = self._build_system_prompt(session_id)
                messages = [{"role": m["role"], "content": m["content"]} for m in history[-20:]]
                full_response = ""
                for chunk in self._llm.chat_stream(messages, system_prompt):
                    self._signals.chat_stream_chunk.emit(chunk)
                    full_response += chunk
                self._signals.chat_stream_done.emit()
                self._signals.chat_response.emit("assistant", full_response)
            else: self._emit(result)
            self._signals.status_update.emit("Ready")
        threading.Thread(target=_run, daemon=True).start()

    def _handle_browser(self, text: str, session_id: str, history: list):
        url = self._llm.generate_url(text)
        if url:
            success, msg = self._executor.open_url(url)
            self._emit(msg)
            self._signals.timeline_event.emit("browser", url)

    def _handle_music(self, text: str, session_id: str, history: list):
        query = re.sub(r"^play\s+", "", text, flags=re.I).strip()
        try:
            success, msg = play_music(query)
            self._emit(msg)
        except Exception as e:
            self._emit(f"\u274c Music playback failed: {e}")

    def _handle_search(self, text: str, session_id: str, history: list):
        self._handle_smart_search(text, session_id, history)

    def _handle_smart_search(self, text: str, session_id: str, history: list):
        url = self._llm.generate_url(text)
        if url:
            success, msg = self._executor.open_url(url)
            self._emit(msg)
            self._signals.timeline_event.emit("search", url)
        else: self._emit("Couldn't determine a search URL. Try being more specific.")

    def _handle_show_apps(self, text: str, session_id: str, history: list):
        self._handle_powershell("list installed apps", session_id, history)

    def _handle_time(self, text: str, session_id: str, history: list):
        now = datetime.datetime.now().astimezone()
        self._emit(f"\U0001f550 **{now.strftime('%A, %B %d %Y \u2014 %I:%M %p %Z')}**")

    def _handle_powershell(self, text: str, session_id: str, history: list):
        ps_cmd = nl_to_powershell(text)
        if not ps_cmd:
            # Let LLM generate a PS command
            resp = self._llm.chat([{"role": "user", "content": f"Write a PowerShell command to: {text}. Return only the command, no explanation."}])
            ps_cmd = resp.strip()

        def _run():
            self._signals.status_update.emit("Running PowerShell...")
            success, output = self._executor.run_powershell(ps_cmd)
            self._signals.terminal_output.emit(output, not success)
            self._db.log_command(session_id, ps_cmd, output, success)

            output_mode = self._selfmod.get("output_mode", "verbose") if self._selfmod else "verbose"
            display = self._llm.summarize(output) if output_mode == "summary" and len(output) > 300 else output
            self._emit(display)
            self._signals.status_update.emit("Ready")
        threading.Thread(target=_run, daemon=True).start()

    def _handle_explain(self, text: str, session_id: str, history: list):
        def _run():
            self._signals.status_update.emit("Analyzing...")
            result = self._llm.explain(text)
            self._emit(result)
            self._signals.status_update.emit("Ready")
        threading.Thread(target=_run, daemon=True).start()

    def _handle_image_gen(self, text: str, session_id: str, history: list):
        prompt = re.sub(r"(generate|create|draw|make|produce)\s+(an?\s+)?(image|picture|photo|art)\s+(of\s+)?", "", text, flags=re.I).strip()
        prompt = prompt or text
        self._emit(f"\U0001f3a8 Generating image: *{prompt}*")
        generate_image_async(prompt, self._signals)

    def _handle_history_intent(self, text: str, session_id: str, history: list):
        cmds = self._db.get_command_history(session_id, limit=10)
        if not cmds:
            self._emit("No command history for this session.")
            return
        lines = [f"`{i+1}.` `{c['command']}` \u2014 {'\u2705' if c['success'] else '\u274c'} {str(c['timestamp'])[:16]}" for i, c in enumerate(cmds)]
        self._emit("**Recent commands:**\n\n" + "\n\n".join(lines))

    def _handle_rerun_intent(self, text: str, session_id: str, history: list):
        m = re.search(r"(\d+)", text)
        if not m:
            self._emit("Specify a command number to re-run, e.g. 'rerun 3' or use `/rerun N`.")
            return
        n = int(m.group(1))
        entry = self._db.get_nth_command(session_id, n)
        if not entry:
            self._emit(f"No command #{n} in history.")
            return
        self._signals.status_update.emit(f"Re-running: {entry['command']}")
        self._run_command(entry["command"], session_id, use_ps=False)

    def _handle_fabric_slash(self, text: str, session_id: str):
        remainder = re.sub(r"^/fabric\s*", "", text, flags=re.I).strip()

        if not remainder or remainder.lower() == "help":
            self._emit(
                "**Fabric Usage:**\n\n"
                "`/fabric status` \u2014 Check if Fabric is installed\n\n"
                "`/fabric list` \u2014 List all patterns grouped by category\n\n"
                "`/fabric list <group>` \u2014 List patterns in a specific group\n\n"
                "`/fabric path <path>` \u2014 Set Fabric binary path manually\n\n"
                "`/fabric <pattern> <text>` \u2014 Run a pattern on text\n\n"
                "**Quick patterns:**\n" +
                "\n".join(f"`/fabric {k}` \u2014 {v}" for k, v in FABRIC_QUICK_PATTERNS.items())
            )
            return

        # status
        if remainder.lower() == "status":
            st = self._fabric.status()
            if st["available"]: self._emit(
                    f"\u2705 **Fabric is installed**\n\n"
                    f"\u2022 Path: `{st['path']}`\n"
                    f"\u2022 Available patterns: **{st['pattern_count']}**\n\n"
                    f"Use `/fabric list` to see all patterns."
                )
            else: self._emit(
                    "\u274c **Fabric not found**\n\n"
                    "Install it from [github.com/danielmiessler/fabric](https://github.com/danielmiessler/fabric)\n\n"
                    "Once installed, use `/fabric path <path-to-binary>` if it's not in your PATH."
                )
            return

        # list
        if remainder.lower().startswith("list"):
            parts = remainder.split(maxsplit=1)
            group = parts[1].lower().strip() if len(parts) > 1 else None
            if group and group in FABRIC_PATTERNS:
                patterns = FABRIC_PATTERNS[group]
                self._emit(
                    f"**Fabric patterns \u2014 {group}:**\n\n" +
                    "\n".join(f"\u2022 `{p}`" for p in patterns)
                )
            else:
                lines = []
                for grp, pats in FABRIC_PATTERNS.items():
                    lines.append(f"**{grp.title()}**")
                    lines.extend(f"  \u2022 `{p}`" for p in pats)
                    lines.append("")
                self._emit(
                    f"**All Fabric pattern groups** \u2014 {sum(len(v) for v in FABRIC_PATTERNS.values())} total:\n\n" +
                    "\n\n".join(lines)
                )
            return

        # path
        m = re.match(r"path\s+(.+)", remainder, re.I)
        if m:
            path = m.group(1).strip().strip("\"'")
            if os.path.isfile(path):
                self._fabric.set_fabric_path(path)
                self._emit(f"\u2705 Fabric path set to `{path}`")
            else: self._emit(f"\u274c File not found: `{path}`")
            return

        # <pattern> <text>
        parts = remainder.split(maxsplit=1)
        pattern_raw = parts[0].lower().strip()
        pattern = FABRIC_QUICK_PATTERNS.get(pattern_raw, pattern_raw)
        input_text = parts[1].strip() if len(parts) > 1 else ""

        if not input_text:
            self._emit(
                f"\u26a0\ufe0f No input text provided for pattern `{pattern}`.\n\n"
                f"Usage: `/fabric {pattern} <text to process>`"
            )
            return

        self._run_fabric_pattern(pattern, input_text, session_id)

    def _handle_fabric(self, text: str, session_id: str, history: list):
        m = re.match(r"(?:fabric\s+)?(\w+)\s+(?:this\s*[:\-]?\s*|with fabric\s*[:\-]?\s*)?(.+)", text, re.I | re.S)
        if m:
            pattern_raw = m.group(1).lower()
            input_text  = m.group(2).strip()
            pattern = FABRIC_QUICK_PATTERNS.get(pattern_raw, pattern_raw)
            self._run_fabric_pattern(pattern, input_text, session_id)
        else:
            m2 = re.match(r"(extract|analyze|create|improve|summarize|rate|write|review)\s+(\w+)\s+(.+)", text, re.I | re.S)
            if m2:
                verb = m2.group(1).lower()
                noun = m2.group(2).lower()
                input_text = m2.group(3).strip()
                candidate = f"{verb}_{noun}"
                pattern = FABRIC_QUICK_PATTERNS.get(candidate, candidate)
                if self._fabric.pattern_exists(pattern):
                    self._run_fabric_pattern(pattern, input_text, session_id)
                    return
            suggested = self._fabric.suggest_pattern(text)
            if suggested:
                self._emit(
                    f"\U0001f4a1 Looks like you want Fabric. Try:\n\n"
                    f"`/fabric {suggested} <your text>`\n\n"
                    f"Or `/fabric list` to see all patterns."
                )
            else: self._emit(
                    "\U0001f9f5 **Fabric** is ready. Usage:\n\n"
                    "`/fabric <pattern> <text>` \u2014 Run any Fabric pattern\n\n"
                    "`/fabric list` \u2014 Browse all patterns"
                )

    def _run_fabric_pattern(self, pattern: str, text: str, session_id: str):
        self._signals.typing_indicator.emit(True)
        self._signals.status_update.emit(f"Running Fabric: {pattern}...")
        self._signals.timeline_event.emit("fabric", f"{pattern} \u2014 {text[:60]}")

        def _on_chunk(chunk: str): self._signals.chat_stream_chunk.emit(chunk)

        def _on_done():
            self._signals.chat_stream_done.emit()
            self._signals.typing_indicator.emit(False)
            self._signals.status_update.emit("Ready")

        def _on_error(err: str):
            self._signals.chat_stream_done.emit()
            self._emit(f"\u274c Fabric error: {err}")
            self._signals.typing_indicator.emit(False)
            self._signals.status_update.emit("Ready")

        if self._fabric.available:
            self._fabric.run_stream(
                pattern=pattern,
                text=text,
                chunk_callback=_on_chunk,
                done_callback=_on_done,
                error_callback=_on_error,
            )
        else: _on_error(
                "Fabric not found. Install from https://github.com/danielmiessler/fabric "
                "or set the path with `/fabric path <binary-path>`"
            )

    # Helpers
    def _emit(self, text: str, force_speak: bool = False):
        # Sanitize output for safe display
        sanitized = self._sanitizer.sanitize_markdown(text)
        if sanitized.was_modified:
            print(f"[Security] Output sanitized: {sanitized.warnings}")
        self._signals.chat_response.emit("assistant", sanitized.text)
        if self._voice and force_speak: self._voice.speak(text, force=True)

    def get_suggestions(self, mode: str = "chat") -> list:
        count = self._selfmod.get("suggestion_count", 3) if self._selfmod else 3
        pool = SUGGESTION_POOLS.get(mode, SUGGESTION_POOLS["chat"])
        # Deduplicate: exclude recently used suggestions
        available = [s for s in pool if s not in self._recent_suggestions]
        if len(available) < count:
            # Reset if not enough variety
            self._recent_suggestions.clear()
            available = pool
        picked = random.sample(available, min(count, len(available)))
        self._recent_suggestions.update(picked)
        return picked

    def set_confirm_pending(self, state: Optional[dict]): self._confirm_pending = state

import re, datetime, threading, random, uuid
from typing import Optional
from extract import nl_to_powershell, system_snapshot, format_snapshot, play_music, needs_confirmation
from executor import CommandExecutor
from image_generation import generate_image_async
from constants import SUGGESTIONS, SUGGESTION_POOLS, FABRIC_QUICK_PATTERNS
from fabric_client import FabricClient, FABRIC_PATTERNS
from pattern_engine import load_pattern, list_patterns, run_pattern_stream

class ChatEngine:
    def __init__(self, db, llm_client, signals, selfmod_controller=None, voice_engine=None):
        self._db         = db
        self._llm        = llm_client
        self._signals    = signals
        self._selfmod    = selfmod_controller
        self._voice      = voice_engine
        self._executor   = CommandExecutor()
        self._fabric     = FabricClient()
        # Pending confirmation state
        self._confirm_pending: Optional[dict] = None
        # Output mode (can be overridden by selfmod)
        self._message_count = 0

    # Public: Process Input
    def process(self, user_input: str, session_id: str, history: list):
        self._message_count += 1
        text = user_input.strip()
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

        self._signals.timeline_event.emit("intent", f"{mode} ({conf:.0%}) — {text[:60]}")
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
        if self._selfmod and self._message_count % 15 == 0: self._selfmod.analyze_async(session_id)

    # Slash Commands
    def _handle_slash(self, text: str, session_id: str, history: list):
        cmd = text.lower().strip()

        if cmd == "/history":
            cmds = self._db.get_command_history(session_id, limit=10)
            if not cmds:
                self._emit("No command history for this session.")
                return
            lines = [f"`{i+1}.` `{c['command']}` — {'✅' if c['success'] else '❌'} {str(c['timestamp'])[:16]}" for i, c in enumerate(cmds)]
            self._emit("**Recent commands:**\n\n" + "\n\n".join(lines))
            return

        if cmd == "/sessions":
            sessions = self._db.list_sessions(limit = 10000)
            if not sessions:
                self._emit("No previous sessions found.")
                return
            lines = []
            for i, s in enumerate(sessions):
                ts = str(s.get("created", ""))[:16]
                sid = s.get("session_id", "")[:8]
                title = s.get("title") or self._db.generate_session_title(s.get("session_id", ""))
                prefix = "1." if sid == session_id[:8] else f"{i+1}."
                lines.append(f"`{prefix}` `{sid}...` — {ts} — {title}")
            self._emit("**Previous Sessions:**\n\n" + "\n\n".join(lines) + "\n\n\n\nType `/session N` to switch to a session.")
            return

        if cmd == "/new":
            new_id = str(uuid.uuid4())
            self._signals.session_loaded.emit(new_id)
            self._emit(f"✨ Started new session `{new_id[:8]}...`")
            return

        if cmd == "/resume":
            last_id = self._db.get_last_session()
            if not last_id or last_id == session_id:
                self._emit("No previous session to resume. This is already the latest session.")
                return
            self._signals.session_loaded.emit(last_id)
            title = self._db.generate_session_title(last_id)
            self._emit(f"🔄 Resumed session `{last_id[:8]}...` — {title}")
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
            self._emit(f"🔄 Switched to session `{target_id[:8]}...` — {title}")
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

        if cmd == "/selfmod":
            if self._selfmod:
                proposals = self._selfmod.analyze_sync(session_id)
                if proposals:
                    self._signals.selfmod_proposal.emit(proposals)
                    self._emit(f"🔍 Found {len(proposals)} behavioral pattern(s). Check the **Self-Mod** panel.")
                else: self._emit("No significant behavioral patterns detected yet. Keep using ARIA and check back.")
            else: self._emit("Self-Modification system not initialized.")
            return

        if cmd == "/mods":
            if self._selfmod:
                mods = self._selfmod.get_active_modifications()
                if not mods:
                    self._emit("No active modifications. All settings are at defaults.")
                    return
                lines = [f"• **{m['param_label']}**: `{m['new_value']}` (since {str(m['timestamp'])[:16]})" for m in mods]
                self._emit("**Active Modifications:**\n" + "\n".join(lines))
            return

        # /fabric
        if cmd.startswith("/fabric"):
            self._handle_fabric_slash(text, session_id)
            return

        if cmd == "/help":
            self._emit(
                "**ARIA Commands:**\n\n"
                "`/history` — Show recent command history\n\n"
                "`/rerun N` — Re-run command #N from history\n\n"
                "`/sessions` — List previous sessions with titles\n\n"
                "`/session N` — Switch to session #N\n\n"
                "`/resume` — Resume your last session\n\n"
                "`/new` — Start a fresh session\n\n"
                "`/snapshot` — System health snapshot\n\n"
                "`/selfmod` — Run behavioral analysis now\n\n"
                "`/mods` — Show active self-modifications\n\n"
                "`/fabric <pattern> <text>` — Run a Fabric AI pattern\n\n"
                "`/fabric list` — List all available Fabric patterns\n\n"
                "`/fabric list <group>` — List patterns in a group (analysis/extraction/summarization/writing/security/coding)\n\n"
                "`/fabric status` — Check if Fabric is installed\n\n"
                "`/fabric path <path>` — Set Fabric binary path manually\n\n"
                "`/help` — This message\n"
            )
            return
        if cmd == "/pattern list" or cmd == "/patterns":
            patterns = list_patterns()
            if not patterns:
                self._emit("No patterns found. Make sure the `patterns/` folder is in the ARIA directory.")
                return
            lines = [f"`{p['name']}` — {p['preview']}" for p in patterns[:30]]
            self._emit("**Available Patterns** (use `/pattern <n> <input>`):\n" + "\n".join(lines))
            if len(patterns) > 30: self._emit(f"…and {len(patterns) - 30} more. Use the **Patterns** page to browse all.")
            return
        m = re.match(r"/pattern\s+(\S+)(?:\s+(.+))?", cmd, re.DOTALL)
        if m:
            pattern_name = m.group(1)
            user_input   = (m.group(2) or "").strip()
            self._run_pattern(pattern_name, user_input, session_id)
            return
        self._emit(f"Unknown command: `{text}`. Try `/help`.")

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
                self._emit(f"❌ Pattern error: {e}")
            finally:
                self._signals.typing_indicator.emit(False)
        threading.Thread(target=_run, daemon=True).start()

    # Intent Handlers
    def _handle_chat(self, text: str, session_id: str, history: list):
        self._signals.typing_indicator.emit(True)
        try:
            # Build message history for LLM (history already includes current message)
            messages = [{"role": m["role"], "content": m["content"]} for m in history[-20:]]

            full_response = ""
            for chunk in self._llm.chat_stream(messages):
                self._signals.chat_stream_chunk.emit(chunk)
                full_response += chunk
            self._signals.chat_stream_done.emit()
            # Apply output mode
            output_mode = self._selfmod.get("output_mode", "verbose") if self._selfmod else "verbose"
            if output_mode == "summary" and len(full_response) > 400:
                summarized = self._llm.summarize(full_response)
                self._signals.chat_response.emit("assistant", summarized)
            else: self._signals.chat_response.emit("assistant", full_response)
            if self._voice: self._voice.speak(full_response)
        except Exception as e: self._emit(f"❌ LLM error: {e}")
        finally: self._signals.typing_indicator.emit(False)

    def _handle_command(self, text: str, session_id: str, history: list):
        app_name = self._executor.extract_app_name(text)
        # Check if it looks like a system command vs app open
        if re.search(r"^(open|launch|start)\s+", text, re.I):
            success, output = self._executor.open_app(app_name)
            self._emit(output)
            self._db.log_command(session_id, f"open {app_name}", output, success)
            self._signals.terminal_output.emit(output, not success)
            return
        # It's a shell command — check for confirmation
        if needs_confirmation(text):
            self._confirm_pending = {"cmd": text, "session_id": session_id}
            verbosity = self._selfmod.get("confirmation_verbosity", "full") if self._selfmod else "full"
            if verbosity == "full": msg = f"⚠️ This command requires confirmation:\n```\n{text}\n```\nType **yes** to execute or **no** to cancel."
            else: msg = f"⚠️ Confirm: `{text[:60]}` — **yes** / **no**"
            self._signals.confirm_request.emit(text, msg)
            self._emit(msg, force_speak=True)
            return
        self._run_command(text, session_id)

    def _handle_confirmation(self, text: str, session_id: str):
        pending = self._confirm_pending
        self._confirm_pending = None
        if text.lower().strip() in ("yes", "y", "confirm", "ok"):
            self._emit("✅ Executing...")
            self._run_command(pending["cmd"], pending["session_id"])
        else: self._emit("❌ Cancelled.")

    def _run_command(self, cmd: str, session_id: str, use_ps: bool = False):
        def _run():
            self._signals.status_update.emit("Running command...")
            success, output = self._executor.execute(cmd, use_powershell=use_ps)
            self._signals.terminal_output.emit(output, not success)
            self._signals.timeline_event.emit("command", f"{'✅' if success else '❌'} {cmd[:60]}")
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
                messages = [{"role": m["role"], "content": m["content"]} for m in history[-20:]]
                messages.append({"role": "user", "content": text})
                full_response = ""
                for chunk in self._llm.chat_stream(messages):
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
        success, msg = play_music(query)
        self._emit(msg)

    def _handle_search(self, text: str, session_id: str, history: list): self._handle_smart_search(text, session_id, history)

    def _handle_smart_search(self, text: str, session_id: str, history: list):
        url = self._llm.generate_url(text)
        if url:
            success, msg = self._executor.open_url(url)
            self._emit(msg)
            self._signals.timeline_event.emit("search", url)
        else: self._emit("Couldn't determine a search URL. Try being more specific.")

    def _handle_show_apps(self, text: str, session_id: str, history: list): self._handle_powershell("list installed apps", session_id, history)

    def _handle_time(self, text: str, session_id: str, history: list):
        import time
        offset = -time.timezone if time.daylight == 0 else -time.altzone
        tz = datetime.timezone(datetime.timedelta(seconds=offset))
        now = datetime.datetime.now(tz)
        self._emit(f"🕐 **{now.strftime('%A, %B %d %Y — %I:%M %p')}**")

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
        self._emit(f"🎨 Generating image: *{prompt}*")
        generate_image_async(prompt, self._signals)

    def _handle_history_intent(self, text: str, session_id: str, history: list):
        cmds = self._db.get_command_history(session_id, limit=10)
        if not cmds:
            self._emit("No command history for this session.")
            return
        lines = [f"`{i+1}.` `{c['command']}` — {'✅' if c['success'] else '❌'} {str(c['timestamp'])[:16]}" for i, c in enumerate(cmds)]
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
        # Handle /fabric <subcommand> from slash-command flow.
        # Strip the /fabric prefix and parse remainder
        remainder = re.sub(r"^/fabric\s*", "", text, flags=re.I).strip()

        if not remainder or remainder.lower() == "help":
            self._emit(
                "**Fabric Usage:**\n\n"
                "`/fabric status` — Check if Fabric is installed\n\n"
                "`/fabric list` — List all patterns grouped by category\n\n"
                "`/fabric list <group>` — List patterns in a specific group\n\n"
                "`/fabric path <path>` — Set Fabric binary path manually\n\n"
                "`/fabric <pattern> <text>` — Run a pattern on text\n\n"
                "**Quick patterns:**\n" +
                "\n".join(f"`/fabric {k}` — {v}" for k, v in FABRIC_QUICK_PATTERNS.items())
            )
            return

        # status
        if remainder.lower() == "status":
            st = self._fabric.status()
            if st["available"]: self._emit(
                    f"✅ **Fabric is installed**\n\n"
                    f"• Path: `{st['path']}`\n"
                    f"• Available patterns: **{st['pattern_count']}**\n\n"
                    f"Use `/fabric list` to see all patterns."
                )
            else: self._emit(
                    "❌ **Fabric not found**\n\n"
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
                    f"**Fabric patterns — {group}:**\n\n" +
                    "\n".join(f"• `{p}`" for p in patterns)
                )
            else:
                lines = []
                for grp, pats in FABRIC_PATTERNS.items():
                    lines.append(f"**{grp.title()}**")
                    lines.extend(f"  • `{p}`" for p in pats)
                    lines.append("")
                self._emit(
                    f"**All Fabric pattern groups** — {sum(len(v) for v in FABRIC_PATTERNS.values())} total:\n\n" +
                    "\n\n".join(lines)
                )
            return

        # path
        m = re.match(r"path\s+(.+)", remainder, re.I)
        if m:
            path = m.group(1).strip().strip("\"'")
            import os
            if os.path.isfile(path):
                self._fabric.set_fabric_path(path)
                self._emit(f"✅ Fabric path set to `{path}`")
            else: self._emit(f"❌ File not found: `{path}`")
            return

        # <pattern> <text>  OR just <pattern> (use clipboard/last message?)
        parts = remainder.split(maxsplit=1)
        pattern_raw = parts[0].lower().strip()
        # Resolve quick alias → full pattern name
        pattern = FABRIC_QUICK_PATTERNS.get(pattern_raw, pattern_raw)
        input_text = parts[1].strip() if len(parts) > 1 else ""

        if not input_text:
            self._emit(
                f"⚠️ No input text provided for pattern `{pattern}`.\n\n"
                f"Usage: `/fabric {pattern} <text to process>`\n\n"
                f"Or send a message that says **fabric {pattern}** followed by your content."
            )
            return

        self._run_fabric_pattern(pattern, input_text, session_id)

    def _handle_fabric(self, text: str, session_id: str, history: list):
        # Handle messages classified as 'fabric' intent.
        # Pattern: "fabric <pattern_name> <content>" or "<pattern_keyword> this: <content>"
        # Also handles natural: "summarize this with fabric: <content>"
        # Try to parse "fabric <pattern> <text>"
        m = re.match(r"(?:fabric\s+)?(\w+)\s+(?:this\s*[:\-]?\s*|with fabric\s*[:\-]?\s*)?(.+)", text, re.I | re.S)
        if m:
            pattern_raw = m.group(1).lower()
            input_text  = m.group(2).strip()

            # Resolve via quick alias or direct name
            pattern = FABRIC_QUICK_PATTERNS.get(pattern_raw, pattern_raw)
            self._run_fabric_pattern(pattern, input_text, session_id)
        else:
            # Try underscore-separated pattern names: "extract wisdom from text"
            m2 = re.match(r"(extract|analyze|create|improve|summarize|rate|write|review)\s+(\w+)\s+(.+)", text, re.I | re.S)
            if m2:
                verb = m2.group(1).lower()
                noun = m2.group(2).lower()
                input_text = m2.group(3).strip()
                candidate = f"{verb}_{noun}"
                # Check if it matches a known quick alias or fabric pattern
                pattern = FABRIC_QUICK_PATTERNS.get(candidate, candidate)
                if self._fabric.pattern_exists(pattern):
                    self._run_fabric_pattern(pattern, input_text, session_id)
                    return
            # Suggest a pattern based on content
            suggested = self._fabric.suggest_pattern(text)
            if suggested:
                self._emit(
                    f"💡 Looks like you want Fabric. Try:\n\n"
                    f"`/fabric {suggested} <your text>`\n\n"
                    f"Or `/fabric list` to see all patterns."
                )
            else: self._emit(
                    "🧵 **Fabric** is ready. Usage:\n\n"
                    "`/fabric <pattern> <text>` — Run any Fabric pattern\n\n"
                    "`/fabric list` — Browse all patterns"
                )

    def _run_fabric_pattern(self, pattern: str, text: str, session_id: str):
        # Execute a Fabric pattern with streaming output.
        self._signals.typing_indicator.emit(True)
        self._signals.status_update.emit(f"Running Fabric: {pattern}...")
        self._signals.timeline_event.emit("fabric", f"{pattern} — {text[:60]}")

        def _on_chunk(chunk: str): self._signals.chat_stream_chunk.emit(chunk)

        def _on_done():
            self._signals.chat_stream_done.emit()
            self._signals.typing_indicator.emit(False)
            self._signals.status_update.emit("Ready")

        def _on_error(err: str):
            self._signals.chat_stream_done.emit()
            self._emit(f"❌ Fabric error: {err}")
            self._signals.typing_indicator.emit(False)
            self._signals.status_update.emit("Ready")

        # Try streaming first; fall back to sync if stream not supported
        if self._fabric.available:
            self._fabric.run_stream(
                pattern=pattern,
                text=text,
                chunk_callback=_on_chunk,
                done_callback=_on_done,
                error_callback=_on_error,
            )
        else: _on_error(                                                                     # Fabric not installed — show install hint
                "Fabric not found. Install from https://github.com/danielmiessler/fabric " 
                "or set the path with `/fabric path <binary-path>`"
            )
            
    # Helpers
    def _emit(self, text: str, force_speak: bool = False):
        self._signals.chat_response.emit("assistant", text)
        if self._voice and force_speak: self._voice.speak(text, force=True)

    def get_suggestions(self, mode: str = "chat") -> list:
        count = self._selfmod.get("suggestion_count", 3) if self._selfmod else 3
        pool = SUGGESTION_POOLS.get(mode, SUGGESTION_POOLS["chat"])
        return random.sample(pool, min(count, len(pool)))

    def set_confirm_pending(self, state: Optional[dict]): self._confirm_pending = state
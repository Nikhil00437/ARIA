# main_window.py — Concept B: Floating Panels with working Quick Actions

import uuid, threading
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QApplication, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from constants import DEFAULT_THEME, CHAT_MODEL, THEMES
from signals import ARIASignals, HealthMonitor
from database import Database
from llm_client import LLMClient
from voice_engine import VoiceEngine
from chat_engine import ChatEngine
from styles import build_stylesheet
from title import TitleBar
from sidebar import Sidebar
from pages import ChatPage, TerminalPage, TimelinePage, WarningsPage
from selfmod_page import SelfModPage
from selfmod import SelfModController
from widgets import StatusBar
from quick_panel import QuickPanel, SystemPanel
from settings_dialog import SettingsDialog


class ARIAWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setMinimumSize(1100, 700)
        self.resize(1320, 820)

        self._signals    = ARIASignals()
        self._db         = Database()
        self._llm        = LLMClient()
        self._session_id = str(uuid.uuid4())
        self._history: list = []
        self._current_theme = DEFAULT_THEME
        self._selfmod: SelfModController = None
        self._voice  = VoiceEngine(self._signals)
        self._engine: ChatEngine = None
        self._health = HealthMonitor(self._signals)
        self._stream_started = False

        self._build_ui()
        self._connect_signals()
        self._apply_theme(DEFAULT_THEME)
        QTimer.singleShot(100, self._boot)

    # UI
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title bar
        self._title_bar = TitleBar(self)
        root.addWidget(self._title_bar)

        # Body: rail | content + right column
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # Icon rail
        self._sidebar = Sidebar()
        body.addWidget(self._sidebar)

        # Centre: padding wrapper around page stack
        centre_wrap = QWidget()
        centre_lyt = QVBoxLayout(centre_wrap)
        centre_lyt.setContentsMargins(16, 14, 10, 10)
        centre_lyt.setSpacing(0)

        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent; border: none;")

        # Pages
        self._chat_page     = ChatPage()
        self._terminal_page = TerminalPage()
        self._timeline_page = TimelinePage()
        self._warnings_page = WarningsPage()
        self._selfmod_page  = SelfModPage()

        try:
            from patterns_page import PatternsPage
            self._patterns_page = PatternsPage()
        except ImportError:
            self._patterns_page = QWidget()

        self._pages = {
            "chat":     self._chat_page,
            "terminal": self._terminal_page,
            "timeline": self._timeline_page,
            "warnings": self._warnings_page,
            "selfmod":  self._selfmod_page,
            "patterns": self._patterns_page,
        }
        for page in self._pages.values():
            self._stack.addWidget(page)

        centre_lyt.addWidget(self._stack, 1)
        body.addWidget(centre_wrap, 1)

        # Right column — Quick + System panels (visible only on Chat page)
        self._right_col = QWidget()
        self._right_col.setFixedWidth(210)
        right_lyt = QVBoxLayout(self._right_col)
        right_lyt.setContentsMargins(0, 14, 14, 10)
        right_lyt.setSpacing(12)

        self._quick_panel  = QuickPanel()
        self._system_panel = SystemPanel()

        right_lyt.addWidget(self._quick_panel)
        right_lyt.addWidget(self._system_panel)
        right_lyt.addStretch()

        body.addWidget(self._right_col)

        body_widget = QWidget()
        body_widget.setLayout(body)
        root.addWidget(body_widget, 1)

        # Status bar
        self._status_bar = StatusBar()
        root.addWidget(self._status_bar)

    # Signals
    def _connect_signals(self):
        s = self._signals

        # Sidebar nav
        self._sidebar.nav_clicked.connect(self._navigate)
        self._sidebar.voice_toggled.connect(self._on_voice_toggle)
        self._sidebar.silent_toggled.connect(self._on_silent_toggle)
        self._sidebar.mic_pressed.connect(self._on_mic_press)

        # Settings button in title bar
        self._title_bar.settings_requested.connect(self._open_settings)

        # Chat input
        self._chat_page.message_submitted.connect(self._on_user_message)
        self._chat_page.suggestion_clicked.connect(self._on_user_message)
        self._terminal_page.command_submitted.connect(self._on_terminal_command)

        # Quick panel wiring
        # pattern → put "/pattern <name> " in input and focus
        self._quick_panel.pattern_requested.connect(self._on_quick_pattern)
        # nav → switch page
        self._quick_panel.nav_requested.connect(self._navigate)
        # input → set input text and focus
        self._quick_panel.input_requested.connect(self._on_quick_input)
        # cmd → submit directly
        self._quick_panel.cmd_requested.connect(self._on_user_message)

        # ARIA signals → UI
        s.chat_response.connect(self._on_chat_response)
        s.chat_stream_chunk.connect(self._on_stream_chunk)
        s.chat_stream_done.connect(self._on_stream_done)
        s.typing_indicator.connect(self._chat_page.set_typing)
        s.status_update.connect(self._status_bar.set_status)
        s.terminal_output.connect(self._terminal_page.append_output)
        s.timeline_event.connect(self._timeline_page.add_event)
        s.warning_added.connect(self._warnings_page.add_warning)
        s.stt_started.connect(lambda: self._chat_page.set_stt_status("🔴 Recording…"))
        s.stt_result.connect(self._on_stt_result)
        s.stt_error.connect(lambda e: self._chat_page.set_stt_status(f"STT: {e}"))

        # Self-Mod
        s.selfmod_proposal.connect(self._on_selfmod_proposals)
        s.selfmod_applied.connect(self._on_selfmod_applied)
        s.selfmod_rolled_back.connect(self._on_selfmod_rolled_back)

        # Warnings badge on rail
        self._warnings_page.count_changed.connect(self._sidebar.set_warning_count)

        # Session loaded
        s.session_loaded.connect(self._on_session_loaded)

        # Self-Mod page buttons
        self._selfmod_page.approved.connect(self._on_proposal_approved)
        self._selfmod_page.rejected.connect(self._on_proposal_rejected)
        self._selfmod_page.rollback.connect(self._on_rollback)
        self._selfmod_page.analyze.connect(self._on_analyze_now)
        self._selfmod_page.file_uploaded.connect(self._on_file_uploaded)

        # Streaming
        self._stream_started = False
        s.chat_stream_chunk.connect(self._ensure_stream_started)

    # Boot
    def _boot(self):
        self._status_bar.set_status("Connecting to MongoDB…")
        db_ok = self._db.connect()
        if db_ok:
            self._status_bar.set_status("MongoDB connected.")
            self._signals.warning_added.emit("info", "MongoDB connected.")
        else:
            self._status_bar.set_status("MongoDB offline — history disabled.")
            self._signals.warning_added.emit("warning", "MongoDB unavailable.")

        self._selfmod = SelfModController(self._db, self._llm, self._signals)
        self._engine  = ChatEngine(
            db=self._db, llm_client=self._llm, signals=self._signals,
            selfmod_controller=self._selfmod, voice_engine=self._voice,
        )

        try:
            self._patterns_page.set_llm(self._llm)
            self._patterns_page._signals = self._signals
        except Exception: pass

        self._apply_selfmod_config()

        self._status_bar.set_status("Checking LLM…")
        llm_ok = self._llm.ping()
        self._status_bar.set_online(llm_ok)
        self._system_panel.set_llm_status(llm_ok)

        if llm_ok:
            self._status_bar.set_llm(CHAT_MODEL)
            self._status_bar.set_status("Ready")
            self._signals.warning_added.emit("info", f"LM Studio: {CHAT_MODEL}")
        else:
            self._status_bar.set_status("LLM offline")
            self._signals.warning_added.emit("warning", "LM Studio not reachable.")

        self._chat_page.set_suggestions(self._engine.get_suggestions("chat"))
        self._health.start()
        self._apply_page_tints("chat")

        last_session = self._db.get_last_session()
        if last_session:
            self._signals.session_loaded.emit(last_session)
            title = self._db.generate_session_title(last_session)
            self._chat_page.add_message("assistant",
                f"🔄 Resumed previous session — **{title}**\n\n"
                f"Type `/new` to start a fresh session, or `/sessions` to browse all sessions."
            )
        else:
            self._chat_page.add_message("assistant",
                "Hello! I'm **ARIA** — your local AI assistant.\n\n"
                "I can run commands, fetch & summarize sites using Fabric patterns, "
                "answer questions, and more — all running locally.\n\n"
                "Use the **Quick** panel on the right to jump to common actions, "
                "or type `/help` for all commands."
            )

    # Navigation
    @pyqtSlot(str)
    def _navigate(self, page: str):
        if page not in self._pages: return
        self._stack.setCurrentWidget(self._pages[page])
        # Show right column only on chat page
        self._right_col.setVisible(page == "chat")
        if page == "selfmod" and self._selfmod: self._refresh_selfmod_page()
        self._apply_page_tints(page)

    @pyqtSlot(str)
    def _apply_page_tints(self, page: str):
        theme = THEMES.get(self._current_theme, THEMES["cyber"])
        sidebar_key = f"sidebar_{page}"
        glass_key = f"glass_{page}"
        if sidebar_key in theme:
            self._sidebar.set_page_tint(theme[sidebar_key])
        if glass_key in theme:
            border = theme.get("border", "#13243a")
            self._quick_panel.set_page_tint(theme[glass_key], border)
            self._system_panel.set_page_tint(theme[glass_key], border)

    # Quick panel handlers
    @pyqtSlot(str)
    def _on_quick_pattern(self, pattern_name: str):
        # Put /pattern <name>  in the input and focus — user pastes text/URL.
        self._stack.setCurrentWidget(self._chat_page)
        self._right_col.setVisible(True)
        self._chat_page.set_input_text(f"/pattern {pattern_name} ")
        self._chat_page._input.setFocus()

    @pyqtSlot(str)
    def _on_quick_input(self, text: str):
        # Pre-fill the input field.
        self._stack.setCurrentWidget(self._chat_page)
        self._right_col.setVisible(True)
        self._chat_page.set_input_text(text)
        self._chat_page._input.setFocus()

    # Settings
    @pyqtSlot()
    def _open_settings(self):
        dlg = SettingsDialog(current_color=self._current_theme, parent=self)
        dlg.move(
            self.x() + (self.width()  - dlg.width())  // 2,
            self.y() + (self.height() - dlg.height()) // 2,
        )
        dlg.theme_changed.connect(self._apply_theme)
        dlg.exec_()

    @pyqtSlot(str)
    def _apply_theme(self, theme_name: str):
        self._current_theme = theme_name
        theme = THEMES.get(theme_name, THEMES["cyber"])
        QApplication.instance().setStyleSheet(build_stylesheet(theme))

    # User input
    @pyqtSlot(str)
    def _on_user_message(self, text: str):
        if not text.strip(): return
        self._chat_page.add_message("user", text)
        self._db.save_message(self._session_id, "user", text)
        self._db.save_last_session(self._session_id)
        self._history.append({"role": "user", "content": text})
        self._stream_started = False
        if self._engine: threading.Thread(
                target=self._engine.process,
                args=(text, self._session_id, self._history.copy()),
                daemon=True,
            ).start()

    @pyqtSlot(str)
    def _on_terminal_command(self, cmd: str):
        if self._engine: threading.Thread(
                target=self._engine._run_command,
                args=(cmd, self._session_id),
                daemon=True,
            ).start()

    # Streaming
    @pyqtSlot(str)
    def _ensure_stream_started(self, chunk: str):
        if not self._stream_started:
            self._chat_page.start_stream()
            self._stream_started = True

    @pyqtSlot(str)
    def _on_stream_chunk(self, chunk: str): self._chat_page.append_stream_chunk(chunk)

    @pyqtSlot()
    def _on_stream_done(self):
        self._chat_page.end_stream()
        self._stream_started = False

    @pyqtSlot(str, str)
    def _on_chat_response(self, role: str, text: str):
        if role == "assistant":
            stripped = text.strip()
            if not stripped or stripped.startswith("[LLM Error:"): return
            self._chat_page.add_message("assistant", text)
            self._db.save_message(self._session_id, "assistant", text)
            self._history.append({"role": "assistant", "content": text})
            if len(self._history) > 40: self._history = self._history[-40:]
            if len(self._history) == 2:
                first_user = self._history[0].get("content", "")
                title = first_user[:60] + ("..." if len(first_user) > 60 else "")
                self._db.save_session_title(self._session_id, title)

    # STT
    @pyqtSlot()
    def _on_mic_press(self): self._voice.record_and_transcribe(duration=5)

    @pyqtSlot(str)
    def _on_stt_result(self, text: str):
        self._chat_page.set_stt_status("")
        self._chat_page.set_input_text(text)
        self._on_user_message(text)

    # Voice
    @pyqtSlot(bool)
    def _on_voice_toggle(self, enabled: bool):
        if self._selfmod:
            try: self._selfmod.sandbox.config.apply("tts_enabled", enabled)
            except Exception: pass

    @pyqtSlot(bool)
    def _on_silent_toggle(self, enabled: bool):
        self._voice.set_silent_mode(enabled)

    # Self-Mod
    @pyqtSlot(list)
    def _on_selfmod_proposals(self, proposals: list):
        self._selfmod_page.add_proposal(proposals)
        self._signals.warning_added.emit("info",
            f"ARIA detected {len(proposals)} pattern(s). Check Self-Mod."
        )

    @pyqtSlot(str)
    def _on_proposal_approved(self, proposal_id: str):
        if not self._selfmod: return
        try:
            key, value, _ = self._selfmod.approve(proposal_id)
            self._apply_runtime_change(key, value)
            self._signals.warning_added.emit("info", f"Applied: {key} = {value}")
            self._refresh_selfmod_page()
        except Exception as e: self._signals.warning_added.emit("error", f"Approval failed: {e}")

    @pyqtSlot(str)
    def _on_proposal_rejected(self, proposal_id: str):
        if not self._selfmod: return
        try: self._selfmod.reject(proposal_id)
        except Exception as e: print(f"[Reject] {e}")

    @pyqtSlot(str)
    def _on_rollback(self, entry_id: str):
        if not self._selfmod: return
        try:
            key, old = self._selfmod.rollback(entry_id)
            self._apply_runtime_change(key, old)
            self._signals.warning_added.emit("info", f"Rolled back: {key}")
            self._refresh_selfmod_page()
        except Exception as e:
            self._signals.warning_added.emit("error", f"Rollback failed: {e}")

    @pyqtSlot(str, object)
    def _on_selfmod_applied(self, key: str, value):
        self._apply_runtime_change(key, value)

    @pyqtSlot(str)
    def _on_selfmod_rolled_back(self, _): self._refresh_selfmod_page()

    @pyqtSlot()
    def _on_analyze_now(self):
        if not self._selfmod: return
        self._status_bar.set_status("Analyzing patterns…")
        self._signals.chat_response.emit("assistant", "🔍 Running behavioral analysis…")
        def _run():
            proposals = self._selfmod.analyze_sync(self._session_id)
            if proposals:
                self._signals.selfmod_proposal.emit(proposals)
                self._signals.chat_response.emit("assistant",
                    f"✅ Found **{len(proposals)}** pattern(s). Check **Self-Mod** tab.")
            else:
                self._signals.chat_response.emit("assistant",
                    "No significant patterns yet. Keep chatting and check back.")
            self._signals.status_update.emit("Ready")
        threading.Thread(target=_run, daemon=True).start()

    @pyqtSlot(str)
    def _on_file_uploaded(self, content: str):
        if not self._selfmod: return
        self._status_bar.set_status("Analyzing uploaded conversation…")
        self._signals.chat_response.emit("assistant", "📄 Analyzing uploaded conversation file…")
        def _run():
            try:
                proposals = self._selfmod.analyze_from_file(content)
                if proposals:
                    self._signals.selfmod_proposal.emit(proposals)
                    self._signals.chat_response.emit("assistant",
                        f"✅ Found **{len(proposals)}** pattern(s) from file. Check **Self-Mod** tab.")
                else:
                    self._signals.chat_response.emit("assistant",
                        "No significant patterns found in the uploaded file. Try a longer conversation with more interactions.")
            except Exception as e:
                self._signals.chat_response.emit("assistant",
                    f"❌ Error analyzing file: {e}")
            self._signals.status_update.emit("Ready")
        threading.Thread(target=_run, daemon=True).start()

    @pyqtSlot(str)
    def _on_session_loaded(self, session_id: str):
        self._session_id = session_id
        self._history = []
        self._db.save_last_session(session_id)
        messages = self._db.get_messages(session_id)
        for msg in messages:
            self._history.append({"role": msg.get("role"), "content": msg.get("content")})
            self._chat_page.add_message(msg.get("role", "user"), msg.get("content", ""))

    def _apply_runtime_change(self, key: str, value):
        if key == "default_theme":
            self._apply_theme(str(value))
        elif key == "tts_enabled":
            if not value: self._voice.stop_speaking()
        elif key == "silent_mode":
            self._voice.set_silent_mode(bool(value))
            self._sidebar.apply_selfmod(voice_on=not bool(value), silent_on=bool(value))
        elif key == "suggestion_count":
            if self._engine:
                self._chat_page.set_suggestions(self._engine.get_suggestions("chat"))

    def _apply_selfmod_config(self):
        if not self._selfmod: return
        for key, value in self._selfmod.get_all().items():
            try: self._apply_runtime_change(key, value)
            except Exception as e: print(f"[Boot] {key}={value}: {e}")

    def _refresh_selfmod_page(self):
        if not self._selfmod: return
        self._selfmod_page.load_active_mods(self._selfmod.get_active_modifications())
        self._selfmod_page.load_ledger(self._selfmod.get_ledger())
        pending = self._selfmod.get_pending()
        if pending: self._selfmod_page.load_proposals(pending)

    def closeEvent(self, event):
        self._health.stop()
        if self._voice: self._voice.stop_speaking()
        self._db.save_last_session(self._session_id)
        event.accept()
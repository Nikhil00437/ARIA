import uuid, threading
from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, QApplication
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

class ARIAWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)
        # Core systems
        self._signals       = ARIASignals()
        self._db            = Database()
        self._llm           = LLMClient()
        self._session_id    = str(uuid.uuid4())
        self._history: list = []
        self._current_theme = DEFAULT_THEME
        # Self-Mod system
        self._selfmod: SelfModController = None   # initialized after DB connects
        # Voice
        self._voice = VoiceEngine(self._signals)
        # Chat engine (wired after selfmod)
        self._engine: ChatEngine = None
        # Health monitor
        self._health = HealthMonitor(self._signals)
        # Build UI
        self._build_ui()
        self._connect_signals()
        self._apply_theme(DEFAULT_THEME)
        # Boot sequence
        QTimer.singleShot(100, self._boot)
    # UI Construction
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        # Title bar
        self._title_bar = TitleBar(self)
        root.addWidget(self._title_bar)
        # Body: sidebar + page stack
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._sidebar = Sidebar()
        body.addWidget(self._sidebar)

        self._stack = QStackedWidget()

        self._chat_page     = ChatPage()
        self._terminal_page = TerminalPage()
        self._timeline_page = TimelinePage()
        self._warnings_page = WarningsPage()
        self._selfmod_page  = SelfModPage()

        self._pages = {
            "chat":     self._chat_page,
            "terminal": self._terminal_page,
            "timeline": self._timeline_page,
            "warnings": self._warnings_page,
            "selfmod":  self._selfmod_page,
        }
        for page in self._pages.values(): self._stack.addWidget(page)

        body.addWidget(self._stack, 1)

        body_widget = QWidget()
        body_widget.setLayout(body)
        root.addWidget(body_widget, 1)
        # Status bar
        self._status_bar = StatusBar()
        root.addWidget(self._status_bar)
    # Signal Connections
    def _connect_signals(self):
        s = self._signals
        # Navigation
        self._sidebar.nav_clicked.connect(self._navigate)
        self._sidebar.theme_changed.connect(self._apply_theme)
        self._sidebar.voice_toggled.connect(self._on_voice_toggle)
        self._sidebar.silent_toggled.connect(self._on_silent_toggle)
        self._sidebar.mic_pressed.connect(self._on_mic_press)
        # Chat page
        self._chat_page.message_submitted.connect(self._on_user_message)
        self._chat_page.suggestion_clicked.connect(self._on_user_message)
        self._terminal_page.command_submitted.connect(self._on_terminal_command)
        # ARIA signals → UI
        s.chat_response.connect(self._on_chat_response)
        s.chat_stream_chunk.connect(self._chat_page._stream_chunk)
        s.chat_stream_done.connect(self._chat_page._end_stream_bubble)
        s.typing_indicator.connect(self._chat_page.set_typing)
        s.status_update.connect(self._status_bar.set_status)
        s.terminal_output.connect(self._terminal_page.append_output)
        s.timeline_event.connect(self._timeline_page.add_event)
        s.warning_added.connect(self._warnings_page.add_warning)
        s.stt_started.connect(lambda: self._chat_page.set_stt_status("🔴 Recording..."))
        s.stt_result.connect(self._on_stt_result)
        s.stt_error.connect(lambda e: self._chat_page.set_stt_status(f"STT: {e}"))
        s.theme_changed.connect(self._apply_theme)
        # Self-Mod signals
        s.selfmod_proposal.connect(self._on_selfmod_proposals)
        s.selfmod_applied.connect(self._on_selfmod_applied)
        s.selfmod_rolled_back.connect(self._on_selfmod_rolled_back)
        # Warnings count → sidebar badge
        self._warnings_page.count_changed.connect(self._sidebar.set_warning_count)
        # Self-mod page actions
        self._selfmod_page.approved.connect(self._on_proposal_approved)
        self._selfmod_page.rejected.connect(self._on_proposal_rejected)
        self._selfmod_page.rollback.connect(self._on_rollback)
        self._selfmod_page.analyze.connect(self._on_analyze_now)
        # Session management
        s.session_loaded.connect(self._on_session_loaded)
    # Boot Sequence
    def _boot(self):
        self._status_bar.set_status("Connecting to MongoDB...")

        db_ok = self._db.connect()
        if db_ok:
            self._status_bar.set_status("MongoDB connected.")
            self._signals.warning_added.emit("info", "MongoDB connected successfully.")
        else:
            self._status_bar.set_status("MongoDB offline — history disabled.")
            self._signals.warning_added.emit("warning", "MongoDB unavailable. Session history disabled.")
        # Init Self-Mod (works even without DB — degrades gracefully)
        self._selfmod = SelfModController(self._db, self._llm, self._signals)
        # Init Chat Engine
        self._engine = ChatEngine(
            db=self._db,
            llm_client=self._llm,
            signals=self._signals,
            selfmod_controller=self._selfmod,
            voice_engine=self._voice,
        )
        # Apply any selfmod-persisted config
        self._apply_selfmod_config()
        # Check LLM connectivity
        self._status_bar.set_status("Checking LLM...")
        llm_ok = self._llm.ping()
        self._status_bar.set_online(llm_ok)
        if llm_ok:
            self._status_bar.set_llm(CHAT_MODEL)
            self._status_bar.set_status("Ready")
            self._signals.warning_added.emit("info", f"LM Studio connected: {CHAT_MODEL}")
        else:
            self._status_bar.set_status("LLM offline — using fallback mode")
            self._signals.warning_added.emit("warning", "LM Studio not reachable. Start LM Studio and load a model.")
        # Show initial suggestions
        self._chat_page.set_suggestions(self._engine.get_suggestions("chat"))
        # Start health monitor
        self._health.start()
        # Greet user
        self._signals.chat_response.emit("assistant",
            "Hello! I'm **ARIA** — your local AI assistant.\n\n"
            "I can run commands, search the web, answer questions, generate images, and more — "
            "all running locally on your machine.\n\n"
            "Type `/help` for a list of commands, or just ask me anything."
        )
    # Navigation
    @pyqtSlot(str)
    def _navigate(self, page: str):
        if page in self._pages:
            self._stack.setCurrentWidget(self._pages[page])
            # Refresh selfmod page when navigated to
            if page == "selfmod" and self._selfmod: self._refresh_selfmod_page()
    # User Input
    @pyqtSlot(str)
    def _on_user_message(self, text: str):
        if not text.strip(): return
        self._chat_page.add_message("user", text)
        self._db.save_message(self._session_id, "user", text)
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
    # Session Management
    @pyqtSlot(str)
    def _on_session_loaded(self, session_id: str):
        self._session_id = session_id
        self._history = self._db.get_messages(session_id, limit=50)
        self._chat_page.clear_messages()
        for msg in self._history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            self._chat_page.add_message(role, content)
        self._signals.warning_added.emit("info", f"Loaded session {session_id[:8]}...")
    # Chat Response
    @pyqtSlot(str, str)
    def _on_chat_response(self, role: str, content: str):
        if role == "assistant":
            self._chat_page.add_message(role, content)

    @pyqtSlot(bool)
    def _on_typing_indicator(self, active: bool):
        self._chat_page.set_typing(active)
    # STT
    @pyqtSlot()
    def _on_mic_press(self): self._voice.record_and_transcribe(duration=5)
    
    @pyqtSlot(str)
    def _on_stt_result(self, text: str):
        self._chat_page.set_stt_status("")
        self._chat_page.set_input_text(text)
        # Auto-submit
        self._on_user_message(text)
    # Voice Toggles
    @pyqtSlot(bool)
    def _on_voice_toggle(self, enabled: bool):
        # TTS enable/disable — update config via selfmod if possible
        if self._selfmod:
            try:
                cfg = self._selfmod.sandbox.config
                cfg.apply("tts_enabled", enabled)
            except Exception: pass

    @pyqtSlot(bool)
    def _on_silent_toggle(self, enabled: bool):
        self._voice.set_silent_mode(enabled)
        if self._selfmod:
            try:
                cfg = self._selfmod.sandbox.config
                cfg.apply("silent_mode", enabled)
            except Exception: pass
    # Theme
    @pyqtSlot(str)
    def _apply_theme(self, theme_name: str):
        self._current_theme = theme_name
        theme = THEMES.get(theme_name, THEMES[DEFAULT_THEME])
        QApplication.instance().setStyleSheet(build_stylesheet(theme))
    # Self-Mod Slots
    @pyqtSlot(list)
    def _on_selfmod_proposals(self, proposals: list):
        self._selfmod_page.add_proposal(proposals)
        # Badge notification: switch tab indicator
        self._signals.warning_added.emit("info",
            f"ARIA detected {len(proposals)} behavioral pattern(s). Check Self-Mod panel."
        )

    @pyqtSlot(str)
    def _on_proposal_approved(self, proposal_id: str):
        if not self._selfmod: return
        try:
            key, value, ledger_entry = self._selfmod.approve(proposal_id)
            self._apply_runtime_change(key, value)
            self._signals.warning_added.emit("info", f"Self-Mod applied: {key} = {value}")
            self._refresh_selfmod_page()
        except (KeyError, ValueError) as e: self._signals.warning_added.emit("error", f"Approval failed: {e}")

    @pyqtSlot(str)
    def _on_proposal_rejected(self, proposal_id: str):
        if not self._selfmod: return
        try: self._selfmod.reject(proposal_id)
        except KeyError as e: print(f"[MainWindow] Reject error: {e}")

    @pyqtSlot(str)
    def _on_rollback(self, entry_id: str):
        if not self._selfmod: return
        try:
            key, old_value = self._selfmod.rollback(entry_id)
            self._apply_runtime_change(key, old_value)
            self._signals.warning_added.emit("info", f"Rolled back: {key} → {old_value}")
            self._refresh_selfmod_page()
        except (KeyError, ValueError) as e: self._signals.warning_added.emit("error", f"Rollback failed: {e}")

    @pyqtSlot(str, object)
    def _on_selfmod_applied(self, key: str, value): self._apply_runtime_change(key, value)

    @pyqtSlot(str)
    def _on_selfmod_rolled_back(self, entry_id: str): self._refresh_selfmod_page()

    @pyqtSlot()
    def _on_analyze_now(self):
        if not self._selfmod: return
        self._status_bar.set_status("Analyzing behavioral patterns...")
        self._signals.chat_response.emit("assistant", "🔍 Running behavioral analysis on your session history...")
        def _run():
            proposals = self._selfmod.analyze_sync(self._session_id)
            if proposals:
                self._signals.selfmod_proposal.emit(proposals)
                self._signals.chat_response.emit("assistant",
                    f"✅ Found **{len(proposals)}** behavioral pattern(s). Check the **Self-Mod** tab to approve or reject."
                )
            else:
                self._signals.chat_response.emit("assistant",
                    "No significant patterns detected yet. Keep using ARIA and I'll analyze again as we interact more."
                )
            self._signals.status_update.emit("Ready")
        threading.Thread(target=_run, daemon=True).start()
    # Runtime Config Application
    def _apply_runtime_change(self, key: str, value):
        if key == "default_theme": self._apply_theme(str(value))
        elif key == "tts_enabled": 
            if not value: self._voice.stop_speaking()
        elif key == "silent_mode":
            self._voice.set_silent_mode(bool(value))
            self._sidebar.apply_selfmod(
                voice_on=not bool(value),
                silent_on=bool(value),
            )
        elif key == "suggestion_count":
            if self._engine: self._chat_page.set_suggestions(self._engine.get_suggestions("chat"))

    def _apply_selfmod_config(self):
        if not self._selfmod: return
        config = self._selfmod.get_all()
        for key, value in config.items():
            try: self._apply_runtime_change(key, value)
            except Exception as e: print(f"[Boot] Failed to apply {key}={value}: {e}")
    # Self-Mod Page Refresh
    def _refresh_selfmod_page(self):
        if not self._selfmod: return
        # Active mods
        active = self._selfmod.get_active_modifications()
        self._selfmod_page.load_active_mods(active)
        # Full ledger
        ledger = self._selfmod.get_ledger()
        self._selfmod_page.load_ledger(ledger)
        # Pending proposals
        pending = self._selfmod.get_pending()
        if pending: self._selfmod_page.load_proposals(pending)
    # Close
    def closeEvent(self, event):
        self._health.stop()
        if self._voice: self._voice.stop_speaking()
        event.accept()
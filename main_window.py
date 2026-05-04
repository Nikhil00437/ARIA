# main_window.py — Lazy-loaded pages with lifecycle management

import uuid, threading, ctypes
from ctypes import wintypes
from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, QApplication, QFrame
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QColor, QPainter, QLinearGradient
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
from widgets import StatusBar, ToastManager, CommandPalette, ConfirmDialog, KeyboardShortcutsHelp, ErrorBanner
from quick_panel import QuickPanel, SystemPanel
from settings_dialog import SettingsDialog

# Windows DWM blur for acrylic glass effect
try:
    from PyQt5.QtWinExtras import QtWin
    HAS_WINEXTRAS = True
except ImportError:
    HAS_WINEXTRAS = False

def _enable_acrylic(hwnd):
    """Enable Windows 10/11 acrylic blur on a window using undocumented API."""
    try:
        ACCENT_ENABLE_BLURBEHIND = 3
        ACCENT_ENABLE_ACRYLICBLURBEHIND = 4

        class ACCENTPOLICY(ctypes.Structure):
            _fields_ = [
                ("AccentState", ctypes.c_int),
                ("AccentFlags", ctypes.c_uint),
                ("GradientColor", ctypes.c_uint),
                ("AnimationId", ctypes.c_uint),
            ]

        class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
            _fields_ = [
                ("Attribute", ctypes.c_int),
                ("Data", ctypes.POINTER(ctypes.c_int)),
                ("SizeOfData", ctypes.c_size_t),
            ]

        user32 = ctypes.windll.user32
        SetWindowCompositionAttribute = user32.SetWindowCompositionAttribute
        SetWindowCompositionAttribute.restype = ctypes.c_bool
        SetWindowCompositionAttribute.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(WINDOWCOMPOSITIONATTRIBDATA),
        ]

        accent = ACCENTPOLICY()
        accent.AccentState = ACCENT_ENABLE_ACRYLICBLURBEHIND
        accent.AccentFlags = 2
        accent.GradientColor = 0x01000000  # Transparent so CSS can control tint

        accent_data = ctypes.pointer(ctypes.c_int(
            accent.AccentState | (accent.AccentFlags << 16) | (accent.GradientColor << 24)
        ))

        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = 19  # WCA_ACCENT_POLICY
        data.Data = ctypes.cast(accent_data, ctypes.POINTER(ctypes.c_int))
        data.SizeOfData = ctypes.sizeof(ACCENTPOLICY)

        SetWindowCompositionAttribute(int(hwnd), data)
        return True
    except Exception:
        return False

def _enable_blurbehind(hwnd):
    """Fallback: simple DWM blur behind."""
    try:
        class DWM_BLURBEHIND(ctypes.Structure):
            _fields_ = [
                ("dwFlags", ctypes.c_ulong),
                ("fEnable", ctypes.c_bool),
                ("hRgnBlur", ctypes.c_void_p),
                ("fTransitionOnMaximized", ctypes.c_bool),
            ]

        dwmapi = ctypes.windll.dwmapi
        DwmEnableBlurBehindWindow = dwmapi.DwmEnableBlurBehindWindow

        bb = DWM_BLURBEHIND()
        bb.dwFlags = 1  # DWM_BB_ENABLE
        bb.fEnable = True
        bb.hRgnBlur = 0
        bb.fTransitionOnMaximized = False

        DwmEnableBlurBehindWindow(int(hwnd), ctypes.byref(bb))
        return True
    except Exception:
        return False


class ARIAWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
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
        self._msg_load_offset = 0
        self._msg_batch_size = 30

        # Lazy page state
        self._page_loaded: dict[str, bool] = {
            "chat": True,
            "terminal": False,
            "timeline": False,
            "warnings": False,
            "selfmod": False,
            "patterns": False,
        }
        self._active_page = "chat"
        self._warning_buffer: list = []

        self._build_ui()
        self._connect_signals()
        self._apply_theme(DEFAULT_THEME)
        self._install_shortcuts()
        self._enable_window_blur()
        QTimer.singleShot(50, self._boot)

    def paintEvent(self, event):
        """Paint a deep dark gradient behind all glass layers."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, QColor(8, 12, 28, 250))
        grad.setColorAt(0.3, QColor(14, 16, 38, 250))
        grad.setColorAt(0.7, QColor(22, 18, 42, 250))
        grad.setColorAt(1.0, QColor(12, 20, 36, 250))
        painter.fillRect(self.rect(), grad)
        painter.end()

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

        # Eager-load chat page only
        self._chat_page = ChatPage()
        self._stack.addWidget(self._chat_page)

        # Placeholder for unloaded pages
        self._page_widgets: dict[str, QWidget] = {
            "chat": self._chat_page,
        }

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
        
        # Toast notification manager
        self._toast_manager = ToastManager(self)
        self._toast_manager.hide()
        
        # Command palette
        self._command_palette = CommandPalette(self)
        self._command_palette.command_selected.connect(self._on_command_palette_action)
        self._command_palette.hide()
        
        # Confirmation dialog (created on demand)
        self._confirm_dialog = None
        
        # Keyboard shortcuts help
        self._shortcuts_help = KeyboardShortcutsHelp(self)
        self._shortcuts_help.hide()

    # Signals
    def _connect_signals(self):
        s = self._signals

        # Sidebar nav
        self._sidebar.nav_clicked.connect(self._navigate)
        self._sidebar.voice_toggled.connect(self._on_voice_toggle)
        self._sidebar.silent_toggled.connect(self._on_silent_toggle)
        self._sidebar.mic_pressed.connect(self._on_mic_press)
        self._sidebar.new_session.connect(self._on_new_session)

        # Settings button in title bar
        self._title_bar.settings_requested.connect(self._open_settings)

        # Chat input
        self._chat_page.message_submitted.connect(self._on_user_message)
        self._chat_page.suggestion_clicked.connect(self._on_user_message)
        self._chat_page.load_more.connect(self._load_messages_batch)

        # Quick panel wiring
        self._quick_panel.pattern_requested.connect(self._on_quick_pattern)
        self._quick_panel.nav_requested.connect(self._navigate)
        self._quick_panel.input_requested.connect(self._on_quick_input)
        self._quick_panel.cmd_requested.connect(self._on_user_message)

        # ARIA signals → UI
        s.chat_response.connect(self._on_chat_response)
        s.chat_stream_chunk.connect(self._on_stream_chunk)
        s.chat_stream_done.connect(self._on_stream_done)
        s.typing_indicator.connect(self._chat_page.set_typing)
        s.status_update.connect(self._status_bar.set_status)
        s.stt_started.connect(lambda: self._chat_page.set_stt_status("🔴 Recording…"))
        s.stt_result.connect(self._on_stt_result)
        s.stt_error.connect(lambda e: self._chat_page.set_stt_status(f"STT: {e}"))

        # Warnings — buffer before page loads
        s.warning_added.connect(self._on_warning_added)

        # Self-Mod
        s.selfmod_proposal.connect(self._on_selfmod_proposals)
        s.selfmod_applied.connect(self._on_selfmod_applied)
        s.selfmod_rolled_back.connect(self._on_selfmod_rolled_back)

        # Session loaded
        s.session_loaded.connect(self._on_session_loaded)

        # System
        s.llm_status.connect(self._system_panel.set_llm_status)
        s.status_update.connect(self._on_boot_complete)
        
        # Warnings also show as toasts
        s.warning_added.connect(self._on_warning_toast)

        # Streaming
        self._stream_started = False
        s.chat_stream_chunk.connect(self._ensure_stream_started)

    def _enable_window_blur(self):
        """Enable translucent background for the frosted glass effect.
        Uses Windows acrylic blur when available, falls back to DWM blur."""
        self.setAttribute(Qt.WA_TranslucentBackground)
        hwnd = int(self.winId())
        if not _enable_acrylic(hwnd):
            _enable_blurbehind(hwnd)

    # Keyboard Shortcuts
    def _install_shortcuts(self):
        from PyQt5.QtGui import QKeySequence
        from PyQt5.QtWidgets import QShortcut

        # Alt+1 through Alt+5 for page navigation
        pages = ["chat", "terminal", "patterns", "warnings", "selfmod"]
        for i, page in enumerate(pages, 1):
            sc = QShortcut(QKeySequence(f"Alt+{i}"), self)
            sc.activated.connect(lambda p=page: self._navigate(p))

        # Ctrl+N for new session
        sc_new = QShortcut(QKeySequence("Ctrl+N"), self)
        sc_new.activated.connect(self._on_new_session)

        # Ctrl+W to close
        sc_close = QShortcut(QKeySequence("Ctrl+W"), self)
        sc_close.activated.connect(self.close)

        # Escape to minimize
        sc_min = QShortcut(QKeySequence("Escape"), self)
        sc_min.activated.connect(self.showMinimized)
        
        # Ctrl+K for command palette
        sc_palette = QShortcut(QKeySequence("Ctrl+K"), self)
        sc_palette.activated.connect(self._show_command_palette)
        
        # Ctrl+/ for keyboard shortcuts help
        sc_help = QShortcut(QKeySequence("Ctrl+/"), self)
        sc_help.activated.connect(self._show_shortcuts_help)

    # Boot
    def _boot(self):
        self._status_bar.set_status("Initializing…")
        threading.Thread(target=self._boot_async, daemon=True).start()

    def _boot_async(self):
        # MongoDB
        self._signals.status_update.emit("Connecting to MongoDB…")
        db_ok = self._db.connect()
        if db_ok:
            self._signals.status_update.emit("MongoDB connected.")
            self._signals.warning_added.emit("info", "MongoDB connected.")
        else:
            self._signals.status_update.emit("MongoDB offline — history disabled.")
            self._signals.warning_added.emit("warning", "MongoDB unavailable.")

        self._selfmod = SelfModController(self._db, self._llm, self._signals)
        self._engine  = ChatEngine(
            db=self._db, llm_client=self._llm, signals=self._signals,
            selfmod_controller=self._selfmod, voice_engine=self._voice,
        )

        self._apply_selfmod_config()

        # LLM check
        self._signals.status_update.emit("Checking LLM…")
        llm_ok = self._llm.ping()
        self._signals.llm_status.emit(llm_ok)

        if llm_ok:
            self._signals.status_update.emit("Ready")
            self._signals.warning_added.emit("info", f"LM Studio: {CHAT_MODEL}")
        else:
            self._signals.status_update.emit("LLM offline")
            self._signals.warning_added.emit("warning", "LM Studio not reachable.")

        self._signals.status_update.emit("Ready")
        self._chat_page.set_suggestions(self._engine.get_suggestions("chat"))
        self._apply_page_tints("chat")

        # Session resume
        last_session = self._db.get_last_session()
        if last_session:
            self._signals.session_loaded.emit(last_session)
            title = self._db.generate_session_title(last_session)
            self._signals.chat_response.emit("assistant",
                f"🔄 Resumed previous session — **{title}**\n\n"
                f"Type `/new` to start a fresh session, or `/sessions` to browse all sessions."
            )
        else:
            self._signals.chat_response.emit("assistant",
                "Hello! I'm **ARIA** — your local AI assistant.\n\n"
                "I can run commands, fetch & summarize sites using Fabric patterns, "
                "answer questions, and more — all running locally.\n\n"
                "Use the **Quick** panel on the right to jump to common actions, "
                "or type `/help` for all commands."
            )

        # Notify main thread that boot is complete
        self._signals.status_update.emit("boot_complete")

    # Lazy page loading
    def _ensure_page_loaded(self, page: str):
        if self._page_loaded.get(page, False):
            return

        factory = {
            "terminal": self._load_terminal_page,
            "timeline": self._load_timeline_page,
            "warnings": self._load_warnings_page,
            "selfmod":  self._load_selfmod_page,
            "patterns": self._load_patterns_page,
        }
        loader = factory.get(page)
        if loader:
            loader()
            self._page_loaded[page] = True

    def _load_terminal_page(self):
        page = TerminalPage()
        page.command_submitted.connect(self._on_terminal_command)
        self._stack.addWidget(page)
        self._page_widgets["terminal"] = page
        self._signals.terminal_output.connect(page.append_output)

    def _load_timeline_page(self):
        page = TimelinePage()
        self._stack.addWidget(page)
        self._page_widgets["timeline"] = page
        self._signals.timeline_event.connect(page.add_event)

    def _load_warnings_page(self):
        page = WarningsPage()
        self._stack.addWidget(page)
        self._page_widgets["warnings"] = page
        self._signals.warning_added.connect(page.add_warning)
        page.count_changed.connect(self._sidebar.set_warning_count)
        # Replay buffered warnings
        for severity, message in self._warning_buffer:
            page.add_warning(severity, message)
        self._warning_buffer.clear()

    def _load_selfmod_page(self):
        page = SelfModPage()
        self._stack.addWidget(page)
        self._page_widgets["selfmod"] = page
        page.approved.connect(self._on_proposal_approved)
        page.rejected.connect(self._on_proposal_rejected)
        page.rollback.connect(self._on_rollback)
        page.analyze.connect(self._on_analyze_now)
        page.file_uploaded.connect(self._on_file_uploaded)

    def _load_patterns_page(self):
        try:
            from patterns_page import PatternsPage
            page = PatternsPage()
            page.set_llm(self._llm)
            page._signals = self._signals
        except ImportError:
            page = QWidget()
        self._stack.addWidget(page)
        self._page_widgets["patterns"] = page

    # Navigation
    @pyqtSlot(str)
    def _navigate(self, page: str):
        if page not in self._page_loaded:
            return

        # Pause the old page
        self._pause_page(self._active_page)

        # Load the new page if needed
        self._ensure_page_loaded(page)

        if page not in self._page_widgets:
            return

        self._stack.setCurrentWidget(self._page_widgets[page])
        self._right_col.setVisible(page == "chat")
        self._system_panel.set_visible(page == "chat")

        # Resume the new page
        self._resume_page(page)

        if page == "selfmod" and self._selfmod:
            self._refresh_selfmod_page()
        self._apply_page_tints(page)
        self._active_page = page

    def _pause_page(self, page: str):
        pass

    def _resume_page(self, page: str):
        pass

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
        self._stack.setCurrentWidget(self._chat_page)
        self._right_col.setVisible(True)
        self._chat_page.set_input_text(f"/pattern {pattern_name} ")
        self._chat_page._input.setFocus()

    @pyqtSlot(str)
    def _on_quick_input(self, text: str):
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
        if role == "user":
            self._chat_page.add_message("user", text)
            return
        if role == "assistant":
            stripped = text.strip()
            if not stripped or stripped.startswith("[LLM Error:"): return
            self._chat_page.add_message("assistant", text)
            if self._db.ok:
                self._db.save_message(self._session_id, "assistant", text)
            self._history.append({"role": "assistant", "content": text})
            if len(self._history) > 40: self._history = self._history[-40:]
            self._sidebar.set_session_msg_count(len(self._history))
            if len(self._history) == 2:
                first_user = self._history[0].get("content", "")
                title = first_user[:60] + ("..." if len(first_user) > 60 else "")
                if self._db.ok:
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
        if "selfmod" in self._page_widgets:
            self._page_widgets["selfmod"].add_proposal(proposals)
        self._sidebar.set_proposal_count(len(proposals))
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

    # Boot complete - start health monitor in main thread
    @pyqtSlot(str)
    def _on_boot_complete(self, status: str):
        if status == "boot_complete":
            self._health.start()

    # Session loaded
    @pyqtSlot(str)
    def _on_session_loaded(self, session_id: str):
        self._session_id = session_id
        self._history = []
        self._msg_load_offset = 0
        if self._db.ok:
            self._db.save_last_session(session_id)
        self._load_messages_batch()

    # New session
    def _on_new_session(self):
        # Show confirmation if there are messages in the current session
        if self._history:
            self._show_confirm_dialog(
                title="Start New Session?",
                message="This will clear the current conversation. Are you sure you want to start fresh?",
                confirm_text="Start New",
                confirm_style="warning",
                on_confirm=self._do_new_session
            )
        else:
            self._do_new_session()
    
    def _do_new_session(self):
        """Actually perform the new session creation."""
        self._session_id = str(uuid.uuid4())
        self._history = []
        self._msg_load_offset = 0
        self._stream_started = False
        self._chat_page.clear_messages()
        self._sidebar.set_session_msg_count(0)
        self._signals.chat_response.emit("assistant",
            "✨ New session started. What can I help with?"
        )
        self._toast_manager.info("New session started")
    
    def _show_confirm_dialog(self, title: str, message: str, confirm_text: str = "Confirm", 
                            cancel_text: str = "Cancel", confirm_style: str = "danger",
                            on_confirm=None):
        """Show a confirmation dialog."""
        dialog = ConfirmDialog(title, message, confirm_text, cancel_text, confirm_style, self)
        
        def handle_result(confirmed: bool):
            if confirmed and on_confirm:
                on_confirm()
        
        dialog.confirmed.connect(handle_result)
        
        # Position at center of window
        center_x = self.x() + self.width() // 2
        center_y = self.y() + self.height() // 2
        dialog.show_at(center_x, center_y)

    # Warnings — buffer before page loads, forward after
    def _on_warning_added(self, severity: str, message: str):
        page = self._page_widgets.get("warnings")
        if page is not None:
            page.add_warning(severity, message)
        else:
            self._warning_buffer.append((severity, message))
        
        # Also show as toast notification
        self._on_warning_toast(severity, message)
    
    def _on_warning_toast(self, severity: str, message: str):
        """Show warning as toast notification."""
        toast_type = "info"
        if severity == "warning":
            toast_type = "warning"
        elif severity == "error":
            toast_type = "error"
        elif severity == "success":
            toast_type = "success"
        
        # Truncate long messages for toast
        display_msg = message[:100] + "..." if len(message) > 100 else message
        self._toast_manager.show_toast(display_msg, toast_type, 3000)

    def _load_messages_batch(self):
        if not self._db.ok: return
        threading.Thread(target=self._load_messages_async, daemon=True).start()

    def _load_messages_async(self):
        messages = self._db.get_messages(
            self._session_id, limit=self._msg_batch_size, skip=self._msg_load_offset
        )
        self._msg_load_offset += len(messages)
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            self._history.append({"role": role, "content": content})
            # Add directly to UI — don't route through chat_response
            # to avoid double-appending to history and saving to DB again
            self._chat_page.add_message(role, content)
        self._sidebar.set_session_msg_count(len(self._history))
        self._chat_page.set_loading_older_done()

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
        page = self._page_widgets.get("selfmod")
        if not page: return
        page.load_active_mods(self._selfmod.get_active_modifications())
        page.load_ledger(self._selfmod.get_ledger())
        pending = self._selfmod.get_pending()
        if pending: page.load_proposals(pending)

    def closeEvent(self, event):
        self._health.stop()
        if self._voice: self._voice.stop_speaking()
        self._db.save_last_session(self._session_id)
        event.accept()
    
    # Command Palette
    def _show_command_palette(self):
        """Show the command palette at cursor position."""
        from PyQt5.QtGui import QCursor
        cursor = QCursor.pos()
        self._command_palette.show_at(cursor.x(), cursor.y())
    
    def _show_shortcuts_help(self):
        """Show keyboard shortcuts help dialog."""
        center_x = self.x() + self.width() // 2
        center_y = self.y() + self.height() // 2
        self._shortcuts_help.show_at(center_x, center_y)
    
    def _on_command_palette_action(self, command_id: str):
        """Handle command palette action."""
        actions = {
            "new_session": self._on_new_session,
            "settings": self._open_settings,
            "toggle_voice": lambda: self._sidebar.voice_toggled.emit(not self._voice._tts_engine),
            "toggle_silent": lambda: self._on_silent_toggle(True),
            "goto_chat": lambda: self._navigate("chat"),
            "goto_terminal": lambda: self._navigate("terminal"),
            "goto_patterns": lambda: self._navigate("patterns"),
            "goto_warnings": lambda: self._navigate("warnings"),
            "goto_selfmod": lambda: self._navigate("selfmod"),
            "run_selfmod": self._on_analyze_now,
            "show_context": lambda: self._on_user_message("/context"),
            "show_sessions": lambda: self._on_user_message("/sessions"),
            "clear_chat": lambda: self._show_confirm_dialog(
                title="Clear Chat?",
                message="This will delete all messages in the current conversation.",
                confirm_text="Clear Chat",
                confirm_style="danger",
                on_confirm=self._do_new_session
            ),
            "show_shortcuts": self._show_shortcuts_help,
        }
        
        action = actions.get(command_id)
        if action:
            action()
            self._toast_manager.success(f"Executed: {command_id}")

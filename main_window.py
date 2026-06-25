# main_window.py — Lazy-loaded pages with lifecycle management

import uuid, threading, ctypes, json
from ctypes import wintypes
from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, QApplication, QFrame
from PyQt5.QtCore import Qt, QTimer, QSettings, QMutex, pyqtSlot
from typing import Optional
from PyQt5.QtGui import QColor, QPainter, QLinearGradient
from logger import get_logger
from constants import DEFAULT_THEME, CHAT_MODEL, THEMES
from signals import ARIASignals, HealthMonitor

logger = get_logger("main_window")


def _qcolor(hex_str: str, alpha: int = 255):
    """Helper: build a QColor from a hex string with a given alpha."""
    from PyQt5.QtGui import QColor
    c = QColor(hex_str)
    c.setAlpha(alpha)
    return c


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
from widgets import StatusBar, ToastManager, CommandPalette, ConfirmDialog, KeyboardShortcutsHelp
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
    """Main application window with lazy-loaded pages and lifecycle management."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setMinimumSize(1100, 700)
        self.resize(1320, 820)

        # Shared state (protected by _mutex where accessed across threads)
        self._mutex: QMutex = QMutex()
        self._signals: ARIASignals = ARIASignals()
        self._db: Database = Database()
        self._llm: LLMClient = LLMClient()
        self._session_id: str = str(uuid.uuid4())
        self._history: list[dict[str, str]] = []
        self._current_theme: str = DEFAULT_THEME
        self._selfmod: Optional[SelfModController] = None
        self._voice: VoiceEngine = VoiceEngine(self._signals)
        self._engine: Optional[ChatEngine] = None
        self._health: HealthMonitor = HealthMonitor(self._signals)
        self._stream_started: bool = False
        self._stream_completed: bool = False
        self._stream_completed_text: str = ""
        self._msg_load_offset: int = 0
        self._msg_batch_size: int = 30

        # Lazy page state
        self._page_loaded: dict[str, bool] = {
            "chat": True,
            "terminal": False,
            "timeline": False,
            "warnings": False,
            "agent": False,
            "selfmod": False,
            "patterns": False,
        }
        self._active_page: str = "chat"
        self._warning_buffer: list[tuple[str, str]] = []
        self._settings: QSettings = QSettings("ARIA", "ARIA Local")

        # Restore window geometry from previous session
        saved_geo = self._settings.value("window/geometry")
        saved_state = self._settings.value("window/state")
        if saved_geo is not None:
            self.restoreGeometry(saved_geo)
        if saved_state is not None:
            self.restoreState(saved_state)

        self._build_ui()
        self._connect_signals()
        self._apply_theme(self._settings.value("app/theme", DEFAULT_THEME, str))
        self._install_shortcuts()
        self._enable_window_blur()
        QTimer.singleShot(50, self._boot)

    def paintEvent(self, event) -> None:
        """Paint a subtle gradient backdrop sourced from the active theme.

        All four gradient stops derive from theme tokens so switching theme
        changes the window background too. Alpha is held at 210 so the
        Windows acrylic blur remains visible behind the gradient.
        """
        from constants import THEMES as _THEMES, DEFAULT_THEME as _DT
        t = _THEMES.get(self._current_theme, _THEMES.get(_DT, {}))
        bg = t.get("bg", "#0E0F13")
        bg2 = t.get("bg2", "#16181D")
        bg3 = t.get("bg3", "#1D1F26")
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, _qcolor(bg, 210))
        grad.setColorAt(0.3, _qcolor(bg2, 210))
        grad.setColorAt(0.7, _qcolor(bg3, 210))
        grad.setColorAt(1.0, _qcolor(bg, 210))
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

        # Top Horizontal Dock Navigation
        self._sidebar = Sidebar()
        root.addWidget(self._sidebar)

        # Body: content + right column (no sidebar rail in body)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

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

        # Wire the brain widget (Phase 9) to the existing self-mod + nav signals.
        bw = getattr(self._chat_page, "brain_widget", None)
        if bw is not None:
            bw.analyze_requested.connect(self._on_analyze_now)
            bw.review_requested.connect(lambda: self._navigate("selfmod"))
            bw.cancel_preview_requested.connect(self._on_selfmod_cancel_preview)

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

        # Title bar buttons
        self._title_bar.settings_requested.connect(self._open_settings)
        self._title_bar.shortcuts_requested.connect(self._show_shortcuts_help)
        self._title_bar.export_requested.connect(self._export_chat)

        # Chat input
        self._chat_page.message_submitted.connect(self._on_user_message)
        self._chat_page.suggestion_clicked.connect(self._on_user_message)
        self._chat_page.reaction_clicked.connect(self._on_reaction)
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
        # Phase 9: brain signals
        s.selfmod_insights_changed.connect(self._on_selfmod_insights_changed)
        s.selfmod_badge_changed.connect(self._on_selfmod_badge_changed)

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

        # Alt+1 through Alt+6 for page navigation
        pages = ["chat", "terminal", "agent", "patterns", "warnings", "selfmod"]
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
    def _boot(self) -> None:
        """Start the async initialization thread."""
        self._status_bar.set_status("Initializing…")
        threading.Thread(target=self._boot_async, daemon=True).start()

    def _boot_async(self) -> None:
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
    def _ensure_page_loaded(self, page: str) -> None:
        if self._page_loaded.get(page, False):
            return

        factory = {
            "terminal": self._load_terminal_page,
            "timeline": self._load_timeline_page,
            "warnings": self._load_warnings_page,
            "agent":    self._load_agent_page,
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
        page.preview_requested.connect(self._on_proposal_preview)
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

    def _load_agent_page(self):
        from agent_page import AgentTaskPage
        page = AgentTaskPage()
        self._stack.addWidget(page)
        self._page_widgets["agent"] = page

        # Page-out: start / cancel / approve / reject → engine
        page.start_task.connect(self._on_agent_start)
        page.cancel_task.connect(self._on_agent_cancel)
        page.task_selected.connect(self._on_agent_select)
        page.approve_plan.connect(self._on_agent_plan_approve)
        page.reject_plan.connect(self._on_agent_plan_reject)
        page.approve_action.connect(self._on_agent_action_approve)
        page.reject_action.connect(self._on_agent_action_reject)

        # Engine → page: lifecycle signals
        s = self._signals
        s.agent_task_started.connect(self._on_agent_task_started)
        s.agent_plan_ready.connect(self._on_agent_plan_ready)
        s.agent_step.connect(self._on_agent_step)
        s.agent_tool_call.connect(self._on_agent_tool_event)
        s.agent_tool_result.connect(self._on_agent_tool_event)
        s.agent_approval_request.connect(self._on_agent_approval_request)
        s.agent_task_done.connect(self._on_agent_task_done)
        s.agent_cancel.connect(self._on_agent_cancel_emitted)

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
        dlg.model_changed.connect(self._on_model_changed)
        dlg.tts_toggled.connect(self._on_voice_toggle)
        dlg.suggestion_count_changed.connect(self._on_suggestion_count_changed)
        dlg.response_length_changed.connect(self._on_response_length_changed)
        # Agent (Phase 6): seed the dialog from live state, then wire signals
        import constants as _const
        dlg.set_agent_defaults(_const.AGENT_DEFAULT_MODE, _const.AGENT_MAX_STEPS)
        dlg.agent_mode_changed.connect(self._on_agent_mode_changed)
        dlg.agent_max_steps_changed.connect(self._on_agent_max_steps_changed)
        dlg.exec_()

    @pyqtSlot(str)
    def _on_agent_mode_changed(self, mode: str) -> None:
        import constants as _const
        if mode not in ("plan_apply", "auto_workspace"):
            return
        _const.AGENT_DEFAULT_MODE = mode
        # Update the live AgentRunner policy if the chat engine has one.
        if hasattr(self, "_engine") and self._engine and hasattr(self._engine, "_agent"):
            try:
                self._engine._agent._policy.mode = mode
            except Exception:
                pass
        self._signals.toast_show.emit(f"Agent mode: {mode}", "info")

    @pyqtSlot(int)
    def _on_agent_max_steps_changed(self, max_steps: int) -> None:
        import constants as _const
        _const.AGENT_MAX_STEPS = max(1, min(int(max_steps), 100))
        if hasattr(self, "_engine") and self._engine and hasattr(self._engine, "_agent"):
            try:
                self._engine._agent._max_steps = _const.AGENT_MAX_STEPS
            except Exception:
                pass
        self._signals.toast_show.emit(f"Agent max steps: {_const.AGENT_MAX_STEPS}", "info")

    @pyqtSlot()
    def _export_chat(self):
        """Export the current conversation with format choice."""
        if not self._history:
            self._toast_manager.warning("No messages to export.")
            return
        from PyQt5.QtWidgets import QFileDialog
        path_md, _ = QFileDialog.getSaveFileName(
            self, "Export as Markdown", f"aria_session_{self._session_id[:8]}.md",
            "Markdown (*.md);;All Files (*)"
        )
        if path_md:
            try:
                md = self._db.export_session_markdown(self._session_id) if self._db.ok else \
                     self._build_inline_markdown()
                with open(path_md, "w", encoding="utf-8") as f:
                    f.write(md)
                self._toast_manager.success(f"Exported to {path_md}")
            except Exception as e:
                self._toast_manager.error(f"Export failed: {e}")
        else:
            # User cancelled the MD dialog; offer JSON instead
            path_json, _ = QFileDialog.getSaveFileName(
                self, "Export as JSON", f"aria_session_{self._session_id[:8]}.json",
                "JSON (*.json);;All Files (*)"
            )
            if path_json:
                try:
                    js = self._db.export_session_json(self._session_id) if self._db.ok else \
                         json.dumps(self._history, indent=2)
                    with open(path_json, "w", encoding="utf-8") as f:
                        f.write(js)
                    self._toast_manager.success(f"Exported to {path_json}")
                except Exception as e:
                    self._toast_manager.error(f"Export failed: {e}")

    def _build_inline_markdown(self) -> str:
        """Build a simple markdown export from in-memory history (no DB)."""
        lines = [f"# ARIA Session — {self._session_id[:8]}\n"]
        for msg in self._history:
            role = "**You:**" if msg["role"] == "user" else "**ARIA:**"
            lines.append(f"{role}\n{msg['content']}\n\n---\n")
        return "\n".join(lines)

    @pyqtSlot(str)
    def _apply_theme(self, theme_name: str):
        self._current_theme = theme_name
        theme = THEMES.get(theme_name, THEMES["cyber"])
        QApplication.instance().setStyleSheet(build_stylesheet(theme))

    @pyqtSlot(str)
    def _on_model_changed(self, model: str):
        """Update the LLM model used for chat."""
        from constants import CHAT_MODEL
        try:
            self._llm.set_model(model)
            self._settings.setValue("app/model", model)
            self._toast_manager.info(f"Model set to {model}")
        except Exception as e:
            self._toast_manager.error(f"Failed to set model: {e}")

    @pyqtSlot(int)
    def _on_suggestion_count_changed(self, count: int):
        """Update suggestion count via selfmod."""
        if self._selfmod:
            try:
                self._selfmod.sandbox.config.apply("suggestion_count", count)
            except Exception:
                pass
        if self._engine:
            self._chat_page.set_suggestions(self._engine.get_suggestions("chat"))
        self._settings.setValue("app/suggestion_count", count)
        self._toast_manager.info(f"Suggestion count set to {count}")

    @pyqtSlot(str)
    def _on_response_length_changed(self, length: str):
        """Update response length preference."""
        if self._selfmod:
            try:
                self._selfmod.sandbox.config.apply("response_length_preference", length)
            except Exception:
                pass
        self._settings.setValue("app/response_length", length)
        self._toast_manager.info(f"Response length set to {length}")

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
        """Finalize streaming bubble and persist the completed message."""
        final_text = self._chat_page.end_stream()
        self._stream_started = False

        if final_text and final_text.strip():
            # Persist completed stream text (avoids duplicate in _on_chat_response)
            if self._db.ok:
                self._db.save_message(self._session_id, "assistant", final_text)
            self._history.append({"role": "assistant", "content": final_text})
            if len(self._history) > 40:
                self._history = self._history[-40:]
            self._sidebar.set_session_msg_count(len(self._history))
            if len(self._history) == 2:
                first_user = self._history[0].get("content", "")
                title = first_user[:60] + ("..." if len(first_user) > 60 else "")
                if self._db.ok:
                    self._db.save_session_title(self._session_id, title)

            # Mark so _on_chat_response can skip the duplicate UI add
            self._stream_completed = True
            self._stream_completed_text = final_text

    @pyqtSlot(int, str)
    def _on_reaction(self, message_seq: int, reaction: str):
        """Persist a message reaction to MongoDB and provide feedback."""
        if not self._db or not self._db.ok:
            return
        is_new = self._db.save_reaction(self._session_id, message_seq, reaction)
        action = "added" if is_new else "removed"
        self._status_bar.set_status(f"Reaction {action}: {reaction}")

    @pyqtSlot(str, str)
    def _on_chat_response(self, role: str, text: str):
        if role == "user":
            self._chat_page.add_message("user", text)
            return
        if role == "assistant":
            # Skip UI add if this is a streaming completion (already displayed + persisted)
            if self._stream_completed and text == self._stream_completed_text:
                self._stream_completed = False
                self._stream_completed_text = ""
                return

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
        except Exception as e: logger.warning("Reject failed: %s", e)

    @pyqtSlot(str)
    def _on_proposal_preview(self, proposal_id: str):
        """Phase 9: 'Try it' button — temporarily apply the proposed change
        to the running sandbox. Auto-reverts after 60s or on chat turn."""
        if not self._selfmod: return
        try:
            ok = self._selfmod.preview(proposal_id)
            if ok:
                self._signals.warning_added.emit(
                    "info",
                    "Preview active — change will revert after 60s. "
                    "Approve the proposal to keep it permanent."
                )
            else:
                self._signals.warning_added.emit("warning", "Could not start preview.")
        except Exception as e:
            logger.warning("Preview failed: %s", e)

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

    @pyqtSlot(list)
    def _on_selfmod_insights_changed(self, insights: list) -> None:
        """Refresh BrainWidget when the insights feed updates (Phase 9)."""
        if not self._chat_page: return
        bw = getattr(self._chat_page, "brain_widget", None)
        if bw is None: return
        pending = sum(1 for i in insights if i.get("status") == "proposed")
        last_ts = insights[0].get("ts") if insights else None
        last_str = last_ts.strftime("%H:%M") if last_ts and hasattr(last_ts, "strftime") else (
            str(last_ts)[:16] if last_ts else None
        )
        if self._selfmod and self._selfmod.is_previewing():
            bw.show_preview("Preview active — change will revert after 60s.")
            bw.setProperty("active", "preview")
        elif pending > 0:
            bw.show_pending(pending, last_str)
            bw.setProperty("active", "pending")
        else:
            from constants import AGENT_DEFAULT_MODE  # noqa
            shown = self._settings.value("app/first_brain_seen", False, bool)
            if not shown:
                bw.show_empty(last_str, onboarding=True)
            else:
                bw.show_empty(last_str, onboarding=False)
            bw.setProperty("active", "empty")

    @pyqtSlot(int)
    def _on_selfmod_badge_changed(self, count: int) -> None:
        """Update sidebar nav badge for proposal count changes (Phase 9).

        ``_on_selfmod_proposals`` is the primary path; this slot covers cases
        where the count changes without an explicit proposal emission
        (e.g. badge-only updates from the controller).
        """
        if getattr(self, "_sidebar", None) is not None:
            self._sidebar.set_proposal_count(count)

    @pyqtSlot()
    def _on_selfmod_cancel_preview(self) -> None:
        if self._selfmod and self._selfmod.is_previewing():
            self._selfmod.cancel_preview()
            self._signals.warning_added.emit("info", "Preview reverted.")

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

    # ── Agent page slots ────────────────────────────────────────────────────

    def _agent_page(self):
        page = self._page_widgets.get("agent")
        if page is None:
            return None
        self._ensure_page_loaded("agent")
        return self._page_widgets.get("agent")

    def _on_agent_start(self, goal: str) -> None:
        # Reuse chat_engine's intent path which already wires AgentRunner.
        # The task runs on a daemon thread; signals flow back to the page.
        if not goal:
            return
        try:
            self._engine._handle_agent_intent(goal, self._session_id, list(self._history))
        except Exception as e:
            self._signals.chat_response.emit(
                "assistant", f"❌ Failed to start agent task: {e}"
            )

    def _on_agent_cancel(self, task_id: str) -> None:
        if hasattr(self._engine, "_agent") and self._engine._agent:
            self._engine._agent.cancel(task_id)
        page = self._agent_page()
        if page:
            page.set_status(task_id, "cancelled")

    def _on_agent_select(self, task_id: str) -> None:
        page = self._agent_page()
        if page:
            page.select_task(task_id)

    def _on_agent_plan_approve(self, task_id: str) -> None:
        self._on_agent_plan_response(task_id, approved=True)

    def _on_agent_plan_reject(self, task_id: str) -> None:
        self._on_agent_plan_response(task_id, approved=False)

    def _on_agent_plan_response(self, task_id: str, approved: bool) -> None:
        # The page's approve_plan / reject_plan signals are already distinct
        # (separate pyqtSignals), so we have a separate slot for each and the
        # approved value is known up front. We resolve ALL pending approvals
        # for this task — the runner only has one plan approval pending at a
        # time during a plan_apply run, so this is safe.
        if hasattr(self._engine, "_agent") and self._engine._agent:
            for aid in list(self._engine._agent._approval_events.keys()):
                self._engine._agent.resolve_approval(aid, approved)
        page = self._agent_page()
        if page and approved:
            page.clear_plan()

    def _on_agent_action_approve(self, approval_id: str, task_id: str) -> None:
        self._on_agent_action_response(approval_id, task_id, approved=True)

    def _on_agent_action_reject(self, approval_id: str, task_id: str) -> None:
        self._on_agent_action_response(approval_id, task_id, approved=False)

    def _on_agent_action_response(
        self, approval_id: str, task_id: str, approved: bool
    ) -> None:
        if hasattr(self._engine, "_agent") and self._engine._agent:
            self._engine._agent.resolve_approval(approval_id, approved)
        # Remove the in-page approval card by rebuilding steps (simple approach)
        page = self._agent_page()
        if page and task_id:
            page.select_task(task_id)

    def _on_agent_task_started(self, task_id: str, goal: str) -> None:
        page = self._agent_page()
        if page:
            page.add_or_update_task({
                "task_id": task_id, "goal": goal, "status": "running",
                "mode": "plan_apply", "steps": [],
            })
        # Also reflect in timeline
        self._signals.timeline_event.emit("agent", f"started: {goal[:50]}")

    def _on_agent_plan_ready(self, task_id: str, plan_text: str) -> None:
        page = self._agent_page()
        if page:
            page.set_plan(task_id, plan_text)

    def _on_agent_step(self, task_id: str, step: dict) -> None:
        page = self._agent_page()
        if page:
            page.add_step(task_id, step)
        # Mirror to the main Timeline page
        st = step.get("type", "thought")
        if st == "action":
            tool = step.get("tool_name", "?")
            args = step.get("tool_args", {}) or {}
            # Concise inline chat status — one line per action so the user
            # sees progress without leaving the chat surface.
            arg_preview = self._short_args(args)
            self._signals.chat_response.emit(
                "assistant",
                f"\U0001f916 `{task_id[:8]}` ▸ `{tool}`{arg_preview}",
            )
            msg = f"{task_id[:8]} → {tool}"
        elif st == "observation":
            ok = step.get("executed", True)
            msg = f"{task_id[:8]} ← {step.get('tool_name','?')} ({'ok' if ok else 'refused'})"
        else:
            return
        self._signals.timeline_event.emit(f"agent_{st}", msg)

    @staticmethod
    def _short_args(args: dict, limit: int = 80) -> str:
        if not args:
            return ""
        try:
            import json as _json
            s = _json.dumps(args, ensure_ascii=False, default=str)
        except Exception:
            s = str(args)
        s = s if len(s) <= limit else s[: limit - 1] + "…"
        return f"  `{s}`"

    def _on_agent_tool_event(self, task_id: str, tool: str, payload: str) -> None:
        # Already covered by agent_step; kept as a hook for future inline rendering.
        pass

    def _on_agent_approval_request(self, approval_id: str, action: dict) -> None:
        # Plan approvals (kind=="plan") get a dedicated tab card; per-action
        # approvals are added to the Steps tab.
        page = self._agent_page()
        if not page:
            return
        if action.get("kind") == "plan":
            # Plan text is already shown via set_plan; nothing to add here.
            return
        page.add_approval(approval_id, action)

    def _on_agent_task_done(self, task_id: str, status: str, summary: str) -> None:
        page = self._agent_page()
        if page:
            page.set_status(task_id, status)
            page.set_summary(task_id, summary)
            if page._selected_task_id == task_id:
                page.select_task(task_id)
        self._signals.timeline_event.emit("agent", f"{status}: {task_id[:8]}")
        # Inline chat: emit the final answer so the user sees the result in
        # chat (mirrors how chat-delegated agents end with a streamed answer).
        icon = {"done": "\u2705", "failed": "\u274c", "cancelled": "\u23ed"}.get(status, "\u00b7")
        if status == "done":
            self._signals.chat_response.emit(
                "assistant",
                f"{icon} **Agent `{task_id[:8]}` finished**\n\n{summary}",
            )
        else:
            self._signals.chat_response.emit(
                "assistant",
                f"{icon} **Agent `{task_id[:8]}` {status}** — {summary}",
            )

    def _on_agent_cancel_emitted(self, task_id: str) -> None:
        page = self._agent_page()
        if page:
            page.set_status(task_id, "cancelled")
        self._signals.timeline_event.emit("agent", f"cancelled: {task_id[:8]}")

    # Boot complete - start health monitor in main thread
    @pyqtSlot(str)
    def _on_boot_complete(self, status: str):
        if status == "boot_complete":
            self._health.start()
            # Phase 9: first-run onboarding for the brain.
            if not self._settings.value("app/first_brain_seen", False, bool):
                self._toast_manager.info(
                    "I learn from how you use me — visit Self-Mod to see what I've noticed."
                )
                self._settings.setValue("app/first_brain_seen", True)

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
            seq = msg.get("seq", -1)
            self._history.append({"role": role, "content": content})
            self._chat_page.add_message(role, content, message_seq=seq)
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
            except Exception as e: logger.warning("Boot apply %s=%s failed: %s", key, value, e)

    def _refresh_selfmod_page(self):
        if not self._selfmod: return
        page = self._page_widgets.get("selfmod")
        if not page: return
        page.load_active_mods(self._selfmod.get_active_modifications())
        page.load_ledger(self._selfmod.get_ledger())
        pending = self._selfmod.get_pending()
        if pending: page.load_proposals(pending)
        # Phase 9: also refresh the Overview tab with insights + stats
        try:
            insights = self._selfmod.get_insights(limit=200)
            last_ts = self._selfmod.last_analysis()
            last_str = (
                last_ts.strftime("%Y-%m-%d %H:%M") if last_ts
                else None
            )
            page.load_overview(
                insights,
                self._selfmod.get_active_modifications(),
                last_str,
            )
        except Exception as e:
            logger.warning("Overview refresh failed: %s", e)

    def closeEvent(self, event):
        self._health.stop()
        if self._voice: self._voice.stop_speaking()
        self._db.save_last_session(self._session_id)
        # Persist window geometry and theme
        self._settings.setValue("window/geometry", self.saveGeometry())
        self._settings.setValue("window/state", self.saveState())
        self._settings.setValue("app/theme", self._current_theme)
        event.accept()
    
    # Command Palette
    def _show_command_palette(self):
        """Show the command palette at cursor position (lazy recreate if deleted)."""
        from PyQt5 import sip as _sip
        if self._command_palette is None or _sip.isdeleted(self._command_palette):
            self._command_palette = CommandPalette(self)
            self._command_palette.command_selected.connect(self._on_command_palette_action)
        from PyQt5.QtGui import QCursor
        cursor = QCursor.pos()
        self._command_palette.show_at(cursor.x(), cursor.y())


    def _show_shortcuts_help(self):
        """Show keyboard shortcuts help dialog (lazy recreate if deleted)."""
        from PyQt5 import sip as _sip
        if self._shortcuts_help is None or _sip.isdeleted(self._shortcuts_help):
            self._shortcuts_help = KeyboardShortcutsHelp(self)
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

import os, base64, threading
from datetime import datetime
from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel, QPushButton, QStackedWidget
from PyQt5.QtCore import Qt, QTimer, QByteArray, QBuffer
from PyQt5.QtGui import QFont, QPixmap
from constants import THEMES
from styles import build_stylesheet
from sidebar import Sidebar
from pages import ChatPage, TerminalPage, TimelinePage, WarningsPage
from signals import SignalBridge, HealthMonitor
from voice_engine import VoiceEngine
from chat_engine import chat_with_llm
from database import log_command, save_session_messages
from extract import execute_command, get_system_snapshot, requires_confirmation
from image_generation_try import ImageGenerator
from title import TitleBar

class ARIAWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.title_bar = TitleBar(self)
        self.setGeometry(200, 100, 1400, 850)
        # State
        self.session_id          = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.history: list       = []
        self.voice_enabled       = False
        self.silent_voice_mode   = False
        self.output_mode         = "verbose"
        self.current_theme       = "cyber"
        self.pending_command     = None
        self.last_search_results: list = []
        self._mic_active         = False       # STT recording state
        self._unread_warnings    = 0           # badge counter
        # Services
        self.voice_engine = VoiceEngine()
        self.image_gen    = ImageGenerator()
        # Signal bridge
        self.bridge = SignalBridge()
        self.bridge.message_signal.connect(self._on_message)
        self.bridge.suggestion_signal.connect(self._on_suggestions)
        self.bridge.timeline_signal.connect(self._on_timeline)
        self.bridge.image_signal.connect(self._on_image)
        self.bridge.stt_result_signal.connect(self._on_stt_result)
        self.bridge.stt_error_signal.connect(self._on_stt_error)
        self.bridge.warning_signal.connect(self._on_warning_page)
        # Health monitor
        self.health_monitor = HealthMonitor(interval_ms=300_000)
        self.health_monitor.alert_signal.connect(self._on_health_alert)
        self.health_monitor.start()
        self._build_ui()
        self.apply_theme()
        QTimer.singleShot(1000, self._update_sys_info)

    # UI
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self._switch_page)
        self.sidebar.voice_toggled.connect(self._on_voice_toggled)
        self.sidebar.silent_toggled.connect(self._on_silent_toggled)
        self.sidebar.theme_changed.connect(self.apply_theme)
        self.sidebar.mic_pressed.connect(self._on_mic_pressed)
        root.addWidget(self.sidebar)
        # Main area
        main_area = QFrame()
        main_area.setObjectName("mainArea")
        main_lyt = QVBoxLayout(main_area)
        main_lyt.setContentsMargins(0, 0, 0, 0)
        main_lyt.setSpacing(0)
        # Top bar
        top_bar = QFrame()
        top_bar.setObjectName("topBar")
        top_bar.setFixedHeight(52)
        top_bar_lyt = QHBoxLayout(top_bar)
        top_bar_lyt.setContentsMargins(24, 0, 24, 0)

        self.page_title = QLabel("Chat")
        self.page_title.setObjectName("pageTitle")
        self.page_title.setFont(QFont("Consolas", 11, QFont.Bold))
        top_bar_lyt.addWidget(self.page_title)
        top_bar_lyt.addStretch()

        self.mode_btn = QPushButton("MODE: VERBOSE")
        self.mode_btn.setObjectName("modeBtn")
        self.mode_btn.setFont(QFont("Consolas", 8))
        self.mode_btn.setFixedHeight(28)
        self.mode_btn.clicked.connect(self._toggle_output_mode)
        top_bar_lyt.addWidget(self.mode_btn)
        top_bar_lyt.addSpacing(16)

        self.confidence_label = QLabel("conf: –")
        self.confidence_label.setObjectName("confidenceLabel")
        self.confidence_label.setFont(QFont("Consolas", 8))
        top_bar_lyt.addWidget(self.confidence_label)
        top_bar_lyt.addSpacing(16)

        status_dot = QLabel("●  Online")
        status_dot.setObjectName("statusDot")
        status_dot.setFont(QFont("Consolas", 8))
        top_bar_lyt.addWidget(status_dot)

        main_lyt.addWidget(top_bar)

        accent_line = QFrame()
        accent_line.setObjectName("accentLine")
        accent_line.setFixedHeight(2)
        main_lyt.addWidget(accent_line)
        # Pages
        self.nav_stack = QStackedWidget()

        self.chat_page     = ChatPage()
        self.terminal_page = TerminalPage()
        self.timeline_page = TimelinePage()
        self.warnings_page = WarningsPage()

        self.chat_page.message_submitted.connect(self._send_message)
        self.chat_page.quick_action.connect(
            lambda cmd: (self.chat_page.input_field.setText(cmd), self._send_message(cmd))
        )
        self.terminal_page.command_submitted.connect(self._run_terminal_command)
        self.terminal_page.export_requested.connect(self._export_terminal)
        self.warnings_page.cleared.connect(lambda: self._reset_warning_badge())

        self.nav_stack.addWidget(self.chat_page)      # 0
        self.nav_stack.addWidget(self.terminal_page)  # 1
        self.nav_stack.addWidget(self.timeline_page)  # 2
        self.nav_stack.addWidget(self.warnings_page)  # 3

        main_lyt.addWidget(self.nav_stack)
        root.addWidget(main_area, stretch=1)

        self._switch_page(0)

    # Page switching
    def _switch_page(self, index: int):
        self.nav_stack.setCurrentIndex(index)
        titles = {0: "Chat", 1: "Terminal", 2: "Timeline", 3: "Warnings"}
        self.page_title.setText(titles.get(index, ""))
        self.sidebar.set_active_page(index)
        # Clear badge when user navigates to warnings page
        if index == 3:
            self._unread_warnings = 0
            self.sidebar.set_warning_badge(0)

    # Theme
    def apply_theme(self, name: str = None):
        if name:
            self.current_theme = name
        self.setStyleSheet(build_stylesheet(THEMES[self.current_theme]))

    def _theme(self) -> dict:
        return THEMES[self.current_theme]

    # System info
    def _update_sys_info(self):
        try:
            info     = get_system_snapshot()
            caption  = info.get("Caption", "Windows")
            hostname = info.get("Hostname", "Unknown")
            rows = [
                f"Host: {hostname}",
                f"OS:   {caption}",
            ]
            # Try to pull a couple more fields if available
            for key in ("TotalVisibleMemorySize", "FreePhysicalMemory"):
                val = info.get(key)
                if val:
                    label = "RAM Total" if "Total" in key else "RAM Free"
                    try:
                        mb = int(val) // 1024
                        rows.append(f"{label}: {mb} MB")
                    except Exception:
                        rows.append(f"{label}: {val}")
        except Exception:
            rows = ["System info", "unavailable"]
        self.sidebar.update_sys_info(rows)

    # Signal handlers
    def _on_message(self, role: str, content: str, mode: str):
        self.chat_page.append_message(role, content, mode, self._theme())

    def _on_suggestions(self, suggestions: list):
        self.chat_page.show_suggestions(suggestions)

    def _on_timeline(self, timestamp: str, action: str, status: str):
        self.timeline_page.add_entry(timestamp, action, status, self._theme()["dim"])

    def _on_image(self, path: str):
        try:
            pixmap = QPixmap(path)
            if pixmap.isNull():
                self.chat_page.append_message("system", f"⚠️ Could not load image: {path}", "system", self._theme())
                return
            pixmap = pixmap.scaledToWidth(400, Qt.SmoothTransformation)
            ba = QByteArray()
            buf = QBuffer(ba)
            buf.open(QBuffer.WriteOnly)
            pixmap.save(buf, "PNG")
            b64 = base64.b64encode(ba.data()).decode()
            self.chat_page.show_image(b64, self._theme()["border"])
        except Exception as e:
            self.chat_page.append_message("system", f"⚠️ Could not display image: {e}", "system", self._theme())

    def _on_health_alert(self, message: str, severity: str):
        color = "#ffcc00" if severity == "warning" else "#ff5252"
        self.sidebar.set_health(message, color)
        # Route to Warnings page — not chat
        self.bridge.warning_signal.emit(message, severity)
        if self.voice_enabled:
            self.voice_engine.speak(message, force=True)

    # Voice controls
    def _on_voice_toggled(self, enabled: bool):
        self.voice_enabled = enabled
        if enabled:
            self.voice_engine.speak("Voice enabled", force=True)

    def _on_silent_toggled(self, enabled: bool):
        self.silent_voice_mode = enabled

    # STT handlers
    def _on_mic_pressed(self):
        if not self._mic_active:
            # Start recording
            ok = self.voice_engine.start_recording()
            if not ok:
                self.chat_page.set_stt_status(
                    "⚠ Audio libs missing — pip install sounddevice soundfile numpy", "#f44336"
                )
                # Uncheck the button visually
                self.sidebar.mic_btn.setChecked(False)
                self.sidebar.mic_btn.setText("  ◎  Hold to Speak")
                self.sidebar.mic_btn.setStyleSheet("")
                return
            self._mic_active = True
            self.chat_page.set_stt_status("  ◉  Recording…  press mic again to stop", "#ff5252")
        else:
            # Stop and transcribe
            self._mic_active = False
            self.chat_page.set_stt_status("  ◌  Transcribing…", "#ffcc00")
            self.voice_engine.stop_recording_and_transcribe(
                on_result=lambda text: self.bridge.stt_result_signal.emit(text),
                on_error=lambda msg:   self.bridge.stt_error_signal.emit(msg),
            )

    def _on_stt_result(self, text: str):
        self.chat_page.set_stt_status("")
        self.chat_page.set_input_text(text)
        # Reset mic button state
        self.sidebar.mic_btn.setChecked(False)
        self.sidebar.mic_btn.setText("  ◎  Hold to Speak")
        self.sidebar.mic_btn.setStyleSheet("")

    def _on_stt_error(self, msg: str):
        self.chat_page.set_stt_status(f"⚠ {msg}", "#f44336")
        self.sidebar.mic_btn.setChecked(False)
        self.sidebar.mic_btn.setText("  ◎  Hold to Speak")
        self.sidebar.mic_btn.setStyleSheet("")

    # Warnings page handler
    def _on_warning_page(self, message: str, severity: str):
        self.warnings_page.add_warning(message, severity)
        # Increment badge only if user isn't on the warnings page right now
        if self.nav_stack.currentIndex() != 3:
            self._unread_warnings += 1
            self.sidebar.set_warning_badge(self._unread_warnings)

    def _reset_warning_badge(self):
        self._unread_warnings = 0
        self.sidebar.set_warning_badge(0)

    # Output mode
    def _toggle_output_mode(self):
        self.output_mode = "summary" if self.output_mode == "verbose" else "verbose"
        self.mode_btn.setText(f"MODE: {self.output_mode.upper()}")

    # Confidence display
    def _update_confidence(self, val: float):
        color = "#4caf50" if val >= 0.80 else ("#ffcc00" if val >= 0.60 else "#f44336")
        self.confidence_label.setStyleSheet(f"color: {color};")
        self.confidence_label.setText(f"conf: {val:.2f}")

    # Chat message flow
    def _send_message(self, message: str = None):
        if message is None: return
        message = message.strip()
        if not message: return
        self.chat_page.append_message("user", message, "chat", self._theme())
        self.history.append({"role": "user", "content": message})

        def process():
            try:
                result = chat_with_llm(
                    message,
                    self.session_id,
                    self.history,
                    output_mode=self.output_mode,
                    pending_command=self.pending_command,
                    last_search_results=self.last_search_results or None,
                )
                mode    = result["mode"]
                content = result["content"]
                conf    = result.get("confidence_val", 0.0)

                QTimer.singleShot(0, lambda: self._update_confidence(conf))

                if result.get("needs_confirmation"):
                    self.pending_command = result.get("pending_command")
                elif result.get("clear_pending") or not result.get("needs_confirmation"):
                    self.pending_command = None

                if result.get("search_results"):
                    self.last_search_results = result["search_results"]

                if result.get("raw_output") and mode == "command":
                    content = f"Command: {result['action']}\n\n{result['raw_output']}\n\n{content}"

                self.history.append({"role": "assistant", "content": content})
                self.bridge.message_signal.emit("assistant", content, mode)

                if result.get("image_path"):
                    self.bridge.image_signal.emit(result["image_path"])
                ts           = datetime.now().strftime("%H:%M:%S")
                status       = "ok" if not content.startswith(("❌", "⛔", "⚠")) else "error"
                action_label = result.get("action") or mode
                self.bridge.timeline_signal.emit(ts, str(action_label)[:60], status)

                if self.voice_enabled:
                    self.voice_engine.speak(content, mode=mode, silent_mode=self.silent_voice_mode)
                save_session_messages(self.session_id, message, content, mode)
            except Exception as e:
                self.bridge.message_signal.emit("system", f"Error: {e}", "error")
        threading.Thread(target=process, daemon=True).start()

    # Terminal
    def _run_terminal_command(self, command: str):
        if not command.strip(): return
        t = self._theme()
        self.bridge.timeline_signal.emit(datetime.now().strftime("%H:%M:%S"), command[:60], "ok")

        def execute():
            try:
                needs = requires_confirmation(command)
                if needs:
                    self.terminal_page.append_warning(
                        f"This will {needs}. Run command in Chat for confirmation flow."
                    )
                    return
                output = execute_command(command, skip_confirmation_check=True)
                self.terminal_page.append_output(command, output, t["dim"], t["accent"])
                log_command(self.session_id, command, output, "terminal")
            except Exception as e:
                self.terminal_page.append_error(str(e))
        threading.Thread(target=execute, daemon=True).start()

    def _export_terminal(self):
        content = self.terminal_page.terminal_display.toPlainText()
        if not content.strip(): return
        path = os.path.join(
            os.path.expanduser("~"), "Desktop",
            f"ARIA_terminal_{self.session_id}.txt",
        )
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.terminal_page.append_info(f"✔ Exported to Desktop: {os.path.basename(path)}")
        except Exception as e:
            self.terminal_page.append_error(f"Export failed: {e}")
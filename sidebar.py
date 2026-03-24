import psutil
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QComboBox, QFrame
from PyQt5.QtCore import QTimer, pyqtSignal
from constants import THEMES

class Sidebar(QWidget):
    # Signals
    nav_clicked      = pyqtSignal(str)   # page name
    theme_changed    = pyqtSignal(str)
    voice_toggled    = pyqtSignal(bool)
    silent_toggled   = pyqtSignal(bool)
    mic_pressed      = pyqtSignal()
    PAGES = [
        ("💬", "Chat",      "chat"),
        ("⌨️",  "Terminal",  "terminal"),
        ("📋", "Timeline",  "timeline"),
        ("⚠️",  "Warnings",  "warnings"),
        ("🧬", "Self-Mod",  "selfmod"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(200)

        self._nav_buttons: dict = {}
        self._active_page = "chat"
        self._warning_count = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        # Logo
        logo = QLabel("ARIA")
        logo.setObjectName("SidebarLogo")
        layout.addWidget(logo)
        # Nav buttons
        for icon, label, page in self.PAGES:
            btn = QPushButton(f"{icon}  {label}")
            btn.setObjectName("NavBtn")
            btn.setCheckable(False)
            btn.clicked.connect(lambda _, p=page: self._on_nav(p))
            layout.addWidget(btn)
            self._nav_buttons[page] = btn
        # Badge overlay for warnings (created after button)
        self._warn_btn = self._nav_buttons["warnings"]

        self._set_active("chat")

        sep1 = self._separator()
        layout.addWidget(sep1)
        # System info
        self._sys_label = QLabel("Loading...")
        self._sys_label.setObjectName("SysInfo")
        self._sys_label.setWordWrap(True)
        layout.addWidget(self._sys_label)

        sep2 = self._separator()
        layout.addWidget(sep2)
        # Voice toggle
        self._voice_btn = QPushButton("🔊  Voice ON")
        self._voice_btn.setObjectName("ToggleBtn")
        self._voice_btn.setCheckable(True)
        self._voice_btn.setChecked(True)
        self._voice_btn.clicked.connect(self._on_voice_toggle)
        layout.addWidget(self._voice_btn)
        # Silent mode toggle
        self._silent_btn = QPushButton("🤫  Silent OFF")
        self._silent_btn.setObjectName("ToggleBtn")
        self._silent_btn.setCheckable(True)
        self._silent_btn.setChecked(False)
        self._silent_btn.clicked.connect(self._on_silent_toggle)
        layout.addWidget(self._silent_btn)
        # Mic button
        self._mic_btn = QPushButton("🎤  Hold to Speak")
        self._mic_btn.setObjectName("MicBtn")
        self._mic_btn.pressed.connect(self._on_mic_press)
        layout.addWidget(self._mic_btn)

        sep3 = self._separator()
        layout.addWidget(sep3)
        # Theme selector
        theme_label = QLabel("Theme")
        theme_label.setObjectName("SysInfo")
        theme_label.setContentsMargins(16, 4, 0, 0)
        layout.addWidget(theme_label)

        self._theme_combo = QComboBox()
        self._theme_combo.setObjectName("ThemeCombo")
        self._theme_combo.addItems(list(THEMES.keys()))
        self._theme_combo.currentTextChanged.connect(self.theme_changed)
        layout.addWidget(self._theme_combo)

        layout.addStretch()
        # Update system info every 30s
        self._sys_timer = QTimer(self)
        self._sys_timer.setInterval(30_000)
        self._sys_timer.timeout.connect(self._update_sysinfo)
        self._sys_timer.start()
        self._update_sysinfo()
    # Nav
    def _on_nav(self, page: str):
        self._set_active(page)
        self.nav_clicked.emit(page)

    def _set_active(self, page: str):
        self._active_page = page
        for p, btn in self._nav_buttons.items():
            btn.setObjectName("NavBtnActive" if p == page else "NavBtn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
    # Warning badge
    def set_warning_count(self, count: int):
        self._warning_count = count
        label = "⚠️  Warnings"
        if count > 0: label += f" ({count})"
        self._warn_btn.setText(label)
    # Toggles
    def _on_voice_toggle(self):
        on = self._voice_btn.isChecked()
        self._voice_btn.setText("🔊  Voice ON" if on else "🔇  Voice OFF")
        self.voice_toggled.emit(on)

    def _on_silent_toggle(self):
        on = self._silent_btn.isChecked()
        self._silent_btn.setText("🤫  Silent ON" if on else "🤫  Silent OFF")
        self.silent_toggled.emit(on)

    def _on_mic_press(self):
        self._mic_btn.setObjectName("MicBtnActive")
        self._mic_btn.style().unpolish(self._mic_btn)
        self._mic_btn.style().polish(self._mic_btn)
        self._mic_btn.setText("🔴  Recording...")
        self.mic_pressed.emit()
        # Reset button after 6s (recording duration)
        QTimer.singleShot(6200, self._reset_mic_btn)

    def _reset_mic_btn(self):
        self._mic_btn.setObjectName("MicBtn")
        self._mic_btn.style().unpolish(self._mic_btn)
        self._mic_btn.style().polish(self._mic_btn)
        self._mic_btn.setText("🎤  Hold to Speak")

    def apply_selfmod(self, voice_on: bool, silent_on: bool):
        self._voice_btn.setChecked(voice_on)
        self._voice_btn.setText("🔊  Voice ON" if voice_on else "🔇  Voice OFF")
        self._silent_btn.setChecked(silent_on)
        self._silent_btn.setText("🤫  Silent ON" if silent_on else "🤫  Silent OFF")
    # System Info
    def _update_sysinfo(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            self._sys_label.setText(
                f"CPU: {cpu:.0f}%\n"
                f"RAM: {mem.percent:.0f}% ({mem.used // (1024**3)}/{mem.total // (1024**3)} GB)"
            )
        except Exception: self._sys_label.setText("System info unavailable")
    # Helpers
    def _separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        sep.setContentsMargins(8, 4, 8, 4)
        return sep
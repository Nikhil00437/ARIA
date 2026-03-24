import psutil
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QFrame, QSizePolicy
)
from PyQt5.QtCore import QTimer, pyqtSignal, Qt
from constants import THEMES


class Sidebar(QWidget):
    # ── Signals ──────────────────────────────────────────────────────────────
    nav_clicked    = pyqtSignal(str)
    theme_changed  = pyqtSignal(str)
    voice_toggled  = pyqtSignal(bool)
    silent_toggled = pyqtSignal(bool)
    mic_pressed    = pyqtSignal()

    PAGES = [
        ("💬", "Chat",     "chat"),
        ("⌨️",  "Terminal", "terminal"),
        ("📋", "Timeline", "timeline"),
        ("⚠️",  "Warnings", "warnings"),
        ("🧬", "Self-Mod", "selfmod"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(210)

        self._nav_buttons: dict = {}
        self._active_page = "chat"
        self._warning_count = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Logo ─────────────────────────────────────────────────────────────
        logo_area = QWidget()
        logo_area.setObjectName("SidebarLogoArea")
        logo_layout = QVBoxLayout(logo_area)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setSpacing(0)

        logo = QLabel("◈  ARIA")
        logo.setObjectName("SidebarLogo")
        tagline = QLabel("RUNTIME INTELLIGENCE")
        tagline.setObjectName("SidebarTagline")

        logo_layout.addWidget(logo)
        logo_layout.addWidget(tagline)
        layout.addWidget(logo_area)

        # ── Nav buttons ──────────────────────────────────────────────────────
        nav_section = QWidget()
        nav_section.setObjectName("NavSection")
        nav_layout = QVBoxLayout(nav_section)
        nav_layout.setContentsMargins(0, 8, 0, 8)
        nav_layout.setSpacing(0)

        for icon, label, page in self.PAGES:
            btn = QPushButton(f"  {icon}  {label}")
            btn.setObjectName("NavBtn")
            btn.clicked.connect(lambda _, p=page: self._on_nav(p))
            nav_layout.addWidget(btn)
            self._nav_buttons[page] = btn

        self._warn_btn = self._nav_buttons["warnings"]
        self._set_active("chat")
        layout.addWidget(nav_section)

        layout.addWidget(self._hsep())
        # System info
        self._sys_section = QLabel("SYSTEM")
        self._sys_section.setObjectName("SidebarSection")
        layout.addWidget(self._sys_section)

        self._cpu_label = QLabel("CPU  ·  –")
        self._cpu_label.setObjectName("SysInfo")
        self._ram_label = QLabel("RAM  ·  –")
        self._ram_label.setObjectName("SysInfo")

        layout.addWidget(self._cpu_label)
        layout.addWidget(self._ram_label)

        layout.addWidget(self._hsep())
        # Controls section
        ctrl_section = QLabel("CONTROLS")
        ctrl_section.setObjectName("SidebarSection")
        layout.addWidget(ctrl_section)

        self._voice_btn = QPushButton("🔊  Voice  ·  On")
        self._voice_btn.setObjectName("ToggleBtn")
        self._voice_btn.setCheckable(True)
        self._voice_btn.setChecked(True)
        self._voice_btn.clicked.connect(self._on_voice_toggle)
        layout.addWidget(self._voice_btn)

        self._silent_btn = QPushButton("🤫  Silent  ·  Off")
        self._silent_btn.setObjectName("ToggleBtn")
        self._silent_btn.setCheckable(True)
        self._silent_btn.setChecked(False)
        self._silent_btn.clicked.connect(self._on_silent_toggle)
        layout.addWidget(self._silent_btn)

        self._mic_btn = QPushButton("🎤  Hold to Speak")
        self._mic_btn.setObjectName("MicBtn")
        self._mic_btn.pressed.connect(self._on_mic_press)
        layout.addWidget(self._mic_btn)

        layout.addWidget(self._hsep())
        # Theme
        theme_section = QLabel("APPEARANCE")
        theme_section.setObjectName("SidebarSection")
        layout.addWidget(theme_section)

        self._theme_combo = QComboBox()
        self._theme_combo.setObjectName("ThemeCombo")
        self._theme_combo.addItems(list(THEMES.keys()))
        self._theme_combo.currentTextChanged.connect(self.theme_changed)
        layout.addWidget(self._theme_combo)

        layout.addStretch()
        # Version tag
        ver = QLabel("v1.0  ·  local")
        ver.setObjectName("SidebarTagline")
        ver.setAlignment(Qt.AlignCenter)
        layout.addWidget(ver)
        # System refresh timer
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
            name = "NavBtnActive" if p == page else "NavBtn"
            btn.setObjectName(name)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
    # Warning badge
    def set_warning_count(self, count: int):
        self._warning_count = count
        self._warn_btn.setText(
            f"  ⚠️  Warnings  ·  {count}" if count > 0 else "  ⚠️  Warnings"
        )
    # Toggles
    def _on_voice_toggle(self):
        on = self._voice_btn.isChecked()
        self._voice_btn.setText("🔊  Voice  ·  On" if on else "🔇  Voice  ·  Off")
        self.voice_toggled.emit(on)

    def _on_silent_toggle(self):
        on = self._silent_btn.isChecked()
        self._silent_btn.setText("🤫  Silent  ·  On" if on else "🤫  Silent  ·  Off")
        self.silent_toggled.emit(on)

    def _on_mic_press(self):
        self._mic_btn.setObjectName("MicBtnActive")
        self._mic_btn.style().unpolish(self._mic_btn)
        self._mic_btn.style().polish(self._mic_btn)
        self._mic_btn.setText("🔴  Recording...")
        self.mic_pressed.emit()
        QTimer.singleShot(6200, self._reset_mic_btn)

    def _reset_mic_btn(self):
        self._mic_btn.setObjectName("MicBtn")
        self._mic_btn.style().unpolish(self._mic_btn)
        self._mic_btn.style().polish(self._mic_btn)
        self._mic_btn.setText("🎤  Hold to Speak")

    def apply_selfmod(self, voice_on: bool, silent_on: bool):
        self._voice_btn.setChecked(voice_on)
        self._voice_btn.setText("🔊  Voice  ·  On" if voice_on else "🔇  Voice  ·  Off")
        self._silent_btn.setChecked(silent_on)
        self._silent_btn.setText("🤫  Silent  ·  On" if silent_on else "🤫  Silent  ·  Off")
    # System info
    def _update_sysinfo(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            self._cpu_label.setText(f"CPU  ·  {cpu:.0f}%")
            used  = mem.used  // (1024 ** 3)
            total = mem.total // (1024 ** 3)
            self._ram_label.setText(f"RAM  ·  {mem.percent:.0f}%  ({used}/{total} GB)")
        except Exception:
            self._cpu_label.setText("CPU  ·  –")
            self._ram_label.setText("RAM  ·  –")
    # Helpers
    def _hsep(self) -> QWidget:
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("HSep")
        sep.setStyleSheet("background: transparent; border: none; border-top: 1px solid;")
        sep.setContentsMargins(16, 4, 16, 4)
        sep.setFixedHeight(9)
        return sep
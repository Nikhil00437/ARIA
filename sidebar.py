# sidebar.py — Polished icon rail with refined stats

import psutil
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFrame
from PyQt5.QtCore import QTimer, pyqtSignal, Qt
from PyQt5.QtGui import QFont, QPalette, QColor


class Sidebar(QWidget):
    nav_clicked    = pyqtSignal(str)
    voice_toggled  = pyqtSignal(bool)
    silent_toggled = pyqtSignal(bool)
    mic_pressed    = pyqtSignal()

    PAGES = [
        ("chat",     "Chat"),
        ("terminal", "Terminal"),
        ("patterns", "Patterns"),
        ("warnings", "Warnings"),
        ("selfmod",  "Self-Mod"),
    ]

    PAGE_ICONS = {
        "chat":     "💬",
        "terminal": "⌨️",
        "patterns": "⬡",
        "warnings": "⚠️",
        "selfmod":  "🧬",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(68)

        self._nav_buttons: dict[str, QPushButton] = {}
        self._active_page  = "chat"
        self._warning_count = 0
        self._voice_on     = True
        self._silent_on    = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo 
        logo = QLabel("◈")
        logo.setObjectName("RailLogo")
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedHeight(60)
        layout.addWidget(logo)

        # Nav buttons 
        nav_frame = QWidget()
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(12, 8, 12, 8)
        nav_layout.setSpacing(6)

        for page, label in self.PAGES:
            btn = QPushButton(self.PAGE_ICONS[page])
            btn.setObjectName("RailBtn")
            btn.setFixedSize(44, 44)
            btn.setToolTip(label)
            btn.clicked.connect(lambda _, p=page: self._on_nav(p))
            nav_layout.addWidget(btn)
            self._nav_buttons[page] = btn

        layout.addWidget(nav_frame)
        layout.addStretch()

        # Separator 
        layout.addWidget(self._sep())

        # System stats 
        stats_frame = QWidget()
        stats_layout = QVBoxLayout(stats_frame)
        stats_layout.setContentsMargins(12, 8, 12, 8)
        stats_layout.setSpacing(8)

        self._cpu_bar  = self._make_mini_bar("CPU")
        self._ram_bar  = self._make_mini_bar("RAM")
        stats_layout.addWidget(self._cpu_bar[0])
        stats_layout.addWidget(self._ram_bar[0])

        layout.addWidget(stats_frame)
        layout.addWidget(self._sep())

        # Bottom controls
        bottom = QWidget()
        bot_layout = QVBoxLayout(bottom)
        bot_layout.setContentsMargins(12, 8, 12, 14)
        bot_layout.setSpacing(6)

        self._voice_btn = QPushButton("🔊")
        self._voice_btn.setObjectName("RailBtn")
        self._voice_btn.setFixedSize(44, 44)
        self._voice_btn.setToolTip("Voice: ON")
        self._voice_btn.setCheckable(True)
        self._voice_btn.setChecked(True)
        self._voice_btn.clicked.connect(self._on_voice)
        bot_layout.addWidget(self._voice_btn)

        self._mic_btn = QPushButton("🎤")
        self._mic_btn.setObjectName("RailBtn")
        self._mic_btn.setFixedSize(44, 44)
        self._mic_btn.setToolTip("Hold to Speak")
        self._mic_btn.pressed.connect(self._on_mic_press)
        bot_layout.addWidget(self._mic_btn)

        self._silent_btn = QPushButton("🔔")
        self._silent_btn.setObjectName("RailBtn")
        self._silent_btn.setFixedSize(44, 44)
        self._silent_btn.setToolTip("Silent Mode: OFF")
        self._silent_btn.setCheckable(True)
        self._silent_btn.setChecked(False)
        self._silent_btn.clicked.connect(self._on_silent)
        bot_layout.addWidget(self._silent_btn)

        layout.addWidget(bottom)

        root.addLayout(layout)

        # Vertical accent bar on right edge
        self._accent = QFrame()
        self._accent.setFixedWidth(3)
        self._accent.setStyleSheet("background: #00e5cc;")
        root.addWidget(self._accent)

        self._set_active("chat")

        # System info timer
        self._sys_timer = QTimer(self)
        self._sys_timer.setInterval(10_000)
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
            obj = "RailBtnActive" if p == page else "RailBtn"
            btn.setObjectName(obj)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # Warning badge
    def set_warning_count(self, count: int):
        self._warning_count = count
        btn = self._nav_buttons.get("warnings")
        if btn: btn.setToolTip(f"Warnings ({count})")

    # Voice / mic
    def _on_voice(self):
        self._voice_on = self._voice_btn.isChecked()
        self._voice_btn.setText("🔊" if self._voice_on else "🔇")
        self._voice_btn.setToolTip(f"Voice: {'ON' if self._voice_on else 'OFF'}")
        self.voice_toggled.emit(self._voice_on)

    def _on_mic_press(self):
        self._mic_btn.setObjectName("RailBtnActive")
        self._mic_btn.style().unpolish(self._mic_btn)
        self._mic_btn.style().polish(self._mic_btn)
        self._mic_btn.setText("🔴")
        self._mic_btn.setToolTip("Recording…")
        self.mic_pressed.emit()
        QTimer.singleShot(6200, self._reset_mic)

    def _reset_mic(self):
        self._mic_btn.setObjectName("RailBtn")
        self._mic_btn.style().unpolish(self._mic_btn)
        self._mic_btn.style().polish(self._mic_btn)
        self._mic_btn.setText("🎤")
        self._mic_btn.setToolTip("Hold to Speak")

    def _on_silent(self):
        self._silent_on = self._silent_btn.isChecked()
        self._silent_btn.setText("🔕" if self._silent_on else "🔔")
        self._silent_btn.setToolTip(f"Silent Mode: {'ON' if self._silent_on else 'OFF'}")
        self.silent_toggled.emit(self._silent_on)

    def apply_selfmod(self, voice_on: bool, silent_on: bool):
        self._voice_btn.setChecked(voice_on)
        self._voice_on = voice_on
        self._voice_btn.setText("🔊" if voice_on else "🔇")
        self._silent_btn.setChecked(silent_on)
        self._silent_on = silent_on
        self._silent_btn.setText("🔕" if silent_on else "🔔")

    def set_page_tint(self, color: str): self._accent.setStyleSheet(f"background: {color};")

    # System info
    def _make_mini_bar(self, label: str):
        container = QWidget()
        container.setFixedHeight(24)
        container.setToolTip(label)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        bar_wrap = QFrame()
        bar_wrap.setFixedHeight(3)
        bar_wrap.setObjectName("RailStatBar")

        bar_fill = QFrame(bar_wrap)
        bar_fill.setFixedHeight(3)
        bar_fill.setObjectName("RailStatFill")
        bar_fill.setFixedWidth(0)

        layout.addWidget(bar_wrap)
        return container, bar_fill, bar_wrap

    def _update_sysinfo(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()

            _, cpu_fill, cpu_wrap = self._cpu_bar
            _, ram_fill, ram_wrap = self._ram_bar

            w_cpu = cpu_wrap.width()
            w_ram = ram_wrap.width()
            if w_cpu > 4: cpu_fill.setFixedWidth(max(2, int(w_cpu * cpu / 100)))
            if w_ram > 4: ram_fill.setFixedWidth(max(2, int(w_ram * mem.percent / 100)))

            self._cpu_bar[0].setToolTip(f"CPU: {cpu:.0f}%")
            self._ram_bar[0].setToolTip(f"RAM: {mem.percent:.0f}%")
        except Exception: pass

    # Helpers
    def _sep(self) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.HLine)
        f.setFixedHeight(1)
        f.setStyleSheet("background: rgba(255,255,255,0.06); margin: 0 14px;")
        return f
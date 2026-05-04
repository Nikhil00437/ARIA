# sidebar.py — Glassy minimal icon rail

import psutil
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFrame, QHBoxLayout
from PyQt5.QtCore import QTimer, pyqtSignal, Qt
from PyQt5.QtGui import QFont


class Sidebar(QWidget):
    nav_clicked    = pyqtSignal(str)
    voice_toggled  = pyqtSignal(bool)
    silent_toggled = pyqtSignal(bool)
    mic_pressed    = pyqtSignal()
    new_session    = pyqtSignal()

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

    PAGE_TOOLTIPS = {
        "chat":     "Chat — Ask questions, get answers",
        "terminal": "Terminal — Run commands",
        "patterns": "Patterns — Fabric AI patterns",
        "warnings": "Warnings — System alerts",
        "selfmod":  "Self-Mod — Behavioral analysis",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(70)

        self._nav_buttons: dict[str, QPushButton] = {}
        self._notif_badges: dict[str, QLabel]     = {}
        self._active_page   = "chat"
        self._voice_on      = False
        self._silent_on     = False

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        inner = QVBoxLayout()
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(0)

        # Logo
        logo = QLabel("◈")
        logo.setObjectName("RailLogo")
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedHeight(64)
        inner.addWidget(logo)

        # Thin separator
        inner.addWidget(self._sep())

        # Nav buttons
        nav_frame = QWidget()
        nav_frame.setStyleSheet("background: transparent;")
        nav_lyt = QVBoxLayout(nav_frame)
        nav_lyt.setContentsMargins(13, 10, 13, 10)
        nav_lyt.setSpacing(4)

        for page, label in self.PAGES:
            btn = QPushButton(self.PAGE_ICONS[page])
            btn.setObjectName("RailBtn")
            btn.setFixedSize(44, 44)
            btn.setToolTip(self.PAGE_TOOLTIPS.get(page, label))
            btn.clicked.connect(lambda _, p=page: self._on_nav(p))
            nav_lyt.addWidget(btn)
            self._nav_buttons[page] = btn

            dot = QLabel("●")
            dot.setObjectName("NotifDot")
            dot.setAlignment(Qt.AlignCenter)
            dot.setFixedHeight(8)
            dot.setStyleSheet(
                "color: rgba(255,80,80,0.9); background: transparent; "
                "font-size: 8px; font-weight: 800;"
            )
            dot.setVisible(False)
            nav_lyt.addWidget(dot, alignment=Qt.AlignCenter)
            self._notif_badges[page] = dot

        inner.addWidget(nav_frame)
        inner.addStretch()
        inner.addWidget(self._sep())

        # Mini stat bars (CPU + RAM)
        stats = QWidget()
        stats.setStyleSheet("background: transparent;")
        stats_lyt = QVBoxLayout(stats)
        stats_lyt.setContentsMargins(14, 10, 14, 10)
        stats_lyt.setSpacing(8)
        self._cpu_bar = self._make_mini_bar("CPU")
        self._ram_bar = self._make_mini_bar("RAM")
        stats_lyt.addWidget(self._cpu_bar[0])
        stats_lyt.addWidget(self._ram_bar[0])
        inner.addWidget(stats)

        inner.addWidget(self._sep())

        # Bottom controls
        bot = QWidget()
        bot.setStyleSheet("background: transparent;")
        bot_lyt = QVBoxLayout(bot)
        bot_lyt.setContentsMargins(13, 8, 13, 10)
        bot_lyt.setSpacing(4)

        self._new_session_btn = self._make_ctrl_btn("✚", "New Session (Ctrl+N)")
        self._new_session_btn.clicked.connect(lambda: self.new_session.emit())

        self._voice_btn = self._make_ctrl_btn("🔇", "Voice: OFF")
        self._voice_btn.setCheckable(True)
        self._voice_btn.clicked.connect(self._on_voice)

        self._mic_btn = self._make_ctrl_btn("🎤", "Hold to Speak")
        self._mic_btn.pressed.connect(self._on_mic_press)
        self._mic_btn.released.connect(self._on_mic_release)

        self._silent_btn = self._make_ctrl_btn("🔔", "Silent Mode: OFF")
        self._silent_btn.setCheckable(True)
        self._silent_btn.clicked.connect(self._on_silent)

        for b in (self._new_session_btn, self._voice_btn, self._mic_btn, self._silent_btn):
            bot_lyt.addWidget(b)

        inner.addWidget(bot)

        root.addLayout(inner)

        # Right accent bar
        self._accent = QFrame()
        self._accent.setFixedWidth(3)
        self._accent.setStyleSheet("background: rgba(120,180,255,0.6); border-radius: 2px; border: none;")
        root.addWidget(self._accent)

        self._set_active_style("chat")

        # System info timer
        self._sys_timer = QTimer(self)
        self._sys_timer.setInterval(10_000)
        self._sys_timer.timeout.connect(self._update_sysinfo)
        self._sys_timer.start()
        QTimer.singleShot(1500, self._update_sysinfo)

    # Helpers
    def _make_ctrl_btn(self, icon, tip):
        b = QPushButton(icon)
        b.setObjectName("RailBtn")
        b.setFixedSize(44, 44)
        b.setToolTip(tip)
        return b

    def _sep(self):
        f = QFrame()
        f.setFrameShape(QFrame.HLine)
        f.setFixedHeight(1)
        f.setStyleSheet(
            "background: rgba(255,255,255,0.06); margin: 0 14px; border: none;"
        )
        return f

    def _make_mini_bar(self, label):
        container = QWidget()
        container.setFixedHeight(22)
        container.setToolTip(label)
        lyt = QVBoxLayout(container)
        lyt.setContentsMargins(0, 0, 0, 0)
        lyt.setSpacing(2)

        lbl = QLabel(label)
        lbl.setStyleSheet(
            "background: transparent; color: rgba(255,255,255,0.40); "
            "font-size: 7px; font-family: 'Consolas'; font-weight: 600;"
        )
        lbl.setFixedHeight(10)

        bar_wrap = QFrame()
        bar_wrap.setFixedHeight(4)
        bar_wrap.setObjectName("RailStatBar")
        bar_wrap.setStyleSheet("background: rgba(255,255,255,0.06); border-radius: 2px; border: none;")

        bar_fill = QFrame(bar_wrap)
        bar_fill.setFixedHeight(4)
        bar_fill.setObjectName("RailStatFill")
        bar_fill.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 rgba(80,140,255,0.8), stop:1 rgba(140,80,255,0.8)); border-radius: 2px; border: none;"
        )
        bar_fill.setFixedWidth(0)

        lyt.addWidget(lbl)
        lyt.addWidget(bar_wrap)
        return container, bar_fill, bar_wrap

    # Nav
    def _on_nav(self, page):
        self._set_active_style(page)
        self.nav_clicked.emit(page)

    def _set_active_style(self, page):
        if self._active_page == page: return
        self._active_page = page
        for p, btn in self._nav_buttons.items():
            btn.setObjectName("RailBtnActive" if p == page else "RailBtn")
            # Force Qt style refresh
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # Notification badges
    def set_warning_count(self, count):
        self._notif_badges.get("warnings", QLabel()).setVisible(count > 0)
        btn = self._nav_buttons.get("warnings")
        if btn: btn.setToolTip(f"Warnings ({count})")

    def set_proposal_count(self, count):
        self._notif_badges.get("selfmod", QLabel()).setVisible(count > 0)
        btn = self._nav_buttons.get("selfmod")
        if btn: btn.setToolTip(f"Self-Mod ({count} proposals)")

    def set_session_msg_count(self, count):
        btn = self._nav_buttons.get("chat")
        if btn: btn.setToolTip(f"Chat — {count} messages in session")

    # Voice / Mic
    def _on_voice(self):
        self._voice_on = self._voice_btn.isChecked()
        self._voice_btn.setText("🔊" if self._voice_on else "🔇")
        self._voice_btn.setToolTip(f"Voice: {'ON' if self._voice_on else 'OFF'}")
        self.voice_toggled.emit(self._voice_on)

    def _on_mic_press(self):
        self._mic_btn.setText("🔴")
        self.mic_pressed.emit()

    def _on_mic_release(self): self._mic_btn.setText("🎤")

    def _on_silent(self):
        self._silent_on = self._silent_btn.isChecked()
        self._silent_btn.setText("🔕" if self._silent_on else "🔔")
        self._silent_btn.setToolTip(f"Silent Mode: {'ON' if self._silent_on else 'OFF'}")
        self.silent_toggled.emit(self._silent_on)

    def apply_selfmod(self, voice_on, silent_on):
        self._voice_btn.setChecked(voice_on)
        self._voice_on = voice_on
        self._voice_btn.setText("🔊" if voice_on else "🔇")
        self._silent_btn.setChecked(silent_on)
        self._silent_on = silent_on
        self._silent_btn.setText("🔕" if silent_on else "🔔")

    def set_page_tint(self, color): self._accent.setStyleSheet(f"background: {color}; border-radius: 2px; border: none;")

    # System info
    def _update_sysinfo(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()

            _, cpu_fill, cpu_wrap = self._cpu_bar
            _, ram_fill, ram_wrap = self._ram_bar

            w = cpu_wrap.width()
            if w > 4: cpu_fill.setFixedWidth(max(2, int(w * cpu / 100)))
            w2 = ram_wrap.width()
            if w2 > 4: ram_fill.setFixedWidth(max(2, int(w2 * mem.percent / 100)))

            self._cpu_bar[0].setToolTip(f"CPU: {cpu:.0f}%")
            self._ram_bar[0].setToolTip(f"RAM: {mem.percent:.0f}%")
        except Exception: pass
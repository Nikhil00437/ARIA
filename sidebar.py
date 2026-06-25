# sidebar.py — Horizontal Minimal Top Navigation Dock
import psutil
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QFrame
from PyQt5.QtCore import QTimer, pyqtSignal, Qt


class Sidebar(QWidget):
    nav_clicked    = pyqtSignal(str)
    voice_toggled  = pyqtSignal(bool)
    silent_toggled = pyqtSignal(bool)
    mic_pressed    = pyqtSignal()
    new_session    = pyqtSignal()

    PAGES = [
        ("chat",     "Chat"),
        ("terminal", "Terminal"),
        ("agent",    "Agent"),
        ("patterns", "Patterns"),
        ("warnings", "Warnings"),
        ("selfmod",  "Self-Mod"),
    ]

    # Plain uppercase labels (no emoji prefixes — the minimal aesthetic uses
    # typography for hierarchy instead of glyphs).
    PAGE_ICONS = {
        "chat":     "Chat",
        "terminal": "Terminal",
        "agent":    "Agent",
        "patterns": "Patterns",
        "warnings": "Warnings",
        "selfmod":  "Self-Mod",
    }

    PAGE_TOOLTIPS = {
        "chat":     "Chat console with ARIA AI",
        "terminal": "System PowerShell console",
        "agent":    "Plan-act-observe coding agent",
        "patterns": "Fabric and Local pattern browser",
        "warnings": "System health warning logs",
        "selfmod":  "Behavioral learning & self-modification",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedHeight(54)

        self._nav_buttons: dict[str, QPushButton] = {}
        self._notif_badges: dict[str, QLabel]     = {}
        self._active_page   = "chat"
        self._voice_on      = False
        self._silent_on     = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        content = QHBoxLayout()
        content.setContentsMargins(16, 0, 16, 0)
        content.setSpacing(12)

        # ── Left: Nav buttons ──────────────────────────────────
        nav_container = QWidget()
        nav_container.setStyleSheet("background: transparent;")
        nav_lyt = QHBoxLayout(nav_container)
        nav_lyt.setContentsMargins(0, 0, 0, 0)
        nav_lyt.setSpacing(4)

        for page, label in self.PAGES:
            btn = QPushButton(self.PAGE_ICONS[page])
            btn.setObjectName("RailBtn")
            btn.setFixedHeight(36)
            btn.setToolTip(self.PAGE_TOOLTIPS.get(page, label))
            btn.clicked.connect(lambda _, p=page: self._on_nav(p))
            nav_lyt.addWidget(btn)
            self._nav_buttons[page] = btn

            dot = QLabel("\u25cf")
            dot.setObjectName("NotifDot")
            dot.setVisible(False)
            nav_lyt.addWidget(dot)
            self._notif_badges[page] = dot

        content.addWidget(nav_container)
        content.addStretch()

        # ── Middle-Right: CPU + RAM stats (themed via object names) ─
        stats = QWidget()
        stats.setStyleSheet("background: transparent;")
        stats_lyt = QHBoxLayout(stats)
        stats_lyt.setContentsMargins(0, 0, 0, 0)
        stats_lyt.setSpacing(10)

        self._cpu_bar = self._make_mini_bar("CPU")
        self._ram_bar = self._make_mini_bar("RAM")
        stats_lyt.addWidget(self._cpu_bar[0])
        stats_lyt.addWidget(self._ram_bar[0])
        content.addWidget(stats)

        # Vertical divider (themed via #SidebarDivider)
        v_sep = QFrame()
        v_sep.setFrameShape(QFrame.VLine)
        v_sep.setObjectName("SidebarDivider")
        v_sep.setFixedWidth(1)
        content.addWidget(v_sep)

        # ── Right: Control buttons ─────────────────────────────
        bot = QWidget()
        bot.setStyleSheet("background: transparent;")
        bot_lyt = QHBoxLayout(bot)
        bot_lyt.setContentsMargins(0, 0, 0, 0)
        bot_lyt.setSpacing(4)

        self._new_session_btn = self._make_ctrl_btn("+", "New Session (Ctrl+N)")
        self._new_session_btn.clicked.connect(lambda: self.new_session.emit())

        self._voice_btn = self._make_ctrl_btn("\u266b", "Voice: OFF")
        self._voice_btn.setCheckable(True)
        self._voice_btn.clicked.connect(self._on_voice)

        self._mic_btn = self._make_ctrl_btn("\u25cf", "Hold to Speak")
        self._mic_btn.pressed.connect(self._on_mic_press)
        self._mic_btn.released.connect(self._on_mic_release)

        self._silent_btn = self._make_ctrl_btn("\u266b", "Silent Mode: OFF")
        self._silent_btn.setCheckable(True)
        self._silent_btn.clicked.connect(self._on_silent)

        for b in (self._new_session_btn, self._voice_btn, self._mic_btn, self._silent_btn):
            bot_lyt.addWidget(b)

        content.addWidget(bot)
        root.addLayout(content, 1)

        # Subtle 1px accent strip beneath the bar (themed via #SidebarAccent)
        self._accent = QFrame()
        self._accent.setFixedHeight(1)
        self._accent.setObjectName("SidebarAccent")
        root.addWidget(self._accent)

        self._set_active_style("chat")

        self._sys_timer = QTimer(self)
        self._sys_timer.setInterval(10_000)
        self._sys_timer.timeout.connect(self._update_sysinfo)
        self._sys_timer.start()
        QTimer.singleShot(1500, self._update_sysinfo)

    def _make_ctrl_btn(self, icon, tip):
        b = QPushButton(icon)
        b.setObjectName("RailBtn")
        b.setFixedSize(32, 32)
        b.setToolTip(tip)
        return b

    def _make_mini_bar(self, label):
        container = QWidget()
        container.setFixedSize(80, 36)
        container.setToolTip(label)
        lyt = QVBoxLayout(container)
        lyt.setContentsMargins(0, 4, 0, 4)
        lyt.setSpacing(3)

        # Label uses #SidebarStatLabel from the global stylesheet (caps,
        # monospace, muted color). No inline QSS.
        lbl = QLabel(label)
        lbl.setObjectName("SidebarStatLabel")
        lbl.setFixedHeight(10)

        bar_wrap = QFrame()
        bar_wrap.setFixedHeight(3)
        bar_wrap.setObjectName("SidebarStatBar")

        bar_fill = QFrame(bar_wrap)
        bar_fill.setFixedHeight(3)
        bar_fill.setObjectName(f"RailStatFill_{label}")
        bar_fill.setFixedWidth(0)

        lyt.addWidget(lbl)
        lyt.addWidget(bar_wrap)
        return container, bar_fill, bar_wrap

    def _on_nav(self, page):
        self._set_active_style(page)
        self.nav_clicked.emit(page)

    def _set_active_style(self, page):
        self._active_page = page
        for p, btn in self._nav_buttons.items():
            btn.setObjectName("RailBtnActive" if p == page else "RailBtn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

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
        if btn: btn.setToolTip(f"Chat \u2014 {count} messages in session")

    def _on_voice(self):
        self._voice_on = self._voice_btn.isChecked()
        self._voice_btn.setToolTip(f"Voice: {'ON' if self._voice_on else 'OFF'}")
        self.voice_toggled.emit(self._voice_on)

    def _on_mic_press(self):
        self._mic_btn.setText("\u25cf")
        self.mic_pressed.emit()

    def _on_mic_release(self):
        self._mic_btn.setText("\u25cf")

    def _on_silent(self):
        self._silent_on = self._silent_btn.isChecked()
        self._silent_btn.setToolTip(f"Silent Mode: {'ON' if self._silent_on else 'OFF'}")
        self.silent_toggled.emit(self._silent_on)

    def apply_selfmod(self, voice_on, silent_on):
        self._voice_btn.setChecked(voice_on)
        self._voice_on = voice_on
        self._silent_btn.setChecked(silent_on)
        self._silent_on = silent_on

    def set_page_tint(self, color):
        """Legacy hook — tint the accent strip with a per-page color. Uses
        inline QSS only because the color is dynamic per page."""
        self._accent.setStyleSheet(f"background: {color}; border: none;")

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
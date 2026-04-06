# quick_panel.py — Refined Quick Actions + System Stats panels

import psutil
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

try:
    import pynvml
    pynvml.nvmlInit()
    HAS_GPU = True
except Exception: HAS_GPU = False

# Quick action definitions
QUICK_ACTIONS = [
    ("📝", "Summarize",  "pattern", "summarize"),
    ("💡", "Extract",    "pattern", "extract_wisdom"),
    ("🔍", "Analyze",    "pattern", "analyze_claims"),
    ("✍️",  "Improve",   "pattern", "improve_writing"),
    ("⌨️",  "Terminal",  "nav",     "terminal"),
    ("🌐", "Browse",     "input",   "open "),
]

class QuickPanel(QWidget):
    pattern_requested = pyqtSignal(str)
    nav_requested     = pyqtSignal(str)
    input_requested   = pyqtSignal(str)
    cmd_requested     = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlassPanel")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Accent bar
        self._accent = QFrame()
        self._accent.setFixedHeight(3)
        self._accent.setStyleSheet("background: #00e5cc;")
        root.addWidget(self._accent)

        # Header
        header = QWidget()
        header.setObjectName("GlassPanelHeader")
        header.setFixedHeight(40)
        h_lyt = QHBoxLayout(header)
        h_lyt.setContentsMargins(16, 0, 16, 0)

        title = QLabel("QUICK")
        title.setObjectName("GlassPanelTitle")

        dot = QLabel("●")
        dot.setObjectName("GlassPanelDot")

        h_lyt.addWidget(title)
        h_lyt.addStretch()
        h_lyt.addWidget(dot)
        root.addWidget(header)

        # 2×3 Button grid
        grid_wrap = QWidget()
        grid_wrap.setStyleSheet("background: transparent;")
        grid = QGridLayout(grid_wrap)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setSpacing(10)

        for i, (icon, label, atype, value) in enumerate(QUICK_ACTIONS):
            btn = self._make_btn(icon, label, atype, value)
            row, col = divmod(i, 2)
            grid.addWidget(btn, row, col)

        root.addWidget(grid_wrap)

    def _make_btn(self, icon: str, label: str, atype: str, value: str) -> QPushButton:
        btn = QPushButton()
        btn.setObjectName("QuickBtn")
        btn.setFixedHeight(60)
        btn.setText(f"{icon}\n{label}")
        btn.setFont(QFont("Segoe UI", 9))

        def _clicked():
            if   atype == "pattern": self.pattern_requested.emit(value)
            elif atype == "nav":     self.nav_requested.emit(value)
            elif atype == "input":   self.input_requested.emit(value)
            elif atype == "cmd":     self.cmd_requested.emit(value)

        btn.clicked.connect(_clicked)
        return btn

    def set_page_tint(self, bg: str, border: str):
        self._accent.setStyleSheet(f"background: {border};")


class SystemPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlassPanel")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Accent bar
        self._accent = QFrame()
        self._accent.setFixedHeight(3)
        self._accent.setStyleSheet("background: #00e5cc;")
        root.addWidget(self._accent)

        # Header
        header = QWidget()
        header.setObjectName("GlassPanelHeader")
        header.setFixedHeight(40)
        h_lyt = QHBoxLayout(header)
        h_lyt.setContentsMargins(16, 0, 16, 0)

        title = QLabel("SYSTEM")
        title.setObjectName("GlassPanelTitle")
        h_lyt.addWidget(title)
        h_lyt.addStretch()
        root.addWidget(header)

        # Stats
        stats_wrap = QWidget()
        stats_wrap.setStyleSheet("background: transparent;")
        stats_lyt = QVBoxLayout(stats_wrap)
        stats_lyt.setContentsMargins(16, 12, 16, 14)
        stats_lyt.setSpacing(12)

        self._cpu_row  = self._make_stat_row("CPU")
        self._ram_row  = self._make_stat_row("RAM")
        self._gpu_row  = self._make_stat_row("GPU") if HAS_GPU else None
        self._wifi_row = self._make_wifi_row()
        self._llm_row  = self._make_llm_row()

        stats_lyt.addLayout(self._cpu_row[0])
        stats_lyt.addLayout(self._ram_row[0])
        if self._gpu_row:
            stats_lyt.addLayout(self._gpu_row[0])
        stats_lyt.addLayout(self._wifi_row[0])
        stats_lyt.addLayout(self._llm_row[0])
        root.addWidget(stats_wrap)

        # Auto-update timer
        self._timer = QTimer(self)
        self._timer.setInterval(8000)
        self._timer.timeout.connect(self.update_stats)
        self._timer.start()
        self.update_stats()

    def _make_stat_row(self, label: str):
        row = QHBoxLayout()
        row.setSpacing(10)

        name_lbl = QLabel(label)
        name_lbl.setFixedWidth(32)
        name_lbl.setStyleSheet(
            "background: transparent; color: #3a3a5a; "
            "font-family: 'Consolas'; font-size: 8pt; font-weight: 600;"
        )

        bar_track = QFrame()
        bar_track.setFixedHeight(5)
        bar_track.setObjectName("RailStatBar")

        bar_fill = QFrame(bar_track)
        bar_fill.setFixedHeight(5)
        bar_fill.setObjectName("RailStatFill")
        bar_fill.setFixedWidth(0)

        pct_lbl = QLabel("0%")
        pct_lbl.setFixedWidth(34)
        pct_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        pct_lbl.setStyleSheet(
            "background: transparent; color: #ef9a9a; "
            "font-family: 'Consolas'; font-size: 8pt; font-weight: 600;"
        )

        row.addWidget(name_lbl)
        row.addWidget(bar_track, 1)
        row.addWidget(pct_lbl)

        return row, bar_fill, pct_lbl, bar_track

    def _make_wifi_row(self):
        row = QHBoxLayout()
        row.setSpacing(10)

        name_lbl = QLabel("WiFi")
        name_lbl.setFixedWidth(32)
        name_lbl.setStyleSheet(
            "background: transparent; color: #3a3a5a; "
            "font-family: 'Consolas'; font-size: 8pt; font-weight: 600;"
        )

        signal_lbl = QLabel("—")
        signal_lbl.setStyleSheet(
            "background: transparent; color: #ef9a9a; "
            "font-family: 'Consolas'; font-size: 8pt;"
        )

        row.addWidget(name_lbl)
        row.addWidget(signal_lbl, 1)

        return row, signal_lbl

    def _make_llm_row(self):
        row = QHBoxLayout()
        row.setSpacing(10)

        name_lbl = QLabel("LLM")
        name_lbl.setFixedWidth(32)
        name_lbl.setStyleSheet(
            "background: transparent; color: #3a3a5a; "
            "font-family: 'Consolas'; font-size: 8pt; font-weight: 600;"
        )

        dot = QLabel("●")
        dot.setStyleSheet("background: transparent; color: #ef9a9a; font-size: 9px;")

        status = QLabel("online")
        status.setStyleSheet(
            "background: transparent; color: #ef9a9a; "
            "font-family: 'Consolas'; font-size: 8pt;"
        )

        row.addWidget(name_lbl)
        row.addStretch()
        row.addWidget(dot)
        row.addWidget(status)

        return row, dot, status

    def update_stats(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()

            _, cpu_fill, cpu_pct, cpu_track = self._cpu_row
            _, ram_fill, ram_pct, ram_track  = self._ram_row

            def _set_bars():
                w = cpu_track.width()
                if w > 5:
                    cpu_fill.setFixedWidth(max(2, int(w * cpu / 100)))
                    ram_fill.setFixedWidth(max(2, int(w * mem.percent / 100)))

            QTimer.singleShot(50, _set_bars)
            cpu_pct.setText(f"{cpu:.0f}%")
            ram_pct.setText(f"{mem.percent:.0f}%")
        except Exception: pass

        # GPU stats
        if HAS_GPU and self._gpu_row:
            try:
                _, gpu_fill, gpu_pct, gpu_track = self._gpu_row
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                gpu_pct.setText(f"{util.gpu}% {temp}°C")
                w = gpu_track.width()
                if w > 5: gpu_fill.setFixedWidth(max(2, int(w * util.gpu / 100)))
            except Exception: pass

        # WiFi stats
        try:
            _, wifi_lbl = self._wifi_row
            nets = psutil.net_if_stats()
            addrs = psutil.net_if_addrs()
            best = None
            for name, stats in nets.items():
                if not stats.isup: continue
                if any("wireless" in f.lower() or "wi-fi" in f.lower() or "wi-fi" in name.lower() for f in [name]):
                    best = name
                    break
            if not best:
                for name in nets:
                    if nets[name].isup:
                        best = name
                        break
            if best and best in addrs:
                ipv4 = [a.address for a in addrs[best] if a.family == psutil.AF_LINK or hasattr(a, 'address') and '.' in a.address]
                ip = next((a for a in ipv4 if '.' in a), "N/A")
                wifi_lbl.setText(f"{best} · {ip}")
            else: wifi_lbl.setText("Disconnected")
        except Exception: pass

    def set_llm_status(self, online: bool):
        _, dot, status = self._llm_row
        color = "#00e5cc" if online else "#ff6b6b"
        dot.setStyleSheet(f"background: transparent; color: {color}; font-size: 9px;")
        status.setText("online" if online else "offline")
        status.setStyleSheet(
            f"background: transparent; color: {color}; "
            "font-family: 'Consolas'; font-size: 8pt;"
        )

    def set_page_tint(self, bg: str, border: str): self._accent.setStyleSheet(f"background: {border};")
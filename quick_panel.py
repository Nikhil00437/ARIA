# quick_panel.py — Glassy minimal Quick Actions + System Stats panels

import time, random, psutil, requests

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt5.QtGui import QFont

try:
    import pynvml
    pynvml.nvmlInit()
    HAS_GPU = True
except Exception:
    HAS_GPU = False

from constants import LM_STUDIO_BASE_URL


class _StatsWorker(QThread):
    """Worker thread that gathers system stats without blocking the UI."""
    # Signals to send results back to main thread
    stats_ready = pyqtSignal(float, object)  # cpu, mem
    gpu_ready = pyqtSignal(float)
    disk_ready = pyqtSignal(float)
    wifi_ready = pyqtSignal(str)
    llm_ready = pyqtSignal(bool)

    def run(self):
        try:
            psutil.cpu_percent(interval=None)
            time.sleep(0.3)
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            self.stats_ready.emit(cpu, mem)
        except Exception as e:
            print(f"[SystemPanel] CPU/RAM error: {e}")

        if HAS_GPU:
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                self.gpu_ready.emit(float(util.gpu))
            except Exception as e:
                print(f"[SystemPanel] GPU error: {e}")

        try:
            disk = psutil.disk_usage("C:\\")
            self.disk_ready.emit(disk.percent)
        except Exception as e:
            print(f"[SystemPanel] Disk error: {e}")

        try:
            wifi = self._fetch_wifi()
            self.wifi_ready.emit(wifi)
        except Exception as e:
            print(f"[SystemPanel] WiFi error: {e}")

        # LLM health check
        try:
            url = f"{LM_STUDIO_BASE_URL}/models"
            r = requests.get(url, timeout=3)
            llm_online = r.status_code == 200
        except Exception:
            llm_online = False
        self.llm_ready.emit(llm_online)

    def _fetch_wifi(self):
        iface = self._get_active_iface()
        if not iface:
            return "No iface"
        b = psutil.net_io_counters(pernic=True)
        time.sleep(0.5)
        a = psutil.net_io_counters(pernic=True)
        if iface in b and iface in a:
            dl = (a[iface].bytes_recv - b[iface].bytes_recv) / 1024 * 2
            ul = (a[iface].bytes_sent - b[iface].bytes_sent) / 1024 * 2
            fmt = lambda x: f"{x/1024:.1f}MB/s" if x >= 1024 else f"{x:.0f}KB/s"
            return f"↓ {fmt(dl)}  ↑ {fmt(ul)}"
        return "No data"

    def _get_active_iface(self):
        nets = psutil.net_if_stats()
        for name, s in nets.items():
            if s.isup and "wi-fi" in name.lower():
                return name
        for name, s in nets.items():
            if s.isup and name.lower() not in ("loopback", "lo"):
                return name
        return None


# Action pools
STATIC_ACTIONS = [
    ("⌨️", "Terminal",  "nav",   "terminal"),
    ("🌐", "Browse",    "input", "open "),
]

DYNAMIC_POOLS = [
    [
        ("📝", "Summarize",  "pattern", "summarize"),
        ("💡", "Extract",    "pattern", "extract_wisdom"),
        ("🔍", "Analyze",    "pattern", "analyze_claims"),
        ("✍️", "Improve",    "pattern", "improve_writing"),
        ("📚", "Explain",    "pattern", "explain_code"),
        ("⚡", "TL;DR",      "pattern", "create_5_sentence_summary"),
        ("🧠", "Insights",   "pattern", "extract_insights"),
        ("💭", "Ideas",      "pattern", "extract_ideas"),
    ],
    [
        ("🔎", "GitHub",    "input", "search github "),
        ("📺", "YouTube",   "input", "search youtube "),
        ("📜", "arXiv",     "input", "search arxiv "),
        ("💎", "SO",        "input", "search stackoverflow "),
        ("🤗", "HuggingFace","input","search huggingface "),
        ("📦", "PyPI",      "input", "search pypi "),
    ],
    [
        ("💡", "Quantum",   "cmd", "Explain quantum computing simply"),
        ("🚀", "AI Future", "cmd", "Tell me about the future of AI"),
        ("🔮", "Fun Fact",  "cmd", "Give me a random fun fact"),
        ("🌌", "Space",     "cmd", "Tell me something weird about space"),
        ("🧩", "Paradox",   "cmd", "What's a paradox that breaks your brain?"),
        ("💻", "What do?",  "cmd", "What can you do?"),
    ],
]

#  QuickPanel
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

        # Accent stripe
        self._accent = QFrame()
        self._accent.setFixedHeight(3)
        self._accent.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 rgba(80,140,255,0.7), stop:1 rgba(140,80,255,0.7));"
            "border: none;"
        )
        root.addWidget(self._accent)

        # Header
        header = QWidget()
        header.setObjectName("GlassPanelHeader")
        header.setFixedHeight(40)
        h_lyt = QHBoxLayout(header)
        h_lyt.setContentsMargins(16, 0, 12, 0)

        title = QLabel("QUICK")
        title.setObjectName("GlassPanelTitle")

        self._refresh_btn = QPushButton("↻")
        self._refresh_btn.setFixedSize(40, 40)
        self._refresh_btn.setToolTip("Rotate quick actions")
        self._refresh_btn.setStyleSheet(
            "QPushButton { background: transparent; color: rgba(255,255,255,0.40); "
            "border: none; font-size: 14px; border-radius: 12px; }"
            "QPushButton:hover { background: rgba(120,180,255,0.12); color: rgba(120,180,255,0.9); }"
        )
        self._refresh_btn.clicked.connect(self._rotate)

        h_lyt.addWidget(title)
        h_lyt.addStretch()
        h_lyt.addWidget(self._refresh_btn)
        root.addWidget(header)

        # 2×3 button grid
        grid_wrap = QWidget()
        grid_wrap.setStyleSheet("background: transparent;")
        self._grid = QGridLayout(grid_wrap)
        self._grid.setContentsMargins(12, 12, 12, 12)
        self._grid.setSpacing(8)

        self._actions: list = []
        self._build_actions()
        self._render_buttons()

        root.addWidget(grid_wrap)

        # Auto-rotate every 2 min
        self._timer = QTimer(self)
        self._timer.setInterval(120_000)
        self._timer.timeout.connect(self._rotate)
        self._timer.start()

    def _build_actions(self):
        self._actions = list(STATIC_ACTIONS)
        for pool in DYNAMIC_POOLS: self._actions.append(random.choice(pool))
        while len(self._actions) < 6: self._actions.append(("", "More", "cmd", "What can you do?"))

    def _rotate(self):
        self._build_actions()
        self._render_buttons()

    def _render_buttons(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        for i, (icon, label, atype, value) in enumerate(self._actions[:6]):
            btn = self._make_btn(icon, label, atype, value)
            row, col = divmod(i, 2)
            self._grid.addWidget(btn, row, col)

    def _make_btn(self, icon, label, atype, value):
        btn = QPushButton(f"{icon}\n{label}")
        btn.setObjectName("QuickBtn")
        btn.setFixedHeight(58)
        btn.setFont(QFont("Segoe UI", 9))

        def _clicked():
            if   atype == "pattern": self.pattern_requested.emit(value)
            elif atype == "nav":     self.nav_requested.emit(value)
            elif atype == "input":   self.input_requested.emit(value)
            elif atype == "cmd":     self.cmd_requested.emit(value)

        btn.clicked.connect(_clicked)
        return btn

    def set_page_tint(self, bg: str, border: str): self._accent.setStyleSheet(f"background: {border};")

#  SystemPanel
class SystemPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlassPanel")

        self._collapsed     = False
        self._stats_visible = True
        self._stats_worker  = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Accent stripe
        self._accent = QFrame()
        self._accent.setFixedHeight(3)
        self._accent.setStyleSheet("background: rgba(80,140,255,0.6); border: none;")
        root.addWidget(self._accent)

        # Header (collapsible)
        self._header = QWidget()
        self._header.setObjectName("GlassPanelHeader")
        self._header.setFixedHeight(40)
        self._header.setCursor(Qt.PointingHandCursor)
        h_lyt = QHBoxLayout(self._header)
        h_lyt.setContentsMargins(16, 0, 16, 0)

        title = QLabel("SYSTEM")
        title.setObjectName("GlassPanelTitle")

        self._arrow = QLabel("▾")
        self._arrow.setStyleSheet("background: transparent; color: rgba(255,255,255,0.40); font-size: 8pt;")

        h_lyt.addWidget(title)
        h_lyt.addStretch()
        h_lyt.addWidget(self._arrow)
        root.addWidget(self._header)

        # Stats container
        self._stats_container = QWidget()
        stats_wrap = QWidget()
        stats_wrap.setStyleSheet("background: transparent;")
        stats_lyt = QVBoxLayout(stats_wrap)
        stats_lyt.setContentsMargins(16, 12, 16, 14)
        stats_lyt.setSpacing(11)

        self._cpu_row   = self._make_stat_row("CPU")
        self._ram_row   = self._make_stat_row("RAM")
        self._gpu_row   = self._make_stat_row("GPU") if HAS_GPU else None
        self._disk_row  = self._make_stat_row("Disk")
        self._wifi_row  = self._make_wifi_row()
        self._llm_row   = self._make_llm_row()

        stats_lyt.addLayout(self._cpu_row[0])
        stats_lyt.addLayout(self._ram_row[0])
        if self._gpu_row: stats_lyt.addLayout(self._gpu_row[0])
        stats_lyt.addLayout(self._disk_row[0])
        stats_lyt.addLayout(self._wifi_row[0])
        stats_lyt.addLayout(self._llm_row[0])

        sc_lyt = QVBoxLayout(self._stats_container)
        sc_lyt.setContentsMargins(0, 0, 0, 0)
        sc_lyt.setSpacing(0)
        sc_lyt.addWidget(stats_wrap)

        root.addWidget(self._stats_container)

        self._header.mousePressEvent = self._toggle_collapse

        # Update timer
        self._timer = QTimer(self)
        self._timer.setInterval(15_000)
        self._timer.timeout.connect(self.update_stats)
        self._timer.start()
        QTimer.singleShot(800, self.update_stats)

    def _make_stat_row(self, label):
        row = QHBoxLayout()
        row.setSpacing(8)

        name = QLabel(label)
        name.setFixedWidth(30)
        name.setStyleSheet(
            "background: transparent; color: rgba(255,255,255,0.40); "
            "font-family: 'Cascadia Code', 'Consolas'; font-size: 7.5pt; font-weight: 700;"
        )

        track = QFrame()
        track.setFixedHeight(5)
        track.setMinimumWidth(100)
        track.setObjectName("RailStatBar")
        track.setStyleSheet("background: rgba(255,255,255,0.06); border-radius: 2px; border: none;")

        fill = QFrame(track)
        fill.setFixedHeight(5)
        fill.setObjectName("RailStatFill")
        fill.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 rgba(80,140,255,0.8), stop:1 rgba(140,80,255,0.8)); border-radius: 2px; border: none;"
        )
        fill.setFixedWidth(0)
        fill.move(0, 0)

        pct = QLabel("0%")
        pct.setFixedWidth(32)
        pct.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        pct.setStyleSheet(
            "background: transparent; color: rgba(255,255,255,0.60); "
            "font-family: 'Cascadia Code', 'Consolas'; font-size: 7.5pt; font-weight: 700;"
        )

        row.addWidget(name)
        row.addWidget(track, 1)
        row.addWidget(pct)
        return row, fill, pct, track

    def _make_wifi_row(self):
        row = QHBoxLayout()
        row.setSpacing(8)

        name = QLabel("Net")
        name.setFixedWidth(30)
        name.setStyleSheet(
            "background: transparent; color: rgba(255,255,255,0.40); "
            "font-family: 'Cascadia Code', 'Consolas'; font-size: 7.5pt; font-weight: 700;"
        )

        val = QLabel("—")
        val.setStyleSheet(
            "background: transparent; color: rgba(255,255,255,0.60); "
            "font-family: 'Cascadia Code', 'Consolas'; font-size: 7.5pt;"
        )

        row.addWidget(name)
        row.addWidget(val, 1)
        return row, val

    def _make_llm_row(self):
        row = QHBoxLayout()
        row.setSpacing(6)

        name = QLabel("LLM")
        name.setFixedWidth(30)
        name.setStyleSheet(
            "background: transparent; color: rgba(255,255,255,0.40); "
            "font-family: 'Cascadia Code', 'Consolas'; font-size: 7.5pt; font-weight: 700;"
        )

        dot = QLabel("●")
        dot.setStyleSheet("background: transparent; color: rgba(255,80,80,0.9); font-size: 8px;")

        status = QLabel("offline")
        status.setStyleSheet(
            "background: transparent; color: rgba(255,80,80,0.9); "
            "font-family: 'Cascadia Code', 'Consolas'; font-size: 7.5pt;"
        )

        row.addWidget(name)
        row.addStretch()
        row.addWidget(dot)
        row.addWidget(status)
        return row, dot, status

    def _toggle_collapse(self, _event):
        self._collapsed = not self._collapsed
        self._stats_container.setVisible(not self._collapsed)
        self._arrow.setText("▸" if self._collapsed else "▾")

    def set_visible(self, v: bool):
        self._stats_visible = v
        if v:
            self._timer.start()
            self.update_stats()
        else: self._timer.stop()

    def set_llm_status(self, online: bool):
        _, dot, status = self._llm_row
        color = "rgba(80,200,120,0.9)" if online else "rgba(255,80,80,0.9)"
        dot.setStyleSheet(f"background: transparent; color: {color}; font-size: 8px;")
        status.setText("online" if online else "offline")
        status.setStyleSheet(
            f"background: transparent; color: {color}; "
            "font-family: 'Cascadia Code', 'Consolas'; font-size: 7.5pt;"
        )

    def update_stats(self):
        if not self._stats_visible or self._collapsed:
            print(f"[SystemPanel] update_stats skipped: visible={self._stats_visible}, collapsed={self._collapsed}")
            return

        # Clean up any previous finished worker
        if hasattr(self, '_stats_worker') and self._stats_worker is not None:
            try:
                if self._stats_worker.isFinished():
                    self._stats_worker.deleteLater()
                    self._stats_worker = None
            except RuntimeError:
                self._stats_worker = None

        # Create and start new worker
        self._stats_worker = _StatsWorker()
        self._stats_worker.stats_ready.connect(self._apply_cpu_ram)
        if self._gpu_row:
            self._stats_worker.gpu_ready.connect(self._apply_gpu)
        self._stats_worker.disk_ready.connect(self._apply_disk)
        self._stats_worker.wifi_ready.connect(self._apply_wifi)
        self._stats_worker.llm_ready.connect(self.set_llm_status)
        self._stats_worker.finished.connect(self._on_worker_finished)
        self._stats_worker.start()

    def _on_worker_finished(self):
        """Called when stats worker completes."""
        if hasattr(self, '_stats_worker') and self._stats_worker is not None:
            try:
                self._stats_worker.deleteLater()
            except RuntimeError:
                pass
            self._stats_worker = None

    def _apply_cpu_ram(self, cpu, mem):
        _, cpu_fill, cpu_pct, cpu_track = self._cpu_row
        _, ram_fill, ram_pct, ram_track  = self._ram_row
        cpu_pct.setText(f"{cpu:.1f}%")
        ram_pct.setText(f"{mem.percent:.1f}%")
        
        for fill, track, pct_val in [
            (cpu_fill, cpu_track, cpu),
            (ram_fill, ram_track, mem.percent),
        ]:
            w = track.width()
            if w <= 5:
                w = 120
            new_width = max(2, int(w * pct_val / 100))
            fill.setFixedWidth(new_width)
            fill.setGeometry(0, 0, new_width, fill.height())
            fill.repaint()

    def _apply_gpu(self, gpu_pct):
        _, fill, lbl, track = self._gpu_row
        lbl.setText(f"{gpu_pct:.1f}%")
        w = track.width()
        if w <= 5:
            w = 120
        fill.setFixedWidth(max(2, int(w * gpu_pct / 100)))

    def _apply_disk(self, pct):
        _, fill, lbl, track = self._disk_row
        lbl.setText(f"{pct:.0f}%")
        w = track.width()
        if w <= 5:
            w = 120
        fill.setFixedWidth(max(2, int(w * pct / 100)))

    def _apply_wifi(self, text):
        _, lbl = self._wifi_row
        lbl.setText(text)

    def set_page_tint(self, bg: str, border: str):
        self._accent.setStyleSheet(f"background: {border}; border: none;")

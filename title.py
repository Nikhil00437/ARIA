# title.py — Glassy minimal frosted title bar

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class TitleBar(QWidget):
    settings_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(48)
        self._drag_pos = None
        self._parent_window = parent

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 6, 0)
        layout.setSpacing(0)

        # ── Left: logo + wordmark ─────────────────────────────────
        left = QHBoxLayout()
        left.setSpacing(10)

        self._logo = QLabel("◈")
        self._logo.setObjectName("TitleLogo")

        self._title = QLabel("ARIA")
        self._title.setObjectName("TitleLabel")

        self._subtitle = QLabel("Runtime Intelligence")
        self._subtitle.setObjectName("TitleSubtitle")

        # Soft vertical divider
        div = QLabel("·")
        div.setStyleSheet(
            "color: rgba(255,255,255,0.18); font-size: 14px; "
            "padding: 0 4px; background: transparent;"
        )

        left.addWidget(self._logo)
        left.addWidget(self._title)
        left.addWidget(div)
        left.addWidget(self._subtitle)
        left.addStretch()

        layout.addLayout(left, 1)

        # ── Right: controls ───────────────────────────────────────
        right = QHBoxLayout()
        right.setSpacing(2)

        self._btn_settings = self._btn("⚙", "TitleBtnSettings", self._open_settings)
        sep = QLabel()
        sep.setFixedWidth(1)
        sep.setFixedHeight(18)
        sep.setStyleSheet("background: rgba(255,255,255,0.10); margin: 0 6px;")

        self._btn_min   = self._btn("⎯", "TitleBtn", self._minimize)
        self._btn_max   = self._btn("□", "TitleBtn", self._maximize)
        self._btn_close = self._btn("✕", "TitleBtnClose", self._close_win)

        right.addWidget(self._btn_settings)
        right.addWidget(sep)
        right.addWidget(self._btn_min)
        right.addWidget(self._btn_max)
        right.addWidget(self._btn_close)

        layout.addLayout(right)

    def _btn(self, text, obj_name, slot):
        b = QPushButton(text)
        b.setObjectName(obj_name)
        b.setFixedSize(44, 44)
        b.clicked.connect(slot)
        return b

    def _open_settings(self): self.settings_requested.emit()

    def _minimize(self):
        if self._parent_window: self._parent_window.showMinimized()

    def _maximize(self):
        if self._parent_window:
            if self._parent_window.isMaximized():
                self._parent_window.showNormal()
                self._btn_max.setText("□")
            else:
                self._parent_window.showMaximized()
                self._btn_max.setText("❐")

    def _close_win(self):
        if self._parent_window: self._parent_window.close()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPos() - self._parent_window.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and self._drag_pos:
            self._parent_window.move(e.globalPos() - self._drag_pos)

    def mouseDoubleClickEvent(self, e): self._maximize()

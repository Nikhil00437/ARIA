# title.py — Clean minimal title bar

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal

class TitleBar(QWidget):
    settings_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(44)
        self._drag_pos  = None
        self._parent_window = parent

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 0, 4, 0)
        layout.setSpacing(0)

        # Left: logo + title
        left_row = QHBoxLayout()
        left_row.setSpacing(10)

        self._logo = QLabel("◈")
        self._logo.setObjectName("TitleLogo")

        self._title = QLabel("ARIA")
        self._title.setObjectName("TitleLabel")

        self._subtitle = QLabel("Runtime Intelligence")
        self._subtitle.setObjectName("TitleSubtitle")

        left_row.addWidget(self._logo)
        left_row.addWidget(self._title)
        left_row.addWidget(self._subtitle)
        left_row.addStretch()

        layout.addLayout(left_row, 1)

        # Right: settings + window controls
        right_row = QHBoxLayout()
        right_row.setSpacing(0)

        self._btn_settings = self._make_btn("⚙", "TitleBtnSettings", self._open_settings)

        sep = QLabel("│")
        sep.setStyleSheet("color: rgba(255,255,255,0.08); font-size: 14px; padding: 0 6px; background: transparent;")

        self._btn_min   = self._make_btn("─", "TitleBtn",      self._minimize)
        self._btn_max   = self._make_btn("□", "TitleBtn",      self._maximize)
        self._btn_close = self._make_btn("✕", "TitleBtnClose", self._close_win)

        right_row.addWidget(self._btn_settings)
        right_row.addWidget(sep)
        right_row.addWidget(self._btn_min)
        right_row.addWidget(self._btn_max)
        right_row.addWidget(self._btn_close)

        layout.addLayout(right_row)

    def _make_btn(self, text: str, obj_name: str, slot) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName(obj_name)
        btn.setFixedSize(46, 44)
        btn.clicked.connect(slot)
        return btn

    # Actions
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

    # Drag to move
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: self._drag_pos = event.globalPos() - self._parent_window.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos: self._parent_window.move(event.globalPos() - self._drag_pos)

    def mouseDoubleClickEvent(self, event): self._maximize()
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt

class TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(36)
        self._drag_pos = None
        self._parent_window = parent

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(0)
        # Logo + title
        self._logo = QLabel("◈")
        self._logo.setStyleSheet("color: inherit; font-size: 18px; padding-right: 6px;")

        self._title = QLabel("ARIA")
        self._title.setObjectName("TitleLabel")

        self._subtitle = QLabel("  —  Advanced Runtime Intelligence Assistant")
        self._subtitle.setObjectName("SysInfo")
        # Window buttons
        self._btn_min   = self._make_btn("—", "TitleBtn",      self._minimize)
        self._btn_max   = self._make_btn("□", "TitleBtn",      self._maximize)
        self._btn_close = self._make_btn("✕", "TitleBtnClose", self._close)

        layout.addWidget(self._logo)
        layout.addWidget(self._title)
        layout.addWidget(self._subtitle)
        layout.addStretch()
        layout.addWidget(self._btn_min)
        layout.addWidget(self._btn_max)
        layout.addWidget(self._btn_close)

    def _make_btn(self, text, obj_name, slot):
        btn = QPushButton(text)
        btn.setObjectName(obj_name)
        btn.setFixedSize(42, 36)
        btn.clicked.connect(slot)
        return btn

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

    def _close(self):
        if self._parent_window: self._parent_window.close()
    # Drag to move
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: self._drag_pos = event.globalPos() - self._parent_window.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos: self._parent_window.move(event.globalPos() - self._drag_pos)

    def mouseDoubleClickEvent(self, event): self._maximize()
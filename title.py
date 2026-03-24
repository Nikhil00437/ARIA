from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt

class TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(46)
        self._drag_pos = None
        self._parent_window = parent

        # Outer layout: title row + accent line
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Title row ───────────────────────────────────────────────────────
        row_widget = QWidget()
        row_widget.setObjectName("TitleBar")
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(16, 0, 0, 0)
        row_layout.setSpacing(0)

        # Logo mark
        self._mark = QLabel("◈")
        self._mark.setStyleSheet(
            "color: transparent;"
            "background: transparent;"
            "font-size: 14pt;"
            "padding-right: 10px;"
            "padding-left: 2px;"
        )
        # Because we can't do text gradients in QSS, we style it with accent color
        self._mark.setStyleSheet(
            "background: transparent;"
            "font-size: 13pt;"
            "padding-right: 10px;"
        )

        # ARIA title
        self._title = QLabel("ARIA")
        self._title.setObjectName("TitleLabel")

        # Subtitle
        self._subtitle = QLabel("  ·  Runtime Intelligence")
        self._subtitle.setObjectName("TitleSubtitle")

        # Separator stretch
        row_layout.addWidget(self._mark)
        row_layout.addWidget(self._title)
        row_layout.addWidget(self._subtitle)
        row_layout.addStretch()

        # Window control buttons
        self._btn_min   = self._make_btn("⎯",  "TitleBtn",      self._minimize)
        self._btn_max   = self._make_btn("⬜",  "TitleBtn",      self._maximize)
        self._btn_close = self._make_btn("✕",  "TitleBtnClose", self._close)

        row_layout.addWidget(self._btn_min)
        row_layout.addWidget(self._btn_max)
        row_layout.addWidget(self._btn_close)

        # ── Accent line ─────────────────────────────────────────────────────
        self._accent_line = QWidget()
        self._accent_line.setObjectName("TitleAccentLine")
        self._accent_line.setFixedHeight(1)

        outer.addWidget(row_widget, 1)
        outer.addWidget(self._accent_line)

    def _make_btn(self, text: str, obj_name: str, slot) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName(obj_name)
        btn.setFixedSize(46, 45)
        btn.clicked.connect(slot)
        return btn

    # ── Window actions ───────────────────────────────────────────────────────
    def _minimize(self):
        if self._parent_window:
            self._parent_window.showMinimized()

    def _maximize(self):
        if self._parent_window:
            if self._parent_window.isMaximized():
                self._parent_window.showNormal()
                self._btn_max.setText("⬜")
            else:
                self._parent_window.showMaximized()
                self._btn_max.setText("❐")

    def _close(self):
        if self._parent_window:
            self._parent_window.close()

    # ── Drag to move ─────────────────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self._parent_window.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            self._parent_window.move(event.globalPos() - self._drag_pos)

    def mouseDoubleClickEvent(self, event):
        self._maximize()
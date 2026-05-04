# settings_dialog.py — Glassy minimal Settings (theme picker)

from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QLinearGradient

COLOR_THEMES = [
    {
        "id":      "minimal",
        "name":    "Minimal",
        "tagline": "Frosted light · Sky blue",
        "swatches": ["#eef4fb", "#f5f9fe", "#0284c7", "#0c1a2e", "#ccdcef"],
    },
    {
        "id":      "cyber",
        "name":    "Cyber",
        "tagline": "Deep dark · Electric teal",
        "swatches": ["#07090f", "#0b1018", "#00e5cc", "#dce6f4", "#13243a"],
    },
    {
        "id":      "classic",
        "name":    "Classic",
        "tagline": "Monochrome · Silver",
        "swatches": ["#101010", "#181818", "#c0c0c0", "#e8e8e8", "#2a2a2a"],
    },
]


class ColorCard(QWidget):
    selected = pyqtSignal(str)

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self._id = theme["id"]
        self._selected = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(168, 106)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        name = QLabel(theme["name"])
        name.setStyleSheet(
            "color: rgba(255,255,255,0.92); font-size: 13px; font-weight: 700;"
            "font-family: 'Segoe UI Variable', 'Segoe UI'; background: transparent;"
        )
        layout.addWidget(name)

        tag = QLabel(theme["tagline"])
        tag.setStyleSheet(
            "color: rgba(255,255,255,0.40); font-size: 8.5px;"
            "font-family: 'Cascadia Code', 'Consolas'; background: transparent;"
        )
        layout.addWidget(tag)
        layout.addStretch()

        row = QHBoxLayout()
        row.setSpacing(5)
        for color in theme["swatches"]:
            dot = QFrame()
            dot.setFixedSize(14, 14)
            dot.setStyleSheet(
                f"background: {color}; border-radius: 7px;"
                "border: 1px solid rgba(255,255,255,0.15);"
            )
            row.addWidget(dot)
        row.addStretch()
        layout.addLayout(row)

        self._refresh()

    def set_selected(self, v: bool):
        self._selected = v
        self._refresh()

    def _refresh(self):
        if self._selected:
            self.setStyleSheet(
                "ColorCard { background: rgba(120,180,255,0.12);"
                "border: 1.5px solid rgba(120,180,255,0.45); border-radius: 16px; }"
            )
        else:
            self.setStyleSheet(
                "ColorCard { background: rgba(255,255,255,0.08);"
                "border: 1px solid rgba(255,255,255,0.15); border-radius: 16px; }"
                "ColorCard:hover { background: rgba(255,255,255,0.14);"
                "border-color: rgba(120,180,255,0.30); }"
            )

    def mousePressEvent(self, _):
        self.selected.emit(self._id)


class SettingsDialog(QDialog):
    theme_changed = pyqtSignal(str)

    def __init__(self, current_color: str = "minimal", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)
        self.setFixedSize(596, 300)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._color = current_color
        self._cards: dict[str, ColorCard] = {}
        self._build()
        self._select(current_color)

    def paintEvent(self, event):
        """Paint a dark gradient behind the dialog glass."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, QColor(8, 12, 28, 248))
        grad.setColorAt(1.0, QColor(18, 22, 44, 248))
        painter.fillRect(self.rect(), grad)
        painter.end()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        box = QWidget()
        box.setObjectName("SettingsBox")
        outer.addWidget(box)

        root = QVBoxLayout(box)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title bar
        tb = QWidget()
        tb.setObjectName("SettingsTB")
        tb.setFixedHeight(50)
        tb_lyt = QHBoxLayout(tb)
        tb_lyt.setContentsMargins(22, 0, 14, 0)

        icon = QLabel("⚙")
        icon.setStyleSheet("color: rgba(120,180,255,0.9); font-size: 15px; background: transparent;")

        title = QLabel("Settings")
        title.setStyleSheet(
            "color: rgba(255,255,255,0.92); font-size: 14px; font-weight: 700;"
            "font-family: 'Segoe UI Variable', 'Segoe UI';"
            "letter-spacing: 0.5px; background: transparent;"
        )

        close = QPushButton("✕")
        close.setObjectName("SCloseBtn")
        close.setFixedSize(30, 30)
        close.clicked.connect(self.reject)

        tb_lyt.addWidget(icon)
        tb_lyt.addSpacing(8)
        tb_lyt.addWidget(title)
        tb_lyt.addStretch()
        tb_lyt.addWidget(close)
        root.addWidget(tb)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background: rgba(255,255,255,0.10); border: none;")
        root.addWidget(divider)

        # Body
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        body_lyt = QVBoxLayout(body)
        body_lyt.setContentsMargins(22, 18, 22, 18)
        body_lyt.setSpacing(12)

        sec = QLabel("COLOR THEME")
        sec.setStyleSheet(
            "color: rgba(255,255,255,0.40); font-size: 8.5px; font-weight: 700;"
            "letter-spacing: 3px; font-family: 'Cascadia Code', 'Consolas'; background: transparent;"
        )
        body_lyt.addWidget(sec)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        for t in COLOR_THEMES:
            card = ColorCard(t)
            card.selected.connect(self._select)
            self._cards[t["id"]] = card
            cards_row.addWidget(card)
        cards_row.addStretch()
        body_lyt.addLayout(cards_row)
        body_lyt.addStretch()
        root.addWidget(body, 1)

        # Footer
        fd = QFrame()
        fd.setFixedHeight(1)
        fd.setStyleSheet("background: rgba(255,255,255,0.10); border: none;")
        root.addWidget(fd)

        foot = QWidget()
        foot.setObjectName("SettingsFoot")
        foot.setFixedHeight(54)
        foot_lyt = QHBoxLayout(foot)
        foot_lyt.setContentsMargins(22, 0, 22, 0)

        self._preview = QLabel("")
        self._preview.setStyleSheet(
            "color: rgba(255,255,255,0.40); font-size: 10px; "
            "font-family: 'Cascadia Code', 'Consolas'; background: transparent;"
        )
        foot_lyt.addWidget(self._preview)
        foot_lyt.addStretch()

        cancel = QPushButton("Cancel")
        cancel.setObjectName("SCancelBtn")
        cancel.setFixedSize(88, 34)
        cancel.clicked.connect(self.reject)

        apply = QPushButton("Apply")
        apply.setObjectName("SApplyBtn")
        apply.setFixedSize(88, 34)
        apply.clicked.connect(self._apply)

        foot_lyt.addWidget(cancel)
        foot_lyt.addSpacing(8)
        foot_lyt.addWidget(apply)
        root.addWidget(foot)

        self.setStyleSheet("""
            #SettingsBox {
                background: rgba(20, 25, 45, 0.95);
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 20px;
            }
            #SettingsTB {
                background: rgba(255,255,255,0.04);
                border-radius: 20px 20px 0 0;
            }
            #SettingsFoot {
                background: rgba(255,255,255,0.04);
                border-radius: 0 0 20px 20px;
            }
            #SCloseBtn {
                background: rgba(255,255,255,0.08);
                color: rgba(255,255,255,0.50);
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 8px;
                font-size: 11px;
            }
            #SCloseBtn:hover {
                background: rgba(255,60,60,0.20);
                color: #ff8888;
                border-color: rgba(255,60,60,0.35);
            }
            #SCancelBtn {
                background: rgba(255,255,255,0.10);
                color: rgba(255,255,255,0.60);
                border: 1px solid rgba(255,255,255,0.18);
                border-radius: 10px;
                font-size: 12px;
                font-family: 'Segoe UI Variable', 'Segoe UI';
                font-weight: 500;
            }
            #SCancelBtn:hover {
                background: rgba(255,255,255,0.20);
                color: rgba(255,255,255,0.90);
            }
            #SApplyBtn {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(80,140,255,0.7), stop:1 rgba(140,80,255,0.7));
                color: #ffffff;
                border: none;
                border-radius: 10px;
                font-size: 12px;
                font-family: 'Segoe UI Variable', 'Segoe UI';
                font-weight: 700;
            }
            #SApplyBtn:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 rgba(140,80,255,0.8), stop:1 rgba(80,140,255,0.8));
            }
        """)

    def _select(self, color_id: str):
        self._color = color_id
        for cid, card in self._cards.items():
            card.set_selected(cid == color_id)
        name = next((t["name"] for t in COLOR_THEMES if t["id"] == color_id), color_id)
        self._preview.setText(f"Selected: {name}")

    def _apply(self):
        self.theme_changed.emit(self._color)
        self.accept()

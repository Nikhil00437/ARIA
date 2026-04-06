# settings_dialog.py — ARIA Settings (color theme picker)

from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal

COLOR_THEMES = [
    {
        "id":      "cyber",
        "name":    "Cyber",
        "tagline": "Deep charcoal · Rose coral",
        "swatches": ["#111214", "#1a1d21", "#ef9a9a", "#e8eaed", "#2a2d31"],
    },
    {
        "id":      "minimal",
        "name":    "Minimal",
        "tagline": "Frosted light · Warm rose",
        "swatches": ["#f5f0f0", "#ffffff", "#e57373", "#1a1214", "#ddd0d0"],
    },
    {
        "id":      "classic",
        "name":    "Classic",
        "tagline": "Monochrome · Silver",
        "swatches": ["#141414", "#1e1e1e", "#ef9a9a", "#e0e0e0", "#2a2a2a"],
    },
]


class ColorCard(QWidget):
    selected = pyqtSignal(str)

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self._id = theme["id"]
        self._selected = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(160, 100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        name = QLabel(theme["name"])
        name.setStyleSheet(
            "color: #e8eaed; font-size: 13px; font-weight: 700;"
            "font-family: 'Segoe UI'; background: transparent;"
        )
        layout.addWidget(name)

        tag = QLabel(theme["tagline"])
        tag.setStyleSheet(
            "color: #5f6368; font-size: 9px;"
            "font-family: 'Consolas'; background: transparent;"
        )
        layout.addWidget(tag)
        layout.addStretch()

        row = QHBoxLayout()
        row.setSpacing(4)
        for color in theme["swatches"]:
            dot = QFrame()
            dot.setFixedSize(14, 14)
            dot.setStyleSheet(
                f"background: {color}; border-radius: 7px;"
                f"border: 1px solid rgba(255,255,255,0.12);"
            )
            row.addWidget(dot)
        row.addStretch()
        layout.addLayout(row)
        self._refresh()

    def set_selected(self, v: bool):
        self._selected = v
        self._refresh()

    def _refresh(self):
        if self._selected: self.setStyleSheet(
                "ColorCard { background: rgba(239,154,154,0.1);"
                "border: 1.5px solid rgba(239,154,154,0.55); border-radius: 14px; }"
            )
        else: self.setStyleSheet(
                "ColorCard { background: rgba(255,255,255,0.03);"
                "border: 1px solid rgba(255,255,255,0.07); border-radius: 14px; }"
                "ColorCard:hover { background: rgba(255,255,255,0.06);"
                "border-color: rgba(239,154,154,0.3); }"
            )

    def mousePressEvent(self, _): self.selected.emit(self._id)

class SettingsDialog(QDialog):
    theme_changed = pyqtSignal(str)   # color_theme_id

    def __init__(self, current_color: str = "cyber", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)
        self.setFixedSize(580, 320)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._color = current_color
        self._cards: dict[str, ColorCard] = {}
        self._build()
        self._select(current_color)

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
        icon.setStyleSheet("color:#ef9a9a;font-size:15px;background:transparent;")
        title = QLabel("Settings")
        title.setStyleSheet(
            "color:#e8eaed;font-size:14px;font-weight:700;"
            "font-family:'Segoe UI';letter-spacing:0.5px;background:transparent;"
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

        # Divider
        d = QFrame()
        d.setFixedHeight(1)
        d.setStyleSheet("background:rgba(255,255,255,0.07);")
        root.addWidget(d)

        # Body
        body = QWidget()
        body.setStyleSheet("background:transparent;")
        body_lyt = QVBoxLayout(body)
        body_lyt.setContentsMargins(22, 18, 22, 18)
        body_lyt.setSpacing(14)

        sec = QLabel("COLOR THEME")
        sec.setStyleSheet(
            "color:#5f6368;font-size:9px;font-weight:700;"
            "letter-spacing:3px;font-family:'Consolas';background:transparent;"
        )
        body_lyt.addWidget(sec)

        sub = QLabel("Pick a palette. Applies instantly across the whole UI.")
        sub.setStyleSheet("color:#3a3a4a;font-size:11px;font-family:'Segoe UI';background:transparent;")
        body_lyt.addWidget(sub)

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
        fd.setStyleSheet("background:rgba(255,255,255,0.07);")
        root.addWidget(fd)

        foot = QWidget()
        foot.setObjectName("SettingsFoot")
        foot.setFixedHeight(54)
        foot_lyt = QHBoxLayout(foot)
        foot_lyt.setContentsMargins(22, 0, 22, 0)

        self._preview = QLabel("")
        self._preview.setStyleSheet(
            "color:#5f6368;font-size:10px;font-family:'Consolas';background:transparent;"
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
                background: #111216;
                border: 1px solid rgba(255,255,255,0.09);
                border-radius: 18px;
            }
            #SettingsTB {
                background: #16181c;
                border-radius: 18px 18px 0 0;
            }
            #SettingsFoot {
                background: #0e0f13;
                border-radius: 0 0 18px 18px;
            }
            #SCloseBtn {
                background: rgba(255,255,255,0.05);
                color: #5f6368; border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px; font-size: 11px;
            }
            #SCloseBtn:hover {
                background: rgba(200,40,40,0.18); color: #ef5350;
                border-color: rgba(200,40,40,0.35);
            }
            #SCancelBtn {
                background: rgba(255,255,255,0.04); color: #5f6368;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px; font-size: 12px;
                font-family: 'Segoe UI'; font-weight: 500;
            }
            #SCancelBtn:hover { background: rgba(255,255,255,0.08); color: #aaa; }
            #SApplyBtn {
                background: #ef9a9a; color: #111; border: none;
                border-radius: 10px; font-size: 12px;
                font-family: 'Segoe UI'; font-weight: 700;
            }
            #SApplyBtn:hover { background: #e57373; }
        """)

    def _select(self, color_id: str):
        self._color = color_id
        for cid, card in self._cards.items(): card.set_selected(cid == color_id)
        name = next((t["name"] for t in COLOR_THEMES if t["id"] == color_id), color_id)
        self._preview.setText(f"Theme: {name}")

    def _apply(self):
        self.theme_changed.emit(self._color)
        self.accept()
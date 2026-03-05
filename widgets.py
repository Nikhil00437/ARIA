import re
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt5.QtGui import QFont

class CollapsibleSection(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._collapsed = False
        self.setObjectName("collapsibleSection")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.toggle_btn = QPushButton(f"  ▾  {title}")
        self.toggle_btn.setObjectName("collapseToggle")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setFont(QFont("Consolas", 9, QFont.Bold))
        self.toggle_btn.clicked.connect(self._toggle)
        outer.addWidget(self.toggle_btn)

        self.content = QWidget()
        self.content.setObjectName("collapseContent")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.setSpacing(6)
        outer.addWidget(self.content)

    def add_row(self, buttons: list):
        row = QHBoxLayout()
        row.setSpacing(6)
        for btn in buttons:
            row.addWidget(btn)
        self.content_layout.addLayout(row)

    def _toggle(self):
        self._collapsed = not self._collapsed
        self.content.setVisible(not self._collapsed)
        arrow = "▸" if self._collapsed else "▾"
        self.toggle_btn.setText(re.sub(r"[▾▸]", arrow, self.toggle_btn.text()))

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer


class CollapsibleSection(QWidget):
    # A section widget with a toggle-able body.
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._expanded = True

        self._toggle_btn = QPushButton(f"▾  {title}")
        self._toggle_btn.setObjectName("NavBtn")
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setChecked(True)
        self._toggle_btn.clicked.connect(self._toggle)
        self._toggle_btn.setStyleSheet("text-align: left; font-weight: 600;")

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(8, 4, 8, 4)
        self._content_layout.setSpacing(4)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._toggle_btn)
        layout.addWidget(self._content)

    def add_widget(self, widget: QWidget): self._content_layout.addWidget(widget)

    def _toggle(self):
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        arrow = "▾" if self._expanded else "▸"
        text = self._toggle_btn.text()
        self._toggle_btn.setText(arrow + text[1:])


class StatusBar(QWidget):
    # Slim bottom status bar.
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StatusBar")
        self.setFixedHeight(26)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(10)

        self._dot = QLabel("●")
        self._dot.setObjectName("StatusDot")
        self._dot.setFixedWidth(14)

        self._status_label = QLabel("Initializing...")
        self._status_label.setObjectName("StatusLabel")

        self._llm_label = QLabel("LLM  ·  –")
        self._llm_label.setObjectName("LLMLabel")
        self._llm_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        layout.addWidget(self._dot)
        layout.addWidget(self._status_label, 1)
        layout.addWidget(self._llm_label)

    def set_status(self, text: str): self._status_label.setText(text)

    def set_online(self, online: bool):
        self._dot.setObjectName("StatusDot" if online else "StatusDotOffline")
        self._dot.style().unpolish(self._dot)
        self._dot.style().polish(self._dot)

    def set_llm(self, model: str): self._llm_label.setText(f"⬡  {model}")


class TypingIndicator(QLabel):
    # An animated 'ARIA is thinking' label.
    _FRAMES = ["·  ·  ·", "●  ·  ·", "●  ●  ·", "●  ●  ●"]

    def __init__(self, parent=None):
        super().__init__("", parent)
        self.setObjectName("TypingIndicator")
        self._timer_id = None
        self._frame = 0

    def start(self):
        self.show()
        if not self._timer_id: self._timer_id = self.startTimer(400)

    def stop(self):
        if self._timer_id:
            self.killTimer(self._timer_id)
            self._timer_id = None
        self.setText("")
        self.hide()

    def timerEvent(self, event):
        self._frame = (self._frame + 1) % len(self._FRAMES)
        self.setText(f"  aria  {self._FRAMES[self._frame]}")

class ConfidenceBadge(QLabel):
    # Small pill badge showing confidence percentage.# 
    def __init__(self, confidence: float, parent=None):
        pct = int(confidence * 100)
        super().__init__(f"{pct}%", parent)

        if pct >= 85: color, bg = "#00e5cc", "#00e5cc15"
        elif pct >= 65: color, bg = "#f59e0b", "#f59e0b15"
        else: color, bg = "#ef4444", "#ef444415"

        self.setStyleSheet(
            f"background: {bg};"
            f"color: {color};"
            f"border: 1px solid {color}55;"
            "border-radius: 10px;"
            "padding: 2px 8px;"
            "font-size: 8pt;"
            "font-weight: 700;"
            "font-family: 'Cascadia Code', 'Consolas', monospace;"
            "letter-spacing: 0.5px;"
        )

class Separator(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Plain)
        self.setStyleSheet("background: transparent; border: none; border-top: 1px solid #13243a;")
        self.setFixedHeight(1)
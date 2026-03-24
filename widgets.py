from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame
from PyQt5.QtCore import Qt

class CollapsibleSection(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._expanded = True
        # Header button
        self._toggle_btn = QPushButton(f"▼  {title}")
        self._toggle_btn.setObjectName("NavBtn")
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setChecked(True)
        self._toggle_btn.clicked.connect(self._toggle)
        self._toggle_btn.setStyleSheet("text-align: left; font-weight: bold;")
        # Content widget
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(8, 4, 8, 4)
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._toggle_btn)
        layout.addWidget(self._content)

    def add_widget(self, widget: QWidget): self._content_layout.addWidget(widget)

    def _toggle(self):
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        self._toggle_btn.setText(
            ("▼  " if self._expanded else "▶  ") + self._toggle_btn.text()[3:]
        )

class StatusBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StatusBar")
        self.setFixedHeight(24)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(6)

        self._dot = QLabel("●")
        self._dot.setObjectName("StatusDot")

        self._status_label = QLabel("Initializing...")

        self._llm_label = QLabel("LLM: –")
        self._llm_label.setAlignment(Qt.AlignRight)

        layout.addWidget(self._dot)
        layout.addWidget(self._status_label, 1)
        layout.addWidget(self._llm_label)

    def set_status(self, text: str): self._status_label.setText(text)

    def set_online(self, online: bool):
        self._dot.setObjectName("StatusDot" if online else "StatusDotOffline")
        self._dot.style().unpolish(self._dot)
        self._dot.style().polish(self._dot)

    def set_llm(self, model: str): self._llm_label.setText(f"LLM: {model}")

class TypingIndicator(QLabel):
    def __init__(self, parent=None):
        super().__init__("", parent)
        self.setObjectName("TypingIndicator")
        self._timer_id = None
        self._dots = 0

    def start(self):
        self.show()
        self._timer_id = self.startTimer(500)

    def stop(self):
        if self._timer_id:
            self.killTimer(self._timer_id)
            self._timer_id = None
        self.setText("")
        self.hide()

    def timerEvent(self, event):
        self._dots = (self._dots + 1) % 4
        self.setText("ARIA is thinking" + "." * self._dots)

class ConfidenceBadge(QLabel):
    def __init__(self, confidence: float, parent=None):
        super().__init__(f"{confidence:.0%}", parent)
        pct = int(confidence * 100)
        if pct >= 85: color = "#00ff88"
        elif pct >= 70: color = "#ffaa00"
        else: color = "#ff6666"
        self.setStyleSheet(
            f"background: {color}22; color: {color}; "
            f"border: 1px solid {color}; border-radius: 10px; "
            f"padding: 2px 8px; font-size: 11px; font-weight: bold;"
        )

class Separator(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)
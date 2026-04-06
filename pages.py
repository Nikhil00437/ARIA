from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFileDialog, QHBoxLayout, QScrollArea, QLabel, QPushButton, QLineEdit, QSizePolicy, QPlainTextEdit, QTextEdit, QFrame
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QTextCursor, QFont
from widgets import TypingIndicator

#  Chat Page
class ChatPage(QWidget):
    message_submitted  = pyqtSignal(str)
    suggestion_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ChatPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Accent bar
        self._accent = QFrame()
        self._accent.setFixedHeight(3)
        self._accent.setStyleSheet("background: #00e5cc;")
        layout.addWidget(self._accent)

        # Message scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setObjectName("ChatArea")
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QScrollArea.NoFrame)

        self._msg_container = QWidget()
        self._msg_container.setObjectName("ChatArea")
        self._msg_layout = QVBoxLayout(self._msg_container)
        self._msg_layout.setContentsMargins(28, 24, 28, 16)
        self._msg_layout.setSpacing(14)
        self._msg_layout.addStretch()

        self._scroll.setWidget(self._msg_container)

        # Typing indicator
        self._typing = TypingIndicator()
        self._typing.hide()
        self._typing.setFixedHeight(30)

        # STT status
        self._stt_status = QLabel("")
        self._stt_status.setObjectName("STTStatus")
        self._stt_status.setFixedHeight(24)
        self._stt_status.hide()

        # Streaming display
        self.chat_display = QTextEdit()
        self.chat_display.setObjectName("ChatDisplay")
        self.chat_display.setReadOnly(True)
        self.chat_display.setMaximumHeight(200)
        self.chat_display.hide()

        # Suggestions row
        self._suggestions_widget = QWidget()
        self._suggestions_widget.setObjectName("SuggestionsRow")
        self._suggestions_layout = QHBoxLayout(self._suggestions_widget)
        self._suggestions_layout.setContentsMargins(28, 8, 28, 4)
        self._suggestions_layout.setSpacing(10)
        self._suggestions_layout.addStretch()

        # Input area
        input_widget = QWidget()
        input_widget.setObjectName("InputArea")
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(20, 12, 20, 18)
        input_layout.setSpacing(8)

        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        self._input = QLineEdit()
        self._input.setObjectName("ChatInput")
        self._input.setPlaceholderText("Message ARIA…")
        self._input.setMinimumHeight(44)
        self._input.returnPressed.connect(self._submit)

        self._send_btn = QPushButton("Send")
        self._send_btn.setObjectName("SendBtn")
        self._send_btn.setFixedSize(80, 44)
        self._send_btn.clicked.connect(self._submit)

        input_row.addWidget(self._input, 1)
        input_row.addWidget(self._send_btn)

        input_layout.addWidget(self._suggestions_widget)
        input_layout.addLayout(input_row)

        # Assembly
        layout.addWidget(self._scroll, 1)
        layout.addWidget(self.chat_display)
        layout.addWidget(self._stt_status)
        layout.addWidget(self._typing)
        layout.addWidget(input_widget)

        self._stream_buffer: str = ""

    def _submit(self):
        text = self._input.text().strip()
        if text:
            self._input.clear()
            self.message_submitted.emit(text)

    def add_message(self, role: str, text: str):
        is_user = (role == "user")
        outer_widget = QWidget()
        outer_layout = QHBoxLayout(outer_widget)
        outer_layout.setContentsMargins(0, 2, 0, 2)
        outer_layout.setSpacing(0)

        block = QWidget()
        block_layout = QVBoxLayout(block)
        block_layout.setContentsMargins(0, 0, 0, 0)
        block_layout.setSpacing(4)

        role_label = QLabel("YOU" if is_user else "ARIA")
        role_label.setObjectName("MessageRole")
        if is_user: role_label.setAlignment(Qt.AlignRight)
        else: role_label.setAlignment(Qt.AlignLeft)

        bubble = QLabel(text)
        bubble.setObjectName("UserBubble" if is_user else "AiBubble")
        bubble.setWordWrap(True)
        bubble.setTextFormat(Qt.MarkdownText)
        bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bubble.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        block_layout.addWidget(role_label)
        block_layout.addWidget(bubble)

        max_w = int(self.width() * 0.72) if self.width() > 0 else 580
        block.setMaximumWidth(max(max_w, 420))

        if is_user:
            outer_layout.addStretch()
            outer_layout.addWidget(block)
        else:
            outer_layout.addWidget(block)
            outer_layout.addStretch()

        self._msg_layout.insertWidget(self._msg_layout.count() - 1, outer_widget)
        self._scroll_to_bottom()

    def clear_messages(self):
        while self._msg_layout.count() > 1:
            item = self._msg_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def start_stream(self):
        self.chat_display.show()
        self.chat_display.clear()
        self._stream_buffer = ""

    def append_stream_chunk(self, chunk: str):
        self.chat_display.show()
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.chat_display.setTextCursor(cursor)
        self.chat_display.insertPlainText(chunk)
        self.chat_display.moveCursor(QTextCursor.End)
        self._stream_buffer += chunk

    def end_stream(self):
        self.chat_display.hide()
        self.chat_display.clear()
        self._stream_buffer = ""
        self.chat_display.moveCursor(QTextCursor.End)

    def set_typing(self, active: bool):
        if active:
            self._typing.start()
            self._typing.show()
        else:
            self._typing.stop()
            self._typing.hide()

    def set_stt_status(self, text: str):
        if text:
            self._stt_status.setText(f"  {text}")
            self._stt_status.show()
        else: self._stt_status.hide()

    def set_input_text(self, text: str): self._input.setText(text)

    def set_suggestions(self, suggestions: list):
        while self._suggestions_layout.count() > 1:
            item = self._suggestions_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        for s in suggestions:
            btn = QPushButton(s)
            btn.setObjectName("SuggestionBtn")
            btn.clicked.connect(lambda _, t=s: self.suggestion_clicked.emit(t))
            self._suggestions_layout.insertWidget(
                self._suggestions_layout.count() - 1, btn
            )

    def _scroll_to_bottom(self): QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

#  Terminal Page
class TerminalPage(QWidget):
    command_submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TerminalPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        accent = QFrame()
        accent.setFixedHeight(3)
        accent.setStyleSheet("background: #6366f1;")
        layout.addWidget(accent)

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(24, 24, 24, 20)
        inner_layout.setSpacing(14)
        layout.addWidget(inner, 1)

        # Header row
        header_row = QHBoxLayout()
        header = QLabel("Terminal")
        header.setObjectName("SectionHeader")
        header_row.addWidget(header)
        header_row.addStretch()

        export_btn = QPushButton("↑ Export Log")
        export_btn.clicked.connect(self._export)
        header_row.addWidget(export_btn)

        inner_layout.addLayout(header_row)

        # Output
        self._output = QPlainTextEdit()
        self._output.setObjectName("TerminalOutput")
        self._output.setReadOnly(True)
        self._output.setFont(QFont("Cascadia Code", 10))
        inner_layout.addWidget(self._output, 1)

        # Input row
        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        self._prompt = QLabel("›")
        self._prompt.setObjectName("TerminalPrompt")
        self._prompt.setFixedWidth(22)

        self._input = QLineEdit()
        self._input.setObjectName("TerminalInput")
        self._input.setPlaceholderText("Enter command…")
        self._input.setMinimumHeight(40)
        self._input.returnPressed.connect(self._submit)

        run_btn = QPushButton("Run")
        run_btn.setFixedSize(72, 40)
        run_btn.clicked.connect(self._submit)

        input_row.addWidget(self._prompt)
        input_row.addWidget(self._input, 1)
        input_row.addWidget(run_btn)
        inner_layout.addLayout(input_row)

    def _submit(self):
        cmd = self._input.text().strip()
        if cmd:
            self._output.appendPlainText(f"› {cmd}")
            self._input.clear()
            self.command_submitted.emit(cmd)

    def append_output(self, text: str, is_error: bool = False):
        prefix = "  [ERR]  " if is_error else "  "
        self._output.appendPlainText(f"{prefix}{text}")
        self._output.moveCursor(QTextCursor.End)

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Terminal Log", "aria_terminal.txt", "Text Files (*.txt)"
        )
        if path:
            with open(path, "w") as f: f.write(self._output.toPlainText())

#  Timeline Page
class TimelinePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TimelinePage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        accent = QFrame()
        accent.setFixedHeight(3)
        accent.setStyleSheet("background: #f59e0b;")
        layout.addWidget(accent)

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(24, 24, 24, 20)
        inner_layout.setSpacing(14)
        layout.addWidget(inner, 1)

        header_row = QHBoxLayout()
        header = QLabel("Timeline")
        header.setObjectName("SectionHeader")
        header_row.addWidget(header)
        header_row.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear)
        header_row.addWidget(clear_btn)
        inner_layout.addLayout(header_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(6)
        self._container_layout.addStretch()

        scroll.setWidget(self._container)
        inner_layout.addWidget(scroll, 1)
        self._scroll = scroll

    def add_event(self, action: str, detail: str):
        from datetime import datetime
        from tzlocal import get_localzone

        tz = get_localzone()
        ts = datetime.now(tz).strftime(" %H:%M:%S")

        entry = QWidget()
        entry.setObjectName("TimelineEntry")
        row = QHBoxLayout(entry)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(14)

        ts_label = QLabel(ts)
        ts_label.setObjectName("TimelineTime")
        ts_label.setFixedWidth(64)
        ts_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        icon_map = {
            "command":   "⌨", "intent":    "◎",
            "browser":   "⬡", "search":    "◈",
            "image_gen": "◉",
        }
        icon = icon_map.get(action, "·")
        icon_label = QLabel(icon)
        icon_label.setFixedWidth(18)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("color: #00e5cc; font-size: 12pt; background: transparent;")

        text_label = QLabel(f"[{action}]  {detail}")
        text_label.setObjectName("TimelineText")
        text_label.setWordWrap(True)

        row.addWidget(ts_label)
        row.addWidget(icon_label)
        row.addWidget(text_label, 1)

        self._container_layout.insertWidget(self._container_layout.count() - 1, entry)
        QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

    def _clear(self):
        while self._container_layout.count() > 1:
            item = self._container_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

#  Warnings Page
class WarningsPage(QWidget):
    count_changed = pyqtSignal(int)

    _ICONS = {"error": "⬟", "warning": "⬡", "info": "◈"}
    _OBJ   = {"error": "WarningEntryError", "warning": "WarningEntryWarning", "info": "WarningEntryInfo"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WarningsPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        accent = QFrame()
        accent.setFixedHeight(3)
        accent.setStyleSheet("background: #ef4444;")
        layout.addWidget(accent)

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(24, 24, 24, 20)
        inner_layout.setSpacing(14)
        layout.addWidget(inner, 1)

        header_row = QHBoxLayout()
        header = QLabel("Warnings & Health")
        header.setObjectName("SectionHeader")
        header_row.addWidget(header)
        header_row.addStretch()

        clear_btn = QPushButton("Clear All")
        clear_btn.setObjectName("ClearWarningsBtn")
        clear_btn.clicked.connect(self._clear)
        header_row.addWidget(clear_btn)
        inner_layout.addLayout(header_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(6)
        self._container_layout.addStretch()

        scroll.setWidget(self._container)
        inner_layout.addWidget(scroll, 1)
        self._count = 0

    def add_warning(self, severity: str, message: str):
        from datetime import datetime
        from tzlocal import get_localzone

        tz = get_localzone()
        ts = datetime.now(tz).strftime("%H:%M:%S")

        entry = QWidget()
        entry.setObjectName(self._OBJ.get(severity, "WarningEntryInfo"))

        row = QHBoxLayout(entry)
        row.setContentsMargins(16, 10, 16, 10)
        row.setSpacing(14)

        icon = QLabel(self._ICONS.get(severity, "·"))
        icon.setFixedWidth(18)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("background: transparent; font-size: 12pt;")

        text = QLabel(message)
        text.setWordWrap(True)
        text.setStyleSheet("background: transparent;")

        ts_label = QLabel(ts)
        ts_label.setObjectName("TimelineTime")
        ts_label.setFixedWidth(64)
        ts_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        row.addWidget(icon)
        row.addWidget(text, 1)
        row.addWidget(ts_label)

        self._container_layout.insertWidget(self._container_layout.count() - 1, entry)

        self._count += 1
        self.count_changed.emit(self._count)

    def _clear(self):
        while self._container_layout.count() > 1:
            item = self._container_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self._count = 0
        self.count_changed.emit(0)
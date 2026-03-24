import datetime
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QPushButton, QLineEdit, QSizePolicy, QPlainTextEdit, QTextEdit
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QTextCursor, QFont
from widgets import TypingIndicator

# Chat Page
class ChatPage(QWidget):
    message_submitted  = pyqtSignal(str)
    suggestion_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        # Message area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setObjectName("ChatArea")
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._msg_container = QWidget()
        self._msg_container.setObjectName("ChatArea")
        self._msg_layout = QVBoxLayout(self._msg_container)
        self._msg_layout.setContentsMargins(16, 16, 16, 16)
        self._msg_layout.setSpacing(6)
        self._msg_layout.addStretch()

        self._scroll.setWidget(self._msg_container)
        # Typing indicator
        self._typing = TypingIndicator()
        self._typing.hide()
        # STT status
        self._stt_status = QLabel("")
        self._stt_status.setObjectName("STTStatus")
        self._stt_status.hide()
        # Suggestions
        self._suggestions_widget = QWidget()
        self._suggestions_layout = QHBoxLayout(self._suggestions_widget)
        self._suggestions_layout.setContentsMargins(8, 4, 8, 4)
        self._suggestions_layout.setSpacing(6)
        self._suggestions_layout.addStretch()
        # Input area
        input_widget = QWidget()
        input_widget.setObjectName("InputArea")
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(12, 8, 12, 8)
        input_layout.setSpacing(4)

        row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setObjectName("ChatInput")
        self._input.setPlaceholderText("Message ARIA...")
        self._input.returnPressed.connect(self._submit)

        self._send_btn = QPushButton("Send")
        self._send_btn.setObjectName("SendBtn")
        self._send_btn.clicked.connect(self._submit)
        self._send_btn.setFixedWidth(80)

        row.addWidget(self._input)
        row.addWidget(self._send_btn)
        input_layout.addWidget(self._suggestions_widget)
        input_layout.addLayout(row)

        # Streaming display
        self.chat_display = QTextEdit()
        self.chat_display.setObjectName("ChatDisplay")
        self.chat_display.setReadOnly(True)
        self.chat_display.setMaximumHeight(200)

        layout.addWidget(self._scroll, 1)
        layout.addWidget(self.chat_display)
        layout.addWidget(self._stt_status)
        layout.addWidget(self._typing)
        layout.addWidget(input_widget)
        # Streaming buffer
        self._streaming_label: QLabel = None

    def _submit(self):
        text = self._input.text().strip()
        if text:
            self._input.clear()
            self.message_submitted.emit(text)

    def add_message(self, role: str, text: str):
        # Stop any active stream first
        if self._streaming_label: self._streaming_label = None
        container = QWidget()
        vlayout = QVBoxLayout(container)
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.setSpacing(2)
        # Role label
        role_label = QLabel("You" if role == "user" else "ARIA")
        role_label.setObjectName("MessageRole")
        # Message text
        msg_label = QLabel(text)
        msg_label.setObjectName("UserBubble" if role == "user" else "AiBubble")
        msg_label.setWordWrap(True)
        msg_label.setTextFormat(Qt.MarkdownText)
        msg_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        msg_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        vlayout.addWidget(role_label)
        vlayout.addWidget(msg_label)
        # Alignment
        outer = QHBoxLayout()
        if role == "user":
            outer.addStretch()
            outer.addWidget(container)
        else:
            outer.addWidget(container)
            outer.addStretch()
        outer_widget = QWidget()
        outer_widget.setLayout(outer)
        # Insert before the stretch at bottom
        self._msg_layout.insertWidget(self._msg_layout.count() - 1, outer_widget)
        self._scroll_to_bottom()

    def clear_messages(self):
        while self._msg_layout.count() > 1:
            item = self._msg_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _stream_chunk(self, chunk: str):
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.chat_display.setTextCursor(cursor)
        self.chat_display.insertPlainText(chunk)
        self.chat_display.moveCursor(QTextCursor.End)

    def _start_stream_bubble(self, theme: dict):
        t = theme
        timestamp = datetime.now().strftime("%H:%M:%S")
        html = (
            f"<div style='margin-bottom:14px;border-left:2px solid {t['border']};padding-left:10px;'>"
            f"<div style='font-size:7.5pt;color:{t['dim']};margin-bottom:3px;letter-spacing:1px;'>"
            f"<span style='color:#888888;'>ARIA  "
            f"<span style='color:#ef9a9a;font-size:7pt'>[ ● STREAMING ]</span></span>"
            f"&nbsp;&nbsp;<span style='color:{t['border']};'>{timestamp}</span>"
            f"</div>"
            f"<span id='stream_target' style='color:{t['text']};line-height:1.65;font-size:10pt;'></span>"
            f"</div>"
        )
        self.chat_display.append(html)
        self.chat_display.moveCursor(QTextCursor.End)
        self._stream_buffer = ""

    def _end_stream_bubble(self):
        # Re-render the buffered plain text as a proper message bubble
        if hasattr(self, '_stream_buffer') and self._stream_buffer:
            # Remove the incomplete streaming bubble
            doc = self.chat_display.document()
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.End)
            # Append the final clean version
            self.append_message("assistant", self._stream_buffer, "chat",
                                getattr(self, '_last_theme', {}))
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
            self._stt_status.setText(text)
            self._stt_status.show()
        else: self._stt_status.hide()

    def set_input_text(self, text: str): self._input.setText(text)

    def set_suggestions(self, suggestions: list):
        # Clear old
        while self._suggestions_layout.count() > 1:
            item = self._suggestions_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        for s in suggestions:
            btn = QPushButton(s)
            btn.setObjectName("SuggestionBtn")
            btn.clicked.connect(lambda _, t=s: self.suggestion_clicked.emit(t))
            self._suggestions_layout.insertWidget(self._suggestions_layout.count() - 1, btn)

    def _scroll_to_bottom(self): QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

# Terminal Page
class TerminalPage(QWidget):
    command_submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QLabel("⌨️  Terminal")
        header.setObjectName("SectionHeader")
        layout.addWidget(header)

        self._output = QPlainTextEdit()
        self._output.setObjectName("TerminalOutput")
        self._output.setReadOnly(True)
        self._output.setFont(QFont("Consolas", 11))
        layout.addWidget(self._output, 1)
        # Export button
        export_btn = QPushButton("📤 Export Log")
        export_btn.clicked.connect(self._export)
        layout.addWidget(export_btn)
        # Input row
        row = QHBoxLayout()
        self._prompt = QLabel("PS >")
        self._prompt.setObjectName("TerminalPrompt")

        self._input = QLineEdit()
        self._input.setObjectName("TerminalInput")
        self._input.setPlaceholderText("Enter command...")
        self._input.returnPressed.connect(self._submit)

        run_btn = QPushButton("Run")
        run_btn.clicked.connect(self._submit)
        run_btn.setFixedWidth(60)

        row.addWidget(self._prompt)
        row.addWidget(self._input, 1)
        row.addWidget(run_btn)
        layout.addLayout(row)

    def _submit(self):
        cmd = self._input.text().strip()
        if cmd:
            self._output.appendPlainText(f"PS > {cmd}")
            self._input.clear()
            self.command_submitted.emit(cmd)

    def append_output(self, text: str, is_error: bool = False):
        if is_error: self._output.appendPlainText(f"[ERR] {text}")
        else: self._output.appendPlainText(text)
        self._output.moveCursor(QTextCursor.End)

    def _export(self):
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Export Terminal Log", "aria_terminal.txt", "Text Files (*.txt)")
        if path:
            with open(path, "w") as f: f.write(self._output.toPlainText())
# Timeline Page
class TimelinePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QLabel("📋  Timeline")
        header.setObjectName("SectionHeader")
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.addStretch()

        scroll.setWidget(self._container)
        layout.addWidget(scroll, 1)

        clear_btn = QPushButton("Clear Timeline")
        clear_btn.clicked.connect(self._clear)
        layout.addWidget(clear_btn)
        self._scroll = scroll

    def add_event(self, action: str, detail: str):
        ts  = datetime.datetime.now().strftime("%H:%M:%S")

        entry = QWidget()
        entry.setObjectName("TimelineEntry")
        row = QHBoxLayout(entry)
        row.setContentsMargins(8, 4, 8, 4)

        ts_label = QLabel(ts)
        ts_label.setObjectName("TimelineTime")
        ts_label.setFixedWidth(60)

        icon = {"command": "⌨️", "intent": "🎯", "browser": "🌐",
                "search": "🔍", "image_gen": "🎨"}.get(action, "•")

        text_label = QLabel(f"{icon} [{action}] {detail}")
        text_label.setObjectName("TimelineText")
        text_label.setWordWrap(True)

        row.addWidget(ts_label)
        row.addWidget(text_label, 1)

        self._container_layout.insertWidget(self._container_layout.count() - 1, entry)
        QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

    def _clear(self):
        while self._container_layout.count() > 1:
            item = self._container_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
# Warnings Page
class WarningsPage(QWidget):
    count_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QLabel("⚠️  Warnings & Health Alerts")
        header.setObjectName("SectionHeader")
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.addStretch()

        scroll.setWidget(self._container)
        layout.addWidget(scroll, 1)

        clear_btn = QPushButton("Clear All Warnings")
        clear_btn.setObjectName("ClearWarningsBtn")
        clear_btn.clicked.connect(self._clear)
        layout.addWidget(clear_btn)
        self._count = 0

    def add_warning(self, severity: str, message: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S")

        entry = QWidget()
        obj_map = {"error": "WarningEntryError", "warning": "WarningEntryWarning"}
        entry.setObjectName(obj_map.get(severity, "WarningEntryInfo"))

        row = QHBoxLayout(entry)
        row.setContentsMargins(8, 6, 8, 6)

        icon_map = {"error": "🔴", "warning": "🟡", "info": "🔵"}
        icon = QLabel(icon_map.get(severity, "•"))
        icon.setFixedWidth(20)

        text = QLabel(message)
        text.setWordWrap(True)

        ts_label = QLabel(ts)
        ts_label.setObjectName("TimelineTime")

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
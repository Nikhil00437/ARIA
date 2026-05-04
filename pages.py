# pages.py — Glassy minimal pages: Chat, Terminal, Timeline, Warnings

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFileDialog, QHBoxLayout,
    QScrollArea, QLabel, QPushButton, QLineEdit,
    QSizePolicy, QPlainTextEdit, QTextEdit, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QTextCursor, QFont
from widgets import TypingIndicator
from typing import Dict, Set


# Available reactions
MESSAGE_REACTIONS = ["👍", "👎", "❤️", "🔥", "💡", "🎉"]

# ─────────────────────────────────────────────────────────────────
#  Chat Page
# ─────────────────────────────────────────────────────────────────

class ChatPage(QWidget):
    message_submitted  = pyqtSignal(str)
    suggestion_clicked = pyqtSignal(str)
    load_more          = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ChatPage")
        self._loading_older = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Accent top stripe
        self._accent = QFrame()
        self._accent.setFixedHeight(3)
        self._accent.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 rgba(80,140,255,0.7), stop:1 rgba(140,80,255,0.7));"
            "border: none;"
        )
        layout.addWidget(self._accent)

        # Message scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setObjectName("ChatArea")
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll.setFrameShape(QScrollArea.NoFrame)

        self._msg_container = QWidget()
        self._msg_container.setObjectName("ChatArea")
        self._msg_layout = QVBoxLayout(self._msg_container)
        self._msg_layout.setContentsMargins(32, 28, 32, 20)
        self._msg_layout.setSpacing(16)
        self._msg_layout.addStretch()

        self._scroll.setWidget(self._msg_container)
        self._scroll.verticalScrollBar().valueChanged.connect(self._check_scroll)

        # Typing indicator
        self._typing = TypingIndicator()
        self._typing.hide()
        self._typing.setFixedHeight(30)

        # STT status
        self._stt_status = QLabel("")
        self._stt_status.setObjectName("STTStatus")
        self._stt_status.setFixedHeight(24)
        self._stt_status.hide()

        # Streaming display (live chunk output)
        self.chat_display = QTextEdit()
        self.chat_display.setObjectName("AiBubble")
        self.chat_display.setReadOnly(True)
        self.chat_display.setMaximumHeight(200)
        self.chat_display.hide()
        self.chat_display.setStyleSheet(
            "margin: 0 32px 4px 32px; border-radius: 14px;"
            "background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15);"
        )

        # Suggestion chips
        self._suggestions_widget = QWidget()
        self._suggestions_widget.setObjectName("SuggestionsRow")
        self._suggestions_layout = QHBoxLayout(self._suggestions_widget)
        self._suggestions_layout.setContentsMargins(28, 6, 28, 2)
        self._suggestions_layout.setSpacing(8)
        self._suggestions_layout.addStretch()

        # Input area
        input_widget = QWidget()
        input_widget.setObjectName("InputArea")
        input_widget.setStyleSheet(
            "background: rgba(255,255,255,0.05);"
            "border-top: 1px solid rgba(255,255,255,0.08);"
        )
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(20, 10, 20, 16)
        input_layout.setSpacing(8)

        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        self._input = QLineEdit()
        self._input.setObjectName("ChatInput")
        self._input.setPlaceholderText("Message ARIA…")
        self._input.setMinimumHeight(46)
        self._input.returnPressed.connect(self._submit)

        self._send_btn = QPushButton("Send →")
        self._send_btn.setObjectName("SendBtn")
        self._send_btn.setFixedSize(90, 46)
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

        self._stream_buffer = ""

    # ── Public API ──────────────────────────────────────────────

    def _submit(self):
        text = self._input.text().strip()
        if text:
            self._input.clear()
            self.message_submitted.emit(text)

    def add_message(self, role: str, text: str, reactions: Dict[str, int] = None):
        is_user = (role == "user")
        is_ai = (role == "assistant")

        outer = QWidget()
        outer_lyt = QHBoxLayout(outer)
        outer_lyt.setContentsMargins(0, 2, 0, 2)
        outer_lyt.setSpacing(0)

        block = QWidget()
        block_lyt = QVBoxLayout(block)
        block_lyt.setContentsMargins(0, 0, 0, 0)
        block_lyt.setSpacing(4)

        # Role chip
        role_row = QHBoxLayout()
        role_row.setSpacing(6)

        role_chip = QLabel("YOU" if is_user else "ARIA")
        role_chip.setObjectName("MessageRole")
        if is_user:
            role_chip.setAlignment(Qt.AlignRight)
            role_chip.setStyleSheet(
                "color: rgba(120,180,255,0.8); background: transparent; "
                "font-size: 7pt; font-weight: 700; letter-spacing: 1.5px;"
            )
        else:
            role_chip.setAlignment(Qt.AlignLeft)
            role_chip.setStyleSheet(
                "color: rgba(255,255,255,0.40); background: transparent; "
                "font-size: 7pt; font-weight: 700; letter-spacing: 1.5px;"
            )

        if is_user:
            role_row.addStretch()
            role_row.addWidget(role_chip)
        else:
            role_row.addWidget(role_chip)
            role_row.addStretch()

        # Bubble
        bubble = QLabel(text)
        bubble.setObjectName("UserBubble" if is_user else "AiBubble")
        bubble.setWordWrap(True)
        bubble.setTextFormat(Qt.MarkdownText)
        bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        block_lyt.addLayout(role_row)
        block_lyt.addWidget(bubble)

        # Add reaction buttons for AI messages
        if is_ai:
            reaction_row = self._create_reaction_row()
            block_lyt.addLayout(reaction_row)

        max_w = int(self.width() * 0.65) if self.width() > 0 else 520
        block.setMaximumWidth(max(max_w, 380))

        if is_user:
            outer_lyt.addStretch()
            outer_lyt.addWidget(block)
        else:
            outer_lyt.addWidget(block)
            outer_lyt.addStretch()

        self._msg_layout.insertWidget(self._msg_layout.count() - 1, outer)
        self._scroll_to_bottom()
    
    def _create_reaction_row(self) -> QHBoxLayout:
        """Create a row of reaction buttons."""
        row = QHBoxLayout()
        row.setSpacing(4)
        
        for reaction in MESSAGE_REACTIONS:
            btn = QPushButton(reaction)
            btn.setFixedSize(28, 24)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    font-size: 12pt;
                    padding: 0;
                }
                QPushButton:hover {
                    background: rgba(255,255,255,0.1);
                    border-radius: 4px;
                }
            """)
            btn.clicked.connect(lambda checked, r=reaction: self._on_reaction_clicked(r))
            row.addWidget(btn)
        
        row.addStretch()
        return row
    
    def _on_reaction_clicked(self, reaction: str):
        """Handle reaction button click."""
        # In a full implementation, this would emit a signal to save the reaction
        # For now, just show a toast-like feedback
        print(f"Reaction added: {reaction}")

    def clear_messages(self):
        while self._msg_layout.count() > 1:
            item = self._msg_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

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
        else:
            self._stt_status.hide()

    def set_input_text(self, text: str):
        self._input.setText(text)

    def set_suggestions(self, suggestions: list):
        while self._suggestions_layout.count() > 1:
            item = self._suggestions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for s in suggestions:
            btn = QPushButton(s)
            btn.setObjectName("SuggestionBtn")
            btn.clicked.connect(lambda _, t=s: self.suggestion_clicked.emit(t))
            self._suggestions_layout.insertWidget(
                self._suggestions_layout.count() - 1, btn
            )

    def set_loading_older_done(self):
        self._loading_older = False

    def _scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

    def _check_scroll(self):
        if self._loading_older:
            return
        bar = self._scroll.verticalScrollBar()
        if bar.value() <= bar.minimum() + 5:
            self._loading_older = True
            self.load_more.emit()


# ─────────────────────────────────────────────────────────────────
#  Terminal Page
# ─────────────────────────────────────────────────────────────────

class TerminalPage(QWidget):
    command_submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TerminalPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Accent stripe
        accent = QFrame()
        accent.setFixedHeight(3)
        accent.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 rgba(140,80,255,0.7), stop:1 rgba(80,140,255,0.7));"
            "border: none;"
        )
        layout.addWidget(accent)

        inner = QWidget()
        inner_lyt = QVBoxLayout(inner)
        inner_lyt.setContentsMargins(24, 24, 24, 20)
        inner_lyt.setSpacing(14)
        layout.addWidget(inner, 1)

        # Header
        header_row = QHBoxLayout()
        header = QLabel("Terminal")
        header.setObjectName("SectionHeader")
        export_btn = QPushButton("↑ Export Log")
        export_btn.clicked.connect(self._export)

        header_row.addWidget(header)
        header_row.addStretch()
        header_row.addWidget(export_btn)
        inner_lyt.addLayout(header_row)

        # Output
        self._output = QPlainTextEdit()
        self._output.setObjectName("TerminalOutput")
        self._output.setReadOnly(True)
        self._output.setFont(QFont("Cascadia Code", 10))
        inner_lyt.addWidget(self._output, 1)

        # Input row
        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        self._prompt = QLabel("›")
        self._prompt.setObjectName("TerminalPrompt")
        self._prompt.setFixedWidth(24)

        self._input = QLineEdit()
        self._input.setObjectName("TerminalInput")
        self._input.setPlaceholderText("Enter command…")
        self._input.setMinimumHeight(42)
        self._input.returnPressed.connect(self._submit)

        run_btn = QPushButton("Run")
        run_btn.setFixedSize(72, 42)
        run_btn.clicked.connect(self._submit)

        input_row.addWidget(self._prompt)
        input_row.addWidget(self._input, 1)
        input_row.addWidget(run_btn)
        inner_lyt.addLayout(input_row)

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
            with open(path, "w") as f:
                f.write(self._output.toPlainText())


# ─────────────────────────────────────────────────────────────────
#  Timeline Page
# ─────────────────────────────────────────────────────────────────

class TimelinePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TimelinePage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        accent = QFrame()
        accent.setFixedHeight(3)
        accent.setStyleSheet("background: rgba(255,180,40,0.7); border: none;")
        layout.addWidget(accent)

        inner = QWidget()
        inner_lyt = QVBoxLayout(inner)
        inner_lyt.setContentsMargins(24, 24, 24, 20)
        inner_lyt.setSpacing(14)
        layout.addWidget(inner, 1)

        header_row = QHBoxLayout()
        header = QLabel("Timeline")
        header.setObjectName("SectionHeader")
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear)
        header_row.addWidget(header)
        header_row.addStretch()
        header_row.addWidget(clear_btn)
        inner_lyt.addLayout(header_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(6)
        self._container_layout.addStretch()

        scroll.setWidget(self._container)
        inner_lyt.addWidget(scroll, 1)
        self._scroll = scroll

    def add_event(self, action: str, detail: str):
        from datetime import datetime
        try:
            from tzlocal import get_localzone
            tz = get_localzone()
            ts = datetime.now(tz).strftime("%H:%M:%S")
        except Exception:
            ts = datetime.now().strftime("%H:%M:%S")

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
            "command": "⌨", "intent": "◎", "browser": "⬡",
            "search": "◈", "image_gen": "◉",
        }
        icon = QLabel(icon_map.get(action, "·"))
        icon.setFixedWidth(18)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("color: rgba(120,180,255,0.8); font-size: 12pt; background: transparent;")

        text_label = QLabel(f"[{action}]  {detail}")
        text_label.setObjectName("TimelineText")
        text_label.setWordWrap(True)

        row.addWidget(ts_label)
        row.addWidget(icon)
        row.addWidget(text_label, 1)

        self._container_layout.insertWidget(self._container_layout.count() - 1, entry)
        QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

    def _clear(self):
        while self._container_layout.count() > 1:
            item = self._container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


# ─────────────────────────────────────────────────────────────────
#  Warnings Page
# ─────────────────────────────────────────────────────────────────

class WarningsPage(QWidget):
    count_changed = pyqtSignal(int)

    _ICONS = {"error": "⬟", "warning": "⬡", "info": "◈"}
    _OBJ   = {
        "error":   "WarningEntryError",
        "warning": "WarningEntryWarning",
        "info":    "WarningEntryInfo",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WarningsPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        accent = QFrame()
        accent.setFixedHeight(3)
        accent.setStyleSheet("background: rgba(255,60,60,0.7); border: none;")
        layout.addWidget(accent)

        inner = QWidget()
        inner_lyt = QVBoxLayout(inner)
        inner_lyt.setContentsMargins(24, 24, 24, 20)
        inner_lyt.setSpacing(14)
        layout.addWidget(inner, 1)

        header_row = QHBoxLayout()
        header = QLabel("Warnings & Health")
        header.setObjectName("SectionHeader")
        clear_btn = QPushButton("Clear All")
        clear_btn.setObjectName("ClearWarningsBtn")
        clear_btn.clicked.connect(self._clear)
        header_row.addWidget(header)
        header_row.addStretch()
        header_row.addWidget(clear_btn)
        inner_lyt.addLayout(header_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(6)
        self._container_layout.addStretch()

        scroll.setWidget(self._container)
        inner_lyt.addWidget(scroll, 1)
        self._count = 0

    def add_warning(self, severity: str, message: str):
        from datetime import datetime
        try:
            from tzlocal import get_localzone
            tz = get_localzone()
            ts = datetime.now(tz).strftime("%H:%M:%S")
        except Exception:
            ts = datetime.now().strftime("%H:%M:%S")

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
            if item.widget():
                item.widget().deleteLater()
        self._count = 0
        self.count_changed.emit(0)

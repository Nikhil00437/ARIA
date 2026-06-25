# pages.py — Glassy minimal pages: Chat, Terminal, Timeline, Warnings

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFileDialog, QHBoxLayout,
    QScrollArea, QLabel, QPushButton, QLineEdit,
    QSizePolicy, QPlainTextEdit, QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QEvent
from PyQt5.QtGui import QTextCursor, QFont, QKeyEvent
from widgets import TypingIndicator
from typing import Dict


# Available reactions
MESSAGE_REACTIONS = ["\U0001F44D", "\U0001F44E", "\u2764\ufe0f", "\U0001F525", "\U0001F4A1", "\U0001F389"]

# ─────────────────────────────────────────────────────────────────
#  Chat Page
# ─────────────────────────────────────────────────────────────────

class ChatPage(QWidget):
    message_submitted  = pyqtSignal(str)
    suggestion_clicked = pyqtSignal(str)
    reaction_clicked   = pyqtSignal(int, str)  # message_seq, reaction
    load_more          = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ChatPage")
        self._loading_older = False
        self._msg_counter = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Message scroll area (themed via #ChatArea; no top divider needed)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setObjectName("ChatArea")
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll.setFrameShape(QScrollArea.NoFrame)

        self._msg_container = QWidget()
        self._msg_container.setObjectName("ChatArea")
        self._msg_layout = QVBoxLayout(self._msg_container)
        self._msg_layout.setContentsMargins(20, 16, 20, 12)
        self._msg_layout.setSpacing(14)
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

        # Suggestion chips
        self._suggestions_widget = QWidget()
        self._suggestions_widget.setObjectName("SuggestionsRow")
        self._suggestions_layout = QHBoxLayout(self._suggestions_widget)
        self._suggestions_layout.setContentsMargins(16, 4, 16, 2)
        self._suggestions_layout.setSpacing(6)
        self._suggestions_layout.addStretch()

        # BrainWidget (Phase 9 — sits above the input area, shows self-mod
        # insights / proposals / preview state. Hidden by default; main_window
        # calls set_visible() based on controller state.)
        from brain_widget import BrainWidget
        self._brain_widget = BrainWidget()

        # Input area (themed via #InputArea; no inline override)
        input_widget = QWidget()
        input_widget.setObjectName("InputArea")
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(16, 8, 16, 12)
        input_layout.setSpacing(6)

        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        self._input = QPlainTextEdit()
        self._input.setObjectName("ChatInput")
        self._input.setPlaceholderText("Message ARIA…  (Shift+Enter for newline | Ctrl+K for commands)")
        self._input.setMinimumHeight(46)
        self._input.setMaximumHeight(200)
        self._input.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._input.installEventFilter(self)
        self._input.document().contentsChanged.connect(self._auto_grow_input)

        self._send_btn = QPushButton("Send")
        self._send_btn.setObjectName("SendBtn")
        self._send_btn.setFixedSize(80, 46)
        self._send_btn.clicked.connect(self._submit)

        input_row.addWidget(self._input, 1)
        input_row.addWidget(self._send_btn)

        input_layout.addWidget(self._suggestions_widget)
        input_layout.addLayout(input_row)

        layout.addWidget(self._scroll, 1)
        layout.addWidget(self._brain_widget)
        layout.addWidget(self._stt_status)
        layout.addWidget(self._typing)
        layout.addWidget(input_widget)

        # Streaming state
        self._stream_active = False
        self._stream_text = ""
        self._stream_label: QLabel | None = None
        self._stream_block_lyt: QVBoxLayout | None = None
        self._stream_outer: QWidget | None = None
        self._stream_seq: int = -1

    # ── Public API ──────────────────────────────────────────────

    
    @property
    def brain_widget(self):
        """Phase 9: brain widget exposed for main_window wiring."""
        return getattr(self, "_brain_widget", None)

    def eventFilter(self, obj, event):
        """Handle Enter to submit, Shift+Enter for newline in the input."""
        if obj is self._input and event.type() == QEvent.KeyPress:
            key_event: QKeyEvent = event
            if key_event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if key_event.modifiers() & Qt.ShiftModifier:
                    # Shift+Enter → insert newline
                    cursor = self._input.textCursor()
                    cursor.insertText("\n")
                    return True
                else:
                    # Plain Enter → submit
                    self._submit()
                    return True
        return super().eventFilter(obj, event)

    def _submit(self):
        text = self._input.toPlainText().strip()
        if text:
            self._input.clear()
            self._input.setFixedHeight(self._input.minimumHeight())
            self.message_submitted.emit(text)

    def add_message(self, role: str, text: str, reactions: Dict[str, int] = None, message_seq: int = -1):
        is_user = (role == "user")
        is_ai = (role == "assistant")
        seq = message_seq if message_seq >= 0 else self._msg_counter
        self._msg_counter = max(self._msg_counter, seq + 1)

        # Row layout: [avatar] [name+body column]
        # The avatar circle uses #Avatar (AI) or #AvatarUser (user); text
        # column has the role name and the bubble body. No bubble background.
        row = QWidget()
        row_lyt = QHBoxLayout(row)
        row_lyt.setContentsMargins(0, 4, 0, 4)
        row_lyt.setSpacing(10)

        # Avatar circle (28x28) — initials in a colored disc.
        avatar = QLabel("A" if is_ai else "U")
        avatar.setObjectName("AvatarUser" if is_user else "Avatar")
        avatar.setFixedSize(28, 28)
        avatar.setAlignment(Qt.AlignCenter)

        # Name + body column
        body_col = QWidget()
        body_lyt = QVBoxLayout(body_col)
        body_lyt.setContentsMargins(0, 0, 0, 0)
        body_lyt.setSpacing(2)

        name_lbl = QLabel("You" if is_user else "ARIA")
        name_lbl.setObjectName("MessageRole")
        body_lyt.addWidget(name_lbl)

        bubble = QLabel(text)
        bubble.setObjectName("UserBubble" if is_user else "AiBubble")
        bubble.setWordWrap(True)
        bubble.setTextFormat(Qt.MarkdownText)
        bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        body_lyt.addWidget(bubble)

        # Reaction row (AI messages only)
        if is_ai:
            reaction_row = self._create_reaction_row(seq)
            body_lyt.addLayout(reaction_row)

        row_lyt.addWidget(avatar)
        row_lyt.addWidget(body_col, 1)

        # Insert the new row just above the trailing stretch
        self._msg_layout.insertWidget(self._msg_layout.count() - 1, row)
        self._scroll_to_bottom()
    
    def _create_reaction_row(self, seq: int) -> QHBoxLayout:
        """Create a row of reaction buttons for message at given sequence."""
        row = QHBoxLayout()
        row.setSpacing(4)
        row.setContentsMargins(0, 4, 0, 0)

        for reaction in MESSAGE_REACTIONS:
            btn = QPushButton(reaction)
            btn.setFixedSize(28, 24)
            btn.setProperty("seq", seq)
            btn.setProperty("reaction", reaction)
            btn.setObjectName("ReactionBtn")
            btn.clicked.connect(lambda checked, r=reaction, s=seq: self._on_reaction_clicked(r, s))
            row.addWidget(btn)

        row.addStretch()
        return row

    def _on_reaction_clicked(self, reaction: str, seq: int):
        """Handle reaction button click and emit signal for persistence."""
        self.reaction_clicked.emit(seq, reaction)

    def clear_messages(self):
        while self._msg_layout.count() > 1:
            item = self._msg_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def start_stream(self):
        """Create a placeholder AI message bubble for streaming chunks."""
        self._stream_active = True
        self._stream_text = ""

        outer = QWidget()
        outer_lyt = QHBoxLayout(outer)
        outer_lyt.setContentsMargins(0, 4, 0, 4)
        outer_lyt.setSpacing(10)

        avatar = QLabel("A")
        avatar.setObjectName("Avatar")
        avatar.setFixedSize(28, 28)
        avatar.setAlignment(Qt.AlignCenter)

        block = QWidget()
        block_lyt = QVBoxLayout(block)
        block_lyt.setContentsMargins(0, 0, 0, 0)
        block_lyt.setSpacing(2)

        name_lbl = QLabel("ARIA")
        name_lbl.setObjectName("MessageRole")
        block_lyt.addWidget(name_lbl)

        self._stream_label = QLabel("")
        self._stream_label.setObjectName("AiBubble")
        self._stream_label.setWordWrap(True)
        self._stream_label.setTextFormat(Qt.MarkdownText)
        self._stream_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._stream_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        block_lyt.addWidget(self._stream_label)

        outer_lyt.addWidget(avatar)
        outer_lyt.addWidget(block, 1)

        self._stream_seq = self._msg_counter
        self._msg_counter += 1

        self._msg_layout.insertWidget(self._msg_layout.count() - 1, outer)
        self._scroll_to_bottom()

        self._stream_block_lyt = block_lyt
        self._stream_outer = outer

    def append_stream_chunk(self, chunk: str):
        """Append chunk to the streaming message bubble."""
        if not self._stream_active or not self._stream_label:
            return
        self._stream_text += chunk
        self._stream_label.setText(self._stream_text)
        self._scroll_to_bottom()

    def end_stream(self) -> str:
        """Finalize the streaming bubble. Adds reaction row. Returns final text."""
        if not self._stream_active:
            return ""
        self._stream_active = False

        # Add reaction row now that the message is complete
        if self._stream_block_lyt is not None:
            reaction_row = self._create_reaction_row(self._stream_seq)
            self._stream_block_lyt.addLayout(reaction_row)

        final_text = self._stream_text
        self._stream_label = None
        self._stream_block_lyt = None
        self._stream_outer = None
        return final_text

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

    def _auto_grow_input(self):
        """Auto-grow the input height based on content, capped at max height."""
        doc = self._input.document()
        doc_height = doc.size().height()
        new_height = max(self._input.minimumHeight(),
                         min(int(doc_height) + 20, self._input.maximumHeight()))
        self._input.setFixedHeight(new_height)

    def set_input_text(self, text: str):
        self._input.setPlainText(text)
        cursor = self._input.textCursor()
        cursor.movePosition(QTextCursor.End)
        self._input.setTextCursor(cursor)

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

        inner = QWidget()
        inner_lyt = QVBoxLayout(inner)
        inner_lyt.setContentsMargins(16, 16, 16, 12)
        inner_lyt.setSpacing(10)
        layout.addWidget(inner, 1)

        # Header
        header_row = QHBoxLayout()
        header = QLabel("Terminal")
        header.setObjectName("SectionHeader")
        export_btn = QPushButton("Export Log")
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

        self._prompt = QLabel("\u203a")
        self._prompt.setObjectName("TerminalPrompt")
        self._prompt.setFixedWidth(24)

        self._input = QLineEdit()
        self._input.setObjectName("TerminalInput")
        self._input.setPlaceholderText("Enter command…")
        self._input.setMinimumHeight(42)
        self._input.returnPressed.connect(self._submit)

        run_btn = QPushButton("Run")
        run_btn.setObjectName("TerminalRunBtn")
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

        inner = QWidget()
        inner_lyt = QVBoxLayout(inner)
        inner_lyt.setContentsMargins(16, 16, 16, 12)
        inner_lyt.setSpacing(10)
        layout.addWidget(inner, 1)

        header_row = QHBoxLayout()
        header = QLabel("Timeline")
        header.setObjectName("SectionHeader")
        clear_btn = QPushButton("Clear")
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
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(0)
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

        # Icon map — minimal glyphs, themed via #TimelineIcon.
        icon_map = {
            "command": "\u2328", "intent": "\u25cb", "browser": "\u2b22",
            "search": "\u25c8", "image_gen": "\u25c9",
            "agent": "\u25b7", "agent_action": "\u203a", "agent_observation": "\u25cc",
        }
        icon = QLabel(icon_map.get(action, "\u00b7"))
        icon.setObjectName("TimelineIcon")
        icon.setFixedWidth(18)
        icon.setAlignment(Qt.AlignCenter)

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

    _ICONS = {"error": "\u26d4", "warning": "\u26a0", "info": "\u2139"}
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

        inner = QWidget()
        inner_lyt = QVBoxLayout(inner)
        inner_lyt.setContentsMargins(16, 16, 16, 12)
        inner_lyt.setSpacing(10)
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

        icon = QLabel(self._ICONS.get(severity, "\u00b7"))
        icon.setObjectName("WarningIcon")
        icon.setFixedWidth(18)
        icon.setAlignment(Qt.AlignCenter)

        text = QLabel(message)
        text.setObjectName("WarningText")
        text.setWordWrap(True)

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

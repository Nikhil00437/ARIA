import re
from datetime import datetime

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel, QListWidget, QListWidgetItem, QFrame
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor

from widgets import CollapsibleSection
from constants import THEMES

# Chat page
class ChatPage(QWidget):
    message_submitted = pyqtSignal(str)
    quick_action      = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 0)
        layout.setSpacing(10)

        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setObjectName("chatDisplay")
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Consolas", 10))
        layout.addWidget(self.chat_display, stretch=1)

        # Quick actions (collapsible)
        self.quick_section = CollapsibleSection("Quick Actions")
        self._build_quick_actions()
        layout.addWidget(self.quick_section)

        # Suggestions
        self.suggestion_list = QListWidget()
        self.suggestion_list.setObjectName("suggestionList")
        self.suggestion_list.setMaximumHeight(110)
        self.suggestion_list.setFont(QFont("Consolas", 9))
        self.suggestion_list.hide()
        self.suggestion_list.itemClicked.connect(self._on_suggestion_clicked)
        layout.addWidget(self.suggestion_list)

        # Input row
        input_container = QFrame()
        input_container.setObjectName("inputContainer")
        input_lyt = QHBoxLayout(input_container)
        input_lyt.setContentsMargins(14, 10, 10, 10)
        input_lyt.setSpacing(10)

        self.input_field = QLineEdit()
        self.input_field.setObjectName("inputField")
        self.input_field.setPlaceholderText(
            "Ask anything or give a command…  (/history, /rerun N)"
        )
        self.input_field.setFont(QFont("Consolas", 10))
        self.input_field.returnPressed.connect(self._submit)
        self.input_field.textChanged.connect(self._on_text_changed)

        send_btn = QPushButton("SEND  ↵")
        send_btn.setObjectName("sendBtn")
        send_btn.setFont(QFont("Consolas", 9, QFont.Bold))
        send_btn.setFixedWidth(110)
        send_btn.clicked.connect(self._submit)

        input_lyt.addWidget(self.input_field)
        input_lyt.addWidget(send_btn)
        layout.addWidget(input_container)
        layout.addSpacing(8)

    # Public
    def append_message(self, role: str, content: str, mode: str, theme: dict):
        t = theme
        if role == "user":
            name_color, text_color, prefix = t["accent"], t["text"], "YOU"
        elif role == "system":
            name_color, text_color, prefix = t["dim"], t["dim"], "SYS"
        else:
            name_color = "#888888"
            text_color = t["text"]
            mode_tag_map = {
                "command":    f"<span style='color:{t['accent']};font-size:7pt'>[ CMD ]</span>",
                "powershell": "<span style='color:#ce93d8;font-size:7pt'>[ PWSH ]</span>",
                "wikipedia":  "<span style='color:#80cbc4;font-size:7pt'>[ WIKI ]</span>",
                "browser":    "<span style='color:#80deea;font-size:7pt'>[ BROWSER ]</span>",
                "music":      "<span style='color:#ce93d8;font-size:7pt'>[ MUSIC ]</span>",
                "search":     f"<span style='color:{t['accent2']};font-size:7pt'>[ SEARCH ]</span>",
                "show_apps":  "<span style='color:#90caf9;font-size:7pt'>[ APPS ]</span>",
                "time":       "<span style='color:#fff59d;font-size:7pt'>[ TIME ]</span>",
                "quick_open": f"<span style='color:{t['accent']};font-size:7pt'>[ QUICK ]</span>",
                "explain":    "<span style='color:#ffcc80;font-size:7pt'>[ EXPLAIN ]</span>",
                "image_gen":  f"<span style='color:{t['accent2']};font-size:7pt'>[ IMAGE GEN ]</span>",
            }
            tag = mode_tag_map.get(mode, "")
            prefix = f"ARIA  {tag}"

        timestamp = datetime.now().strftime("%H:%M:%S")
        safe = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        safe = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe)
        safe = re.sub(
            r"`([^`]+)`",
            rf'<code style="background:{t["chat_bg"]};color:{t["accent"]};padding:1px 4px;border-radius:2px;">\1</code>',
            safe,
        )
        html = f"""
        <div style='margin-bottom:14px;border-left:2px solid {t["border"]};padding-left:10px;'>
            <div style='font-size:7.5pt;color:{t["dim"]};margin-bottom:3px;letter-spacing:1px;'>
                <span style='color:{name_color};'>{prefix}</span>
                &nbsp;&nbsp;<span style='color:{t["border"]};'>{timestamp}</span>
            </div>
            <div style='color:{text_color};line-height:1.65;white-space:pre-wrap;font-size:10pt;'>{safe}</div>
        </div>
        """
        self.chat_display.append(html)
        self.chat_display.moveCursor(QTextCursor.End)

    def show_image(self, b64: str, border: str):
        html = f"""
        <div style='margin-bottom:14px;border-left:2px solid {border};padding-left:10px;'>
            <img src='data:image/png;base64,{b64}'
                 style='max-width:400px;border-radius:6px;border:1px solid {border};'/>
        </div>
        """
        self.chat_display.append(html)
        self.chat_display.moveCursor(QTextCursor.End)

    def show_suggestions(self, suggestions: list):
        self.suggestion_list.clear()
        for s in suggestions:
            self.suggestion_list.addItem(QListWidgetItem(s))
        self.suggestion_list.setVisible(bool(suggestions))

    def set_input_placeholder(self, text: str):
        self.input_field.setPlaceholderText(text)

    # Private
    def _submit(self):
        text = self.input_field.text().strip()
        if text:
            self.input_field.clear()
            self.suggestion_list.hide()
            self.message_submitted.emit(text)

    def _on_suggestion_clicked(self, item: QListWidgetItem):
        self.input_field.setText(item.text())
        self.suggestion_list.hide()
        self.input_field.setFocus()

    def _on_text_changed(self, text: str):
        from constants import SUGGESTION_MAP
        text_lower = text.lower().strip()
        if not text_lower:
            self.suggestion_list.hide()
            return
        suggestions = []
        for trigger, options in SUGGESTION_MAP.items():
            if text_lower.startswith(trigger.lower()):
                suggestions = [o for o in options if text_lower in o.lower() or o.lower().startswith(text_lower)]
                break
            elif trigger.lower() in text_lower:
                suggestions = options[:4]
                break
        self.show_suggestions(suggestions[:6]) if suggestions else self.suggestion_list.hide()

    def _build_quick_actions(self):
        def _btn(label, cmd):
            b = QPushButton(label)
            b.setObjectName("actionBtn")
            b.setFont(QFont("Consolas", 8))
            b.clicked.connect(lambda _c, c=cmd: self.quick_action.emit(c))
            return b

        self.quick_section.add_row([
            _btn("YouTube", "open YouTube"), _btn("Google", "open Google"),
            _btn("Stack Overflow", "open Stack Overflow"), _btn("Spotify", "open Spotify"),
        ])
        self.quick_section.add_row([
            _btn("VS Code", "open code"), _btn("CMD", "open cmd"),
            _btn("Play Music", "play music"), _btn("Time", "what time is it"),
        ])
        self.quick_section.add_row([
            _btn("PDFs", "search pdf"), _btn("Python", "search py"),
            _btn("Docs", "search docx"), _btn("Show Apps", "show apps"),
        ])
        self.quick_section.add_row([
            _btn("Top Memory", "show top memory apps"),
            _btn("Services", "list running services"),
            _btn("Open Ports", "show open ports"),
            _btn("Flush DNS", "flush dns"),
        ])

# Terminal page
class TerminalPage(QWidget):
    command_submitted = pyqtSignal(str)
    export_requested  = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        self.terminal_display = QTextEdit()
        self.terminal_display.setObjectName("terminalDisplay")
        self.terminal_display.setReadOnly(True)
        self.terminal_display.setFont(QFont("Consolas", 9))
        layout.addWidget(self.terminal_display, stretch=1)

        # Quick command buttons
        quick_row = QHBoxLayout()
        quick_row.setSpacing(6)
        for label, cmd in [
            ("Dir",       "dir %USERPROFILE%"),
            ("Processes", "tasklist"),
            ("Network",   "ipconfig"),
            ("System",    'systeminfo | findstr /C:"OS" /C:"Memory"'),
            ("Disks",     "wmic logicaldisk get caption,freespace,size"),
        ]:
            btn = QPushButton(label)
            btn.setObjectName("quickBtn")
            btn.setFont(QFont("Consolas", 8))
            btn.clicked.connect(lambda _c, c=cmd: self.command_submitted.emit(c))
            quick_row.addWidget(btn)
        layout.addLayout(quick_row)

        # Input row
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.terminal_input = QLineEdit()
        self.terminal_input.setObjectName("terminalInput")
        self.terminal_input.setPlaceholderText("Enter Windows command…")
        self.terminal_input.setFont(QFont("Consolas", 10))
        self.terminal_input.returnPressed.connect(self._submit)

        run_btn = QPushButton("▶  Run")
        run_btn.setObjectName("termRunBtn")
        run_btn.setFont(QFont("Consolas", 9, QFont.Bold))
        run_btn.setFixedWidth(90)
        run_btn.clicked.connect(self._submit)

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("termClearBtn")
        clear_btn.setFont(QFont("Consolas", 9))
        clear_btn.setFixedWidth(70)
        clear_btn.clicked.connect(self.terminal_display.clear)

        export_btn = QPushButton("Export")
        export_btn.setObjectName("termClearBtn")
        export_btn.setFont(QFont("Consolas", 9))
        export_btn.setFixedWidth(70)
        export_btn.clicked.connect(self.export_requested.emit)

        input_row.addWidget(self.terminal_input)
        input_row.addWidget(run_btn)
        input_row.addWidget(clear_btn)
        input_row.addWidget(export_btn)
        layout.addLayout(input_row)

    def append_output(self, command: str, output: str, dim: str, accent: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.terminal_display.append(
            f"<span style='color:{dim}'>[{timestamp}]</span> "
            f"<span style='color:{accent}'>$ {command}</span>"
        )
        color = "#ef9a9a" if output.startswith(("❌", "⛔")) else "#6a9a6a"
        self.terminal_display.append(f"<span style='color:{color}'>{output}</span>\n")

    def append_warning(self, message: str):
        self.terminal_display.append(
            f"<span style='color:#ffcc00'>⚠ {message}</span>\n"
        )

    def append_error(self, message: str):
        self.terminal_display.append(
            f"<span style='color:#ef9a9a'>Error: {message}</span>\n"
        )

    def append_info(self, message: str):
        self.terminal_display.append(
            f"<span style='color:#4caf50'>{message}</span>\n"
        )

    def _submit(self):
        cmd = self.terminal_input.text().strip()
        if cmd:
            self.terminal_input.clear()
            self.command_submitted.emit(cmd)

# Timeline page
class TimelinePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        header = QLabel("Execution Timeline")
        header.setObjectName("pageTitle")
        header.setFont(QFont("Consolas", 10, QFont.Bold))
        layout.addWidget(header)

        self.timeline_display = QTextEdit()
        self.timeline_display.setObjectName("terminalDisplay")
        self.timeline_display.setReadOnly(True)
        self.timeline_display.setFont(QFont("Consolas", 9))
        layout.addWidget(self.timeline_display, stretch=1)

        clear_btn = QPushButton("Clear Timeline")
        clear_btn.setObjectName("termClearBtn")
        clear_btn.setFont(QFont("Consolas", 9))
        clear_btn.setFixedWidth(130)
        clear_btn.clicked.connect(self.timeline_display.clear)
        layout.addWidget(clear_btn)

    def add_entry(self, timestamp: str, action: str, status: str, dim: str):
        icon  = "✔" if status == "ok" else "✖"
        color = "#4caf50" if status == "ok" else "#f44336"
        self.timeline_display.append(
            f"<span style='color:{dim};'>[{timestamp}]</span> "
            f"<span style='color:{color};'>{icon}</span> "
            f"<span style='color:#aaa;'>{action}</span>"
        )
        self.timeline_display.moveCursor(QTextCursor.End)

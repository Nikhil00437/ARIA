# widgets.py — Glassy minimal reusable UI components

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame,
)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, pyqtSignal


class Toast(QFrame):
    """Non-intrusive toast notification widget with auto-dismiss.

    Theming is driven by the global stylesheet (see ``styles.py``): the
    frame uses ``#Toast`` (left border color varies via the ``toastKind``
    dynamic property) and the inner labels/button use the matching object
    names. Inline QSS is only used for per-instance icon glyph sizing.
    """

    TOAST_TYPES = {
        "info":    ("\u2139",  "info"),
        "success": ("\u2713", "success"),
        "warning": ("\u26a0", "warning"),
        "error":   ("\u2715", "error"),
    }

    def __init__(self, message: str, toast_type: str = "info", duration: int = 3000, parent=None):
        super().__init__(parent)
        self._message = message
        self._toast_type = toast_type

        icon, kind = self.TOAST_TYPES.get(toast_type, self.TOAST_TYPES["info"])

        self.setFixedHeight(40)
        self.setMinimumWidth(280)
        self.setMaximumWidth(420)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # Theme via global stylesheet (left-border color varies with kind).
        self.setObjectName("Toast")
        self.setProperty("toastKind", kind)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        self._icon = QLabel(icon)
        self._icon.setFixedWidth(18)
        layout.addWidget(self._icon)

        self._label = QLabel(message)
        self._label.setObjectName("ToastLabel")
        self._label.setWordWrap(True)
        layout.addWidget(self._label, 1)

        self._close_btn = QPushButton("\u00d7")
        self._close_btn.setObjectName("ToastClose")
        self._close_btn.setFixedSize(22, 22)
        self._close_btn.clicked.connect(self.close)
        layout.addWidget(self._close_btn)

        self._opacity = 0.0
        self._animation = QPropertyAnimation(self, b"windowOpacity")
        self._animation.setDuration(300)

        if duration > 0:
            QTimer.singleShot(duration, self._animate_out)

    def showEvent(self, event):
        super().showEvent(event)
        self._animate_in()

    def _animate_in(self):
        self.setWindowOpacity(0.0)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.start()

    def _animate_out(self):
        self._animation.setStartValue(1.0)
        self._animation.setEndValue(0.0)
        self._animation.finished.connect(self.close)
        self._animation.start()


class ToastManager(QWidget):
    """Manages a stack of toast notifications."""
    
    # Signals
    toast_requested = pyqtSignal(str, str, int)  # message, type, duration
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        
        # Position in bottom-right corner
        self._margin = 20
        self._spacing = 10
        self._toasts: list[Toast] = []
        
        # Install event filter to capture keyboard
        self.setFocusPolicy(Qt.NoFocus)
    
    def show_toast(self, message: str, toast_type: str = "info", duration: int = 3000):
        """Show a new toast notification."""
        toast = Toast(message, toast_type, duration, self)
        toast.destroyed.connect(lambda: self._on_toast_closed(toast))
        self._toasts.append(toast)
        self._layout_toasts()
        toast.show()
    
    def _on_toast_closed(self, toast: Toast):
        if toast in self._toasts:
            self._toasts.remove(toast)
        self._layout_toasts()
    
    def _layout_toasts(self):
        if not self._toasts:
            self.hide()
            return
        
        self.show()
        
        # Position toasts in bottom-right, stacking upward
        parent = self.parent()
        if parent:
            parent_w = parent.width()
            parent_h = parent.height()
        else:
            parent_w = 800
            parent_h = 600
        
        x = parent_w - self.width() - self._margin
        y = parent_h - self._margin
        
        for toast in reversed(self._toasts):
            h = toast.height()
            y -= h + self._spacing
            toast.move(x, y)
        
        # Resize to contain all toasts
        total_h = sum(t.height() + self._spacing for t in self._toasts) - self._spacing
        self.setFixedSize(400, total_h)
    
    def info(self, message: str, duration: int = 3000):
        self.show_toast(message, "info", duration)
    
    def success(self, message: str, duration: int = 3000):
        self.show_toast(message, "success", duration)
    
    def warning(self, message: str, duration: int = 4000):
        self.show_toast(message, "warning", duration)
    
    def error(self, message: str, duration: int = 5000):
        self.show_toast(message, "error", duration)


class CollapsibleSection(QWidget):
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

    def add_widget(self, widget: QWidget):
        self._content_layout.addWidget(widget)

    def _toggle(self):
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        text = self._toggle_btn.text()
        self._toggle_btn.setText(("▾" if self._expanded else "▸") + text[1:])


class StatusBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StatusBar")
        self.setFixedHeight(28)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 0, 18, 0)
        layout.setSpacing(10)

        self._dot = QLabel("●")
        self._dot.setObjectName("StatusDot")
        self._dot.setFixedWidth(14)
        self._dot.setStyleSheet(
            "color: rgba(80,200,120,0.9); background: transparent; font-size: 9px;"
        )

        self._status_label = QLabel("Initializing…")
        self._status_label.setObjectName("StatusLabel")

        # Version tag
        ver = QLabel("ARIA v2")
        ver.setStyleSheet(
            "color: rgba(255,255,255,0.35); font-size: 7.5pt; "
            "font-family: 'Cascadia Code', 'Consolas', monospace; "
            "background: transparent;"
        )

        self._llm_label = QLabel("LLM  ·  –")
        self._llm_label.setObjectName("LLMLabel")
        self._llm_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        layout.addWidget(self._dot)
        layout.addWidget(self._status_label, 1)
        layout.addWidget(ver)
        layout.addWidget(self._llm_label)

    def set_status(self, text: str):
        self._status_label.setText(text)

    def set_online(self, online: bool):
        color = "rgba(80,200,120,0.9)" if online else "rgba(255,80,80,0.9)"
        self._dot.setStyleSheet(
            f"color: {color}; background: transparent; font-size: 9px;"
        )

    def set_llm(self, model: str):
        self._llm_label.setText(f"⬡  {model}")


class TypingIndicator(QLabel):
    _FRAMES = ["·   ·   ·", "●   ·   ·", "●   ●   ·", "●   ●   ●"]

    def __init__(self, parent=None):
        super().__init__("", parent)
        self.setObjectName("TypingIndicator")
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_frame)
        self._frame = 0

    def start(self):
        self.show()
        if not self._timer.isActive():
            self._timer.start(380)

    def stop(self):
        self._timer.stop()
        self.setText("")
        self.hide()

    def _update_frame(self):
        self._frame = (self._frame + 1) % len(self._FRAMES)
        self.setText(f"  aria is thinking  {self._FRAMES[self._frame]}")


class ConfidenceBadge(QLabel):
    """Small pill badge showing a confidence percentage.

    Theming via global stylesheet. Per-instance variant is selected by
    setting the object name to one of ``ConfidenceBadgeHigh`` / ``ConfidenceBadgeMid``
    / ``ConfidenceBadgeLow`` so QSS picks up the correct color tier.
    """

    def __init__(self, confidence: float, parent=None):
        pct = int(confidence * 100)
        super().__init__(f"{pct}%", parent)

        if pct >= 85:
            name = "ConfidenceBadgeHigh"
        elif pct >= 60:
            name = "ConfidenceBadgeMid"
        else:
            name = "ConfidenceBadgeLow"

        self.setObjectName(name)


class Separator(QFrame):
    """Thin 1px hairline separator. Themed via global stylesheet."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Plain)
        self.setObjectName("Separator")
        self.setFixedHeight(1)


class GlassCard(QFrame):
    """Generic flat card widget. Themed via the ``#Card`` selector."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")


class CommandPalette(QFrame):
    """Quick command palette triggered by Ctrl+K."""
    
    # Signal emitted when a command is selected
    command_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setFixedSize(500, 400)
        self.setObjectName("CommandPalette")
        
        # Default commands
        self._commands = [
            {"id": "new_session", "label": "New Session", "shortcut": "Ctrl+N", "category": "Session"},
            {"id": "settings", "label": "Settings", "shortcut": "", "category": "App"},
            {"id": "toggle_voice", "label": "Toggle Voice Output", "shortcut": "", "category": "Voice"},
            {"id": "toggle_silent", "label": "Toggle Silent Mode", "shortcut": "", "category": "Voice"},
            {"id": "goto_chat", "label": "Go to Chat", "shortcut": "Alt+1", "category": "Navigation"},
            {"id": "goto_terminal", "label": "Go to Terminal", "shortcut": "Alt+2", "category": "Navigation"},
            {"id": "goto_patterns", "label": "Go to Patterns", "shortcut": "Alt+3", "category": "Navigation"},
            {"id": "goto_warnings", "label": "Go to Warnings", "shortcut": "Alt+4", "category": "Navigation"},
            {"id": "goto_selfmod", "label": "Go to Self-Mod", "shortcut": "Alt+5", "category": "Navigation"},
            {"id": "run_selfmod", "label": "Run Behavioral Analysis", "shortcut": "", "category": "Analysis"},
            {"id": "show_context", "label": "Show Context", "shortcut": "", "category": "Debug"},
            {"id": "show_sessions", "label": "List Sessions", "shortcut": "", "category": "Session"},
            {"id": "clear_chat", "label": "Clear Chat", "shortcut": "", "category": "Session"},
            {"id": "show_shortcuts", "label": "Keyboard Shortcuts", "shortcut": "Ctrl+/", "category": "Help"},
        ]
        
        self._filtered_commands = self._commands
        self._selected_index = 0
        
        self._build_ui()
    
    def _build_ui(self):
        from PyQt5.QtWidgets import QLineEdit, QListWidget, QListWidgetItem

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Search input (themed via #CommandPaletteInput)
        self._search = QLineEdit()
        self._search.setObjectName("CommandPaletteInput")
        self._search.setPlaceholderText("Type a command...")
        self._search.textChanged.connect(self._on_search_changed)
        self._search.installEventFilter(self)
        layout.addWidget(self._search)

        # Command list (themed via #CommandPaletteList)
        self._list = QListWidget()
        self._list.setObjectName("CommandPaletteList")
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        layout.addWidget(self._list)

        # Populate list
        self._update_list()
    
    def _update_list(self):
        from PyQt5.QtWidgets import QListWidgetItem
        self._list.clear()
        
        for cmd in self._filtered_commands:
            item = QListWidgetItem()
            
            # Format: label (shortcut) - category
            text = cmd["label"]
            if cmd["shortcut"]:
                text += f"  [{cmd['shortcut']}]"
            text += f"\n  {cmd['category']}"
            
            item.setText(text)
            item.setData(Qt.UserRole, cmd["id"])
            self._list.addItem(item)
        
        # Select first item
        if self._filtered_commands:
            self._list.setCurrentRow(0)
    
    def _on_search_changed(self, text: str):
        text_lower = text.lower().strip()
        
        if not text_lower:
            self._filtered_commands = self._commands
        else:
            self._filtered_commands = [
                c for c in self._commands
                if text_lower in c["label"].lower() or text_lower in c["category"].lower()
            ]
        
        self._selected_index = 0
        self._update_list()
    
    def _on_item_clicked(self, item):
        cmd_id = item.data(Qt.UserRole)
        self.command_selected.emit(cmd_id)
        self.close()
    
    def show_at(self, x: int, y: int):
        """Show palette at specific position."""
        self.move(x - self.width() // 2, y - 50)
        self._search.clear()
        self._filtered_commands = self._commands
        self._update_list()
        self.show()
        self._search.setFocus()
    
    def eventFilter(self, obj, event):
        """Handle keyboard events."""
        from PyQt5.QtCore import QEvent
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Up:
                self._move_selection(-1)
                return True
            elif event.key() == Qt.Key_Down:
                self._move_selection(1)
                return True
            elif event.key() == Qt.Key_Return:
                self._execute_selected()
                return True
            elif event.key() == Qt.Key_Escape:
                self.close()
                return True
        return super().eventFilter(obj, event)
    
    def _move_selection(self, delta: int):
        new_index = self._selected_index + delta
        if 0 <= new_index < len(self._filtered_commands):
            self._selected_index = new_index
            self._list.setCurrentRow(new_index)
    
    def _execute_selected(self):
        if 0 <= self._selected_index < len(self._filtered_commands):
            cmd_id = self._filtered_commands[self._selected_index]["id"]
            self.command_selected.emit(cmd_id)
            self.close()


class ConfirmDialog(QFrame):
    """Confirmation dialog for destructive actions."""
    
    # Signal must be a class attribute in PyQt5 for connect() to work
    confirmed = pyqtSignal(bool)
    
    def __init__(self, title: str, message: str, confirm_text: str = "Confirm", cancel_text: str = "Cancel",
                 confirm_style: str = "danger", parent=None):
        super().__init__(parent)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setFixedSize(400, 180)
        self.setObjectName("ConfirmDialog")

        # Style drives only the confirm-button variant via object name.
        if confirm_style == "danger":
            primary_name = "RejectBtn"  # red
        elif confirm_style == "warning":
            primary_name = "PatternRunBtn"  # accent but visually distinct
        else:
            primary_name = "DialogBtnPrimary"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title_label = QLabel(title)
        title_label.setObjectName("DialogTitle")
        layout.addWidget(title_label)

        msg_label = QLabel(message)
        msg_label.setObjectName("DialogMessage")
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        cancel_btn = QPushButton(cancel_text)
        cancel_btn.setObjectName("DialogBtn")
        cancel_btn.setFixedSize(110, 34)
        cancel_btn.clicked.connect(lambda: self._respond(False))

        confirm_btn = QPushButton(confirm_text)
        confirm_btn.setObjectName(primary_name)
        confirm_btn.setFixedSize(110, 34)
        confirm_btn.clicked.connect(lambda: self._respond(True))

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(confirm_btn)
        layout.addLayout(btn_layout)
    
    def _respond(self, confirmed: bool):
        self.confirmed.emit(confirmed)
        self.close()
    
    def show_at(self, x: int, y: int):
        """Show dialog at specific position."""
        self.move(x - self.width() // 2, y - self.height() // 2)
        self.show()
        self.setFocus()








class KeyboardShortcutsHelp(QFrame):
    """Show keyboard shortcuts help dialog."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setFixedSize(400, 450)
        self.setObjectName("KeyboardShortcutsHelp")
        
        self._build_ui()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(10)

        title = QLabel("Keyboard Shortcuts")
        title.setObjectName("DialogTitle")
        layout.addWidget(title)

        shortcuts = [
            ("General", [
                ("Ctrl+K", "Open command palette"),
                ("Ctrl+N", "New session"),
                ("Ctrl+W", "Close window"),
                ("Escape", "Minimize window"),
            ]),
            ("Navigation", [
                ("Alt+1", "Go to Chat"),
                ("Alt+2", "Go to Terminal"),
                ("Alt+3", "Go to Agent"),
                ("Alt+4", "Go to Patterns"),
                ("Alt+5", "Go to Warnings"),
                ("Alt+6", "Go to Self-Mod"),
            ]),
            ("Chat", [
                ("Enter", "Send message"),
                ("Shift+Enter", "New line"),
            ]),
        ]

        for category, items in shortcuts:
            cat_label = QLabel(category)
            cat_label.setObjectName("SectionHeader")
            layout.addWidget(cat_label)

            for shortcut, description in items:
                row = QHBoxLayout()
                row.setSpacing(10)

                key_label = QLabel(shortcut)
                key_label.setObjectName("SidebarStatLabel")
                key_label.setStyleSheet(
                    "background: #1D1F26; padding: 2px 6px; border-radius: 3px;"
                )
                # The global #SidebarStatLabel selector provides the
                # monospace font + size; the per-instance inline QSS adds the
                # chip background and compact padding.
                key_label.setAlignment(Qt.AlignCenter)
                key_label.setMinimumWidth(80)

                desc_label = QLabel(description)
                desc_label.setStyleSheet("color: #9CA3AF; font-size: 9pt; background: transparent;")

                row.addWidget(key_label)
                row.addWidget(desc_label, 1)
                row.addStretch()
                layout.addLayout(row)

        close_hint = QLabel("Press Escape to close")
        close_hint.setStyleSheet("color: #525866; font-size: 8pt; background: transparent; padding-top: 12px;")
        close_hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(close_hint)
    
    def show_at(self, x: int, y: int):
        """Show dialog at specific position."""
        self.move(x - self.width() // 2, y - self.height() // 2)
        self.show()
        self.setFocus()




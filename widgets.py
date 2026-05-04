# widgets.py — Glassy minimal reusable UI components

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QPainterPath, QFont


class Toast(QFrame):
    """Non-intrusive toast notification widget with auto-dismiss."""
    
    TOAST_TYPES = {
        "info": ("rgba(80,180,255,0.9)", "rgba(80,180,255,0.15)", "ℹ"),
        "success": ("rgba(80,200,120,0.9)", "rgba(80,200,120,0.15)", "✓"),
        "warning": ("rgba(255,180,40,0.9)", "rgba(255,180,40,0.15)", "⚠"),
        "error": ("rgba(255,80,80,0.9)", "rgba(255,80,80,0.15)", "✕"),
    }
    
    def __init__(self, message: str, toast_type: str = "info", duration: int = 3000, parent=None):
        super().__init__(parent)
        self._message = message
        self._toast_type = toast_type
        self._duration = duration
        
        # Get colors for this type
        color, bg, icon = self.TOAST_TYPES.get(toast_type, self.TOAST_TYPES["info"])
        
        self.setFixedHeight(44)
        self.setMinimumWidth(280)
        self.setMaximumWidth(400)
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        # Glassy style
        self.setStyleSheet(f"""
            Toast {{
                background: {bg};
                border: 1px solid {color};
                border-radius: 10px;
            }}
        """)
        
        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)
        
        # Icon
        self._icon = QLabel(icon)
        self._icon.setStyleSheet(f"color: {color}; font-size: 14pt; background: transparent;")
        self._icon.setFixedWidth(20)
        layout.addWidget(self._icon)
        
        # Message
        self._label = QLabel(message)
        self._label.setStyleSheet(f"color: white; font-size: 9pt; background: transparent;")
        self._label.setWordWrap(True)
        layout.addWidget(self._label, 1)
        
        # Close button
        self._close_btn = QPushButton("×")
        self._close_btn.setFixedSize(20, 20)
        self._close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: rgba(255,255,255,0.5);
                font-size: 14pt;
                font-weight: bold;
            }
            QPushButton:hover {
                color: white;
            }
        """)
        self._close_btn.clicked.connect(self.close)
        layout.addWidget(self._close_btn)
        
        # Animation setup
        self._opacity = 0.0
        self._animation = QPropertyAnimation(self, b"windowOpacity")
        self._animation.setDuration(300)
        
        # Auto-dismiss timer
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
    def __init__(self, confidence: float, parent=None):
        pct = int(confidence * 100)
        super().__init__(f"{pct}%", parent)

        if pct >= 85:
            color, bg = "rgba(80,180,255,0.9)", "rgba(80,180,255,0.10)"
            border = "rgba(80,180,255,0.35)"
        elif pct >= 65:
            color, bg = "rgba(255,180,40,0.9)", "rgba(255,180,40,0.10)"
            border = "rgba(255,180,40,0.35)"
        else:
            color, bg = "rgba(255,80,80,0.9)", "rgba(255,80,80,0.10)"
            border = "rgba(255,80,80,0.35)"

        self.setStyleSheet(
            f"background: {bg}; color: {color};"
            f"border: 1px solid {border};"
            "border-radius: 10px;"
            "padding: 2px 8px;"
            "font-size: 8pt;"
            "font-weight: 700;"
            "font-family: 'Cascadia Code', 'Consolas', monospace;"
        )


class Separator(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Plain)
        self.setStyleSheet(
            "background: transparent; border: none; "
            "border-top: 1px solid rgba(255,255,255,0.10);"
        )
        self.setFixedHeight(1)


class GlassCard(QFrame):
    """Reusable frosted glass card widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "GlassCard {"
            "  background: rgba(255,255,255,0.10);"
            "  border: 1px solid rgba(255,255,255,0.18);"
            "  border-radius: 16px;"
            "}"
        )


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
        
        self.setStyleSheet("""
            CommandPalette {
                background: rgba(20, 25, 45, 0.98);
                border: 1px solid rgba(80, 180, 255, 0.4);
                border-radius: 12px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Search input
        self._search = QLineEdit()
        self._search.setPlaceholderText("Type a command...")
        self._search.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                border-bottom: 1px solid rgba(255,255,255,0.15);
                padding: 16px 20px;
                color: white;
                font-size: 14pt;
                font-family: 'Segoe UI', sans-serif;
            }
            QLineEdit::placeholder {
                color: rgba(255,255,255,0.4);
            }
        """)
        self._search.textChanged.connect(self._on_search_changed)
        self._search.installEventFilter(self)
        layout.addWidget(self._search)
        
        # Command list
        self._list = QListWidget()
        self._list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                padding: 8px;
            }
            QListWidget::item {
                color: rgba(255,255,255,0.85);
                padding: 10px 16px;
                border-radius: 6px;
            }
            QListWidget::item:selected {
                background: rgba(80, 180, 255, 0.25);
                color: white;
            }
            QListWidget::item:hover {
                background: rgba(255,255,255,0.08);
            }
        """)
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
    
    # Signal emitted with True for confirmed, False for cancelled
    confirmed = None  # Will be defined in __init__
    
    def __init__(self, title: str, message: str, confirm_text: str = "Confirm", cancel_text: str = "Cancel", 
                 confirm_style: str = "danger", parent=None):
        super().__init__(parent)
        from PyQt5.QtCore import pyqtSignal
        self.confirmed = pyqtSignal(bool)
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setFixedSize(400, 180)
        self.setObjectName("ConfirmDialog")
        
        # Style based on type
        if confirm_style == "danger":
            confirm_color = "rgba(255,80,80,0.9)"
            confirm_bg = "rgba(255,80,80,0.15)"
        elif confirm_style == "warning":
            confirm_color = "rgba(255,180,40,0.9)"
            confirm_bg = "rgba(255,180,40,0.15)"
        else:
            confirm_color = "rgba(80,180,255,0.9)"
            confirm_bg = "rgba(80,180,255,0.15)"
        
        self.setStyleSheet(f"""
            ConfirmDialog {{
                background: rgba(20, 25, 45, 0.98);
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 12px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            color: white;
            font-size: 14pt;
            font-weight: 600;
            background: transparent;
        """)
        layout.addWidget(title_label)
        
        # Message
        msg_label = QLabel(message)
        msg_label.setStyleSheet("""
            color: rgba(255,255,255,0.7);
            font-size: 10pt;
            background: transparent;
        """)
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        cancel_btn = QPushButton(cancel_text)
        cancel_btn.setFixedSize(120, 36)
        cancel_btn.setStyleSheet("""
            QPushButton {{
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 8px;
                color: rgba(255,255,255,0.8);
                font-size: 10pt;
            }}
            QPushButton:hover {{
                background: rgba(255,255,255,0.15);
            }}
        """)
        cancel_btn.clicked.connect(lambda: self._respond(False))
        
        confirm_btn = QPushButton(confirm_text)
        confirm_btn.setFixedSize(120, 36)
        confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background: {confirm_bg};
                border: 1px solid {confirm_color};
                border-radius: 8px;
                color: {confirm_color};
                font-size: 10pt;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {confirm_color};
                color: white;
            }}
        """)
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


class TabBar(QWidget):
    """Horizontal tab bar for conversation tabs."""
    
    tab_selected = None  # Will be defined in __init__
    tab_closed = None
    new_tab_requested = None
    
    def __init__(self, parent=None):
        super().__init__(parent)
        from PyQt5.QtCore import pyqtSignal
        self.tab_selected = pyqtSignal(str)  # tab_id
        self.tab_closed = pyqtSignal(str)    # tab_id
        self.new_tab_requested = pyqtSignal()
        
        self.setFixedHeight(40)
        self.setObjectName("TabBar")
        
        self._tabs: List[Dict] = []  # {id, title, is_active}
        self._active_tab_id: Optional[str] = None
        
        self._build_ui()
    
    def _build_ui(self):
        from PyQt5.QtWidgets import QScrollArea, QListWidget, QListWidgetItem
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(4)
        
        # Tab list (horizontal)
        self._tab_list = QListWidget()
        self._tab_list.setOrientation(Qt.Horizontal)
        self._tab_list.setFlow(QListWidget.LeftToRight)
        self._tab_list.setSpacing(2)
        self._tab_list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
            }
            QListWidget::item {
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px;
                padding: 6px 12px;
                margin: 2px;
            }
            QListWidget::item:selected {
                background: rgba(80,180,255,0.25);
                border: 1px solid rgba(80,180,255,0.5);
            }
            QListWidget::item:hover:!selected {
                background: rgba(255,255,255,0.12);
            }
        """)
        self._tab_list.currentRowChanged.connect(self._on_tab_changed)
        self._tab_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        layout.addWidget(self._tab_list, 1)
        
        # New tab button
        self._new_btn = QPushButton("+")
        self._new_btn.setFixedSize(28, 28)
        self._new_btn.setStyleSheet("""
            QPushButton {
                background: rgba(80,180,255,0.15);
                border: 1px solid rgba(80,180,255,0.3);
                border-radius: 6px;
                color: rgba(80,180,255,0.9);
                font-size: 16pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(80,180,255,0.3);
            }
        """)
        self._new_btn.clicked.connect(self.new_tab_requested.emit)
        layout.addWidget(self._new_btn)
    
    def add_tab(self, tab_id: str, title: str, is_active: bool = False):
        """Add a new tab."""
        self._tabs.append({"id": tab_id, "title": title, "is_active": is_active})
        self._update_tabs()
        
        if is_active:
            self._active_tab_id = tab_id
            # Find and select the tab
            for i, tab in enumerate(self._tabs):
                if tab["id"] == tab_id:
                    self._tab_list.setCurrentRow(i)
                    break
    
    def remove_tab(self, tab_id: str):
        """Remove a tab."""
        self._tabs = [t for t in self._tabs if t["id"] != tab_id]
        self._update_tabs()
        
        if self._active_tab_id == tab_id:
            self._active_tab_id = self._tabs[0]["id"] if self._tabs else None
    
    def update_tab_title(self, tab_id: str, title: str):
        """Update a tab's title."""
        for tab in self._tabs:
            if tab["id"] == tab_id:
                tab["title"] = title
                break
        self._update_tabs()
    
    def set_active_tab(self, tab_id: str):
        """Set the active tab."""
        self._active_tab_id = tab_id
        for i, tab in enumerate(self._tabs):
            if tab["id"] == tab_id:
                self._tab_list.setCurrentRow(i)
                break
    
    def _update_tabs(self):
        """Update the tab list display."""
        self._tab_list.clear()
        
        for tab in self._tabs:
            item = QListWidgetItem(tab["title"])
            item.setData(Qt.UserRole, tab["id"])
            
            # Add close button indicator
            if tab["id"] == self._active_tab_id:
                item.setText(f"● {tab['title']}")
            else:
                item.setText(tab["title"])
            
            self._tab_list.addItem(item)
    
    def _on_tab_changed(self, index: int):
        if 0 <= index < len(self._tabs):
            tab = self._tabs[index]
            self._active_tab_id = tab["id"]
            self.tab_selected.emit(tab["id"])


class SearchBar(QWidget):
    """Search bar for finding messages in conversation."""
    
    search_triggered = None  # Will be defined in __init__
    search_closed = None
    
    def __init__(self, parent=None):
        super().__init__(parent)
        from PyQt5.QtCore import pyqtSignal
        self.search_triggered = pyqtSignal(str)  # search query
        self.search_closed = pyqtSignal()
        
        self.setFixedHeight(44)
        self.setObjectName("SearchBar")
        self.hide()  # Hidden by default
        
        self._build_ui()
    
    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)
        
        # Search icon
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("background: transparent; font-size: 12pt;")
        layout.addWidget(search_icon)
        
        # Search input
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search messages...")
        self._search_input.setStyleSheet("""
            QLineEdit {
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 6px;
                padding: 8px 12px;
                color: white;
                font-size: 10pt;
            }
            QLineEdit::placeholder {
                color: rgba(255,255,255,0.4);
            }
            QLineEdit:focus {
                border: 1px solid rgba(80,180,255,0.5);
            }
        """)
        self._search_input.textChanged.connect(self._on_search_changed)
        self._search_input.returnPressed.connect(self._on_search_submit)
        layout.addWidget(self._search_input, 1)
        
        # Result count
        self._result_label = QLabel("")
        self._result_label.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 9pt; background: transparent;")
        layout.addWidget(self._result_label)
        
        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: rgba(255,255,255,0.5);
                font-size: 14pt;
            }
            QPushButton:hover {
                color: white;
            }
        """)
        close_btn.clicked.connect(self.hide)
        close_btn.clicked.connect(self.search_closed.emit)
        layout.addWidget(close_btn)
    
    def show(self):
        super().show()
        self._search_input.setFocus()
    
    def _on_search_changed(self, text: str):
        if text:
            self.search_triggered.emit(text)
        else:
            self._result_label.setText("")
    
    def _on_search_submit(self):
        self.search_triggered.emit(self._search_input.text())
    
    def set_result_count(self, count: int, current: int = 0):
        """Set the search result count display."""
        if count > 0:
            self._result_label.setText(f"{current}/{count}")
        else:
            self._result_label.setText("No results")


class LoadingSkeleton(QFrame):
    """Animated loading skeleton for better perceived performance."""
    
    def __init__(self, height: int = 20, parent=None):
        super().__init__(parent)
        self.setFixedHeight(height)
        self.setObjectName("LoadingSkeleton")
        
        self.setStyleSheet("""
            LoadingSkeleton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(255,255,255,0.02), stop:0.5 rgba(255,255,255,0.08), stop:1 rgba(255,255,255,0.02));
                border-radius: 4px;
            }
        """)


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
        self.setStyleSheet("""
            KeyboardShortcutsHelp {
                background: rgba(20, 25, 45, 0.98);
                border: 1px solid rgba(80, 180, 255, 0.4);
                border-radius: 12px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("⌨️ Keyboard Shortcuts")
        title.setStyleSheet("""
            color: white;
            font-size: 14pt;
            font-weight: 600;
            background: transparent;
        """)
        layout.addWidget(title)
        
        # Shortcuts
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
                ("Alt+3", "Go to Patterns"),
                ("Alt+4", "Go to Warnings"),
                ("Alt+5", "Go to Self-Mod"),
            ]),
            ("Chat", [
                ("Enter", "Send message"),
                ("Shift+Enter", "New line"),
            ]),
        ]
        
        for category, items in shortcuts:
            # Category header
            cat_label = QLabel(category)
            cat_label.setStyleSheet("""
                color: rgba(120, 180, 255, 0.9);
                font-size: 9pt;
                font-weight: 600;
                background: transparent;
                padding-top: 8px;
            """)
            layout.addWidget(cat_label)
            
            # Shortcut items
            for shortcut, description in items:
                row = QHBoxLayout()
                row.setSpacing(8)
                
                key_label = QLabel(shortcut)
                key_label.setStyleSheet("""
                    color: rgba(255, 255, 255, 0.9);
                    font-size: 8.5pt;
                    font-family: 'Cascadia Code', 'Consolas', monospace;
                    background: rgba(255, 255, 255, 0.1);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 4px;
                    padding: 2px 8px;
                """)
                
                desc_label = QLabel(description)
                desc_label.setStyleSheet("""
                    color: rgba(255, 255, 255, 0.6);
                    font-size: 8.5pt;
                    background: transparent;
                """)
                
                row.addWidget(key_label)
                row.addWidget(desc_label, 1)
                layout.addLayout(row)
        
        # Close hint
        close_hint = QLabel("Press Escape to close")
        close_hint.setStyleSheet("""
            color: rgba(255, 255, 255, 0.35);
            font-size: 8pt;
            background: transparent;
            padding-top: 12px;
        """)
        close_hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(close_hint)
    
    def show_at(self, x: int, y: int):
        """Show dialog at specific position."""
        self.move(x - self.width() // 2, y - self.height() // 2)
        self.show()
        self.setFocus()


class AnimatedIcon(QWidget):
    """Animated icon with pulse/glow effects."""
    
    def __init__(self, icon: str = "●", parent=None):
        super().__init__(parent)
        self._icon = icon
        self.setFixedSize(24, 24)
        
        self._animation = QPropertyAnimation(self, b"windowOpacity")
        self._animation.setDuration(1500)
        self._animation.setStartValue(0.5)
        self._animation.setEndValue(1.0)
        self._animation.setEasingCurve(QEasingCurve.InOutSine)
        self._animation.setLoopCount(-1)
    
    def showEvent(self, event):
        super().showEvent(event)
        self._animation.start()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw icon with current opacity
        opacity = self.windowOpacity()
        color = QColor(80, 180, 255, int(255 * opacity))
        painter.setPen(color)
        painter.setFont(QFont("Segoe UI", 14))
        painter.drawText(self.rect(), Qt.AlignCenter, self._icon)


class ErrorBanner(QFrame):
    """Error banner with dismiss button."""
    
    def __init__(self, message: str, parent=None):
        super().__init__(parent)
        self.setObjectName("ErrorBanner")
        self.setFixedHeight(50)
        
        self.setStyleSheet("""
            ErrorBanner {
                background: rgba(255, 60, 60, 0.15);
                border: 1px solid rgba(255, 60, 60, 0.4);
                border-radius: 8px;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)
        
        # Error icon
        icon = QLabel("⚠️")
        icon.setStyleSheet("background: transparent; font-size: 14pt;")
        layout.addWidget(icon)
        
        # Error message
        msg = QLabel(message)
        msg.setStyleSheet("""
            color: rgba(255, 200, 200, 0.9);
            font-size: 9pt;
            background: transparent;
        """)
        layout.addWidget(msg, 1)
        
        # Dismiss button
        dismiss = QPushButton("×")
        dismiss.setFixedSize(24, 24)
        dismiss.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: rgba(255, 200, 200, 0.6);
                font-size: 14pt;
            }
            QPushButton:hover {
                color: white;
            }
        """)
        dismiss.clicked.connect(self.hide)
        dismiss.clicked.connect(self.deleteLater)
        layout.addWidget(dismiss)

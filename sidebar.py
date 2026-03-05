from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from constants import THEMES

class Sidebar(QFrame):
    # Emitted when a nav button is clicked (page index)
    page_changed   = pyqtSignal(int)
    voice_toggled  = pyqtSignal(bool)
    silent_toggled = pyqtSignal(bool)
    theme_changed  = pyqtSignal(str)
    image_mode_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(230)

        self._voice_on  = False
        self._silent_on = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo
        logo_frame = QFrame()
        logo_frame.setObjectName("logoFrame")
        logo_frame.setFixedHeight(72)
        logo_lyt = QVBoxLayout(logo_frame)
        logo_lyt.setContentsMargins(20, 0, 0, 0)
        logo_lyt.setAlignment(Qt.AlignVCenter)
        logo_lbl = QLabel("◈  ARIA")
        logo_lbl.setObjectName("logoLabel")
        logo_lbl.setFont(QFont("Consolas", 15, QFont.Bold))
        logo_lyt.addWidget(logo_lbl)
        layout.addWidget(logo_frame)
        layout.addWidget(self._divider())

        # Nav buttons
        self.nav_buttons: dict[str, QPushButton] = {}
        nav_items = [
            ("chat_btn",     "●  Chat",     0),
            ("term_btn",     "■  Terminal", 1),
            ("timeline_btn", "◉  Timeline", 2),
        ]
        for obj_name, label, idx in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("navBtn")
            btn.setCheckable(True)
            btn.setFont(QFont("Consolas", 10))
            btn.setFixedHeight(46)
            btn.clicked.connect(lambda _checked, i=idx: self.page_changed.emit(i))
            layout.addWidget(btn)
            self.nav_buttons[obj_name] = btn

        layout.addStretch()
        layout.addWidget(self._divider())

        # Health label 
        self.health_label = QLabel("● System OK")
        self.health_label.setObjectName("healthLabel")
        self.health_label.setFont(QFont("Consolas", 8))
        self.health_label.setContentsMargins(16, 6, 10, 0)
        layout.addWidget(self.health_label)

        # System info as ListWidget 
        self.sys_list = QListWidget()
        self.sys_list.setObjectName("sysListWidget")
        self.sys_list.setFixedHeight(72)          # shows ~4 rows
        self.sys_list.setFocusPolicy(Qt.NoFocus)
        self.sys_list.setSelectionMode(QListWidget.NoSelection)
        self.sys_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.sys_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._add_sys_row("Loading system info…")
        layout.addWidget(self.sys_list)

        # Voice toggles 
        self.voice_btn = QPushButton("  ○  Voice  OFF")
        self.voice_btn.setObjectName("voiceBtn")
        self.voice_btn.setFont(QFont("Consolas", 9, QFont.Bold))
        self.voice_btn.setFixedHeight(38)
        self.voice_btn.clicked.connect(self._on_voice)
        layout.addWidget(self.voice_btn)

        self.silent_btn = QPushButton("  ○  Silent Voice  OFF")
        self.silent_btn.setObjectName("voiceBtn")
        self.silent_btn.setFont(QFont("Consolas", 9))
        self.silent_btn.setFixedHeight(34)
        self.silent_btn.clicked.connect(self._on_silent)
        layout.addWidget(self.silent_btn)

        # Theme row
        theme_row = QHBoxLayout()
        theme_row.setContentsMargins(12, 4, 12, 0)
        theme_row.setSpacing(4)
        for name in THEMES:
            tb = QPushButton(name.capitalize())
            tb.setObjectName("themeBtn")
            tb.setFont(QFont("Consolas", 7))
            tb.setFixedHeight(24)
            tb.clicked.connect(lambda _c, n=name: self.theme_changed.emit(n))
            theme_row.addWidget(tb)
        layout.addLayout(theme_row)
        layout.addSpacing(6)

        # Image mode button
        img_btn = QPushButton("  ◈  Image Mode")
        img_btn.setObjectName("voiceBtn")
        img_btn.setFont(QFont("Consolas", 9))
        img_btn.setFixedHeight(34)
        img_btn.clicked.connect(self.image_mode_clicked.emit)
        layout.addWidget(img_btn)
        layout.addSpacing(10)

    # Public helpers
    def set_active_page(self, index: int):
        for i, key in enumerate(self.nav_buttons):
            self.nav_buttons[key].setChecked(i == index)

    def update_sys_info(self, rows: list[str]):
        self.sys_list.clear()
        for row in rows:
            self._add_sys_row(row)

    def set_health(self, message: str, color: str):
        self.health_label.setText(message)
        self.health_label.setStyleSheet(f"color: {color};")

    # Private
    def _add_sys_row(self, text: str):
        from PyQt5.QtWidgets import QListWidgetItem
        item = QListWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
        self.sys_list.addItem(item)

    @staticmethod
    def _divider() -> QFrame:
        d = QFrame()
        d.setObjectName("divider")
        d.setFixedHeight(1)
        return d

    def _on_voice(self):
        self._voice_on = not self._voice_on
        dot = "●" if self._voice_on else "○"
        state = "ON" if self._voice_on else "OFF"
        self.voice_btn.setText(f"  {dot}  Voice  {state}")
        self.voice_toggled.emit(self._voice_on)

    def _on_silent(self):
        self._silent_on = not self._silent_on
        dot = "●" if self._silent_on else "○"
        state = "ON" if self._silent_on else "OFF"
        self.silent_btn.setText(f"  {dot}  Silent Voice  {state}")
        self.silent_toggled.emit(self._silent_on)

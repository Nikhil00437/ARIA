# settings_dialog.py — Glassy minimal settings with theme, model, and preferences

from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QComboBox,
    QCheckBox, QSpinBox,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QLinearGradient
from constants import CHAT_MODEL, THEMES

# Theme swatches are sourced from the THEMES dict so changes to the palette
# preview accurately. Each tuple is (bg, bg2, accent, text, border).
def _swatches(theme_id: str) -> tuple:
    t = THEMES.get(theme_id, {})
    return (
        t.get("bg", "#0E0F13"),
        t.get("bg2", "#16181D"),
        t.get("accent", "#8B8CF7"),
        t.get("text", "#E6E8EE"),
        t.get("border", "#262932"),
    )

COLOR_THEMES = [
    {
        "id":      "minimal",
        "name":    "Minimal",
        "tagline": "Clean light · Indigo",
        "swatches": _swatches("minimal"),
    },
    {
        "id":      "cyber",
        "name":    "Cyber",
        "tagline": "Modern dark · Indigo on slate",
        "swatches": _swatches("cyber"),
    },
    {
        "id":      "classic",
        "name":    "Classic",
        "tagline": "Monochrome · Silver",
        "swatches": _swatches("classic"),
    },
]


class ColorCard(QWidget):
    selected = pyqtSignal(str)

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self._id = theme["id"]
        self._selected = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(180, 110)
        self.setObjectName("ColorCard")
        self.setProperty("themeId", theme["id"])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        name = QLabel(theme["name"])
        name.setStyleSheet("color: #E6E8EE; font-size: 13px; font-weight: 700;"
                            "font-family: 'Segoe UI Variable', 'Segoe UI'; background: transparent;")
        layout.addWidget(name)

        tag = QLabel(theme["tagline"])
        tag.setStyleSheet("color: #9CA3AF; font-size: 8.5px;"
                          "font-family: 'Cascadia Code', 'Consolas'; background: transparent;")
        layout.addWidget(tag)
        layout.addStretch()

        row = QHBoxLayout()
        row.setSpacing(5)
        for color in theme["swatches"]:
            dot = QFrame()
            dot.setFixedSize(14, 14)
            dot.setStyleSheet(
                f"background: {color}; border-radius: 7px;"
                "border: 1px solid rgba(255,255,255,0.10);"
            )
            row.addWidget(dot)
        row.addStretch()
        layout.addLayout(row)

    def set_selected(self, v: bool):
        self._selected = v
        self.setProperty("selected", v)
        # Re-apply object-name styling with the dynamic property.
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, _):
        self.selected.emit(self._id)


class SettingsDialog(QDialog):
    theme_changed = pyqtSignal(str)
    model_changed = pyqtSignal(str)
    tts_toggled = pyqtSignal(bool)
    suggestion_count_changed = pyqtSignal(int)
    response_length_changed = pyqtSignal(str)
    # Agent harness settings (Phase 6)
    agent_mode_changed = pyqtSignal(str)
    agent_max_steps_changed = pyqtSignal(int)

    def __init__(self, current_color: str = "minimal", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)
        self.setFixedSize(640, 580)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._color = current_color
        self._cards: dict[str, ColorCard] = {}
        self._model: str = CHAT_MODEL
        self._tts_enabled: bool = False
        self._suggestion_count: int = 3
        self._response_length: str = "balanced"
        # Agent defaults — kept in sync with constants.AGENT_* via main_window.
        # main_window seeds these from the live config before showing the dialog.
        self._agent_mode: str = "plan_apply"
        self._agent_max_steps: int = 25
        self._build()
        self._select(current_color)

    def set_agent_defaults(self, mode: str, max_steps: int) -> None:
        """Seed the agent section from the live config (called before exec)."""
        self._agent_mode = mode if mode in ("plan_apply", "auto_workspace") else "plan_apply"
        self._agent_max_steps = max(1, min(int(max_steps), 100))
        if hasattr(self, "_agent_mode_combo"):
            idx = self._agent_mode_combo.findText(self._agent_mode)
            if idx >= 0:
                self._agent_mode_combo.setCurrentIndex(idx)
        if hasattr(self, "_agent_steps_spin"):
            self._agent_steps_spin.setValue(self._agent_max_steps)

    def paintEvent(self, event):
        """Paint a dark gradient behind the dialog, sourced from the active theme."""
        from constants import DEFAULT_THEME
        t = THEMES.get(DEFAULT_THEME, {})
        bg_a = t.get("bg", "#0E0F13")
        bg2 = t.get("bg2", "#16181D")
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        c1 = QColor(bg_a)
        c1.setAlpha(248)
        c2 = QColor(bg2)
        c2.setAlpha(248)
        grad.setColorAt(0.0, c1)
        grad.setColorAt(1.0, c2)
        painter.fillRect(self.rect(), grad)
        painter.end()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        box = QWidget()
        box.setObjectName("SettingsBox")
        outer.addWidget(box)

        root = QVBoxLayout(box)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title bar (themed via #SettingsTB / #SettingsLabel / #SCloseBtn)
        tb = QWidget()
        tb.setObjectName("SettingsTB")
        tb.setFixedHeight(50)
        tb_lyt = QHBoxLayout(tb)
        tb_lyt.setContentsMargins(22, 0, 14, 0)

        icon = QLabel("\u2699")
        icon.setStyleSheet(
            "color: #8B8CF7; font-size: 15px; background: transparent;"
        )

        title = QLabel("Settings")
        title.setStyleSheet(
            "color: #E6E8EE; font-size: 14px; font-weight: 700;"
            "font-family: 'Segoe UI Variable', 'Segoe UI'; letter-spacing: 0.5px;"
            "background: transparent;"
        )

        close = QPushButton("\u00d7")
        close.setObjectName("SCloseBtn")
        close.setFixedSize(30, 30)
        close.clicked.connect(self.reject)

        tb_lyt.addWidget(icon)
        tb_lyt.addSpacing(8)
        tb_lyt.addWidget(title)
        tb_lyt.addStretch()
        tb_lyt.addWidget(close)
        root.addWidget(tb)

        divider = QFrame()
        divider.setObjectName("SettingsDivider")
        divider.setFixedHeight(1)
        root.addWidget(divider)

        # Body
        body = QWidget()
        body_lyt = QVBoxLayout(body)
        body_lyt.setContentsMargins(22, 18, 22, 18)
        body_lyt.setSpacing(14)

        # ── Theme section ──
        sec_theme = QLabel("Color Theme")
        sec_theme.setObjectName("SettingsSection")
        body_lyt.addWidget(sec_theme)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        for t in COLOR_THEMES:
            card = ColorCard(t)
            card.selected.connect(self._select)
            self._cards[t["id"]] = card
            cards_row.addWidget(card)
        cards_row.addStretch()
        body_lyt.addLayout(cards_row)

        body_lyt.addWidget(self._div())

        # ── Model section ──
        sec_model = QLabel("Model")
        sec_model.setObjectName("SettingsSection")
        body_lyt.addWidget(sec_model)

        model_row = QHBoxLayout()
        model_row.setSpacing(10)
        model_label = QLabel("Chat model:")
        model_label.setObjectName("SettingsLabel")
        self._model_combo = QComboBox()
        self._model_combo.setObjectName("SettingsCombo")
        self._model_combo.setMinimumWidth(280)
        self._model_combo.addItems([
            "qwen/qwen3.5-9b",
            "qwen/qwen3.5-14b",
            "qwen/qwen3.5-32b",
            "mistral/mistral-7b-v0.3",
            "llama/llama-3.1-8b",
            "deepseek/deepseek-v3",
            "phi/microsoft-phi-4",
        ])
        idx = self._model_combo.findText(self._model)
        if idx >= 0:
            self._model_combo.setCurrentIndex(idx)
        model_row.addWidget(model_label)
        model_row.addWidget(self._model_combo, 1)
        body_lyt.addLayout(model_row)

        body_lyt.addWidget(self._div())

        # ── Preferences section ──
        sec_pref = QLabel("Preferences")
        sec_pref.setObjectName("SettingsSection")
        body_lyt.addWidget(sec_pref)

        # TTS toggle
        self._tts_check = QCheckBox("Text-to-Speech enabled")
        self._tts_check.setObjectName("SettingsCheck")
        self._tts_check.setChecked(self._tts_enabled)
        body_lyt.addWidget(self._tts_check)

        # Suggestion count
        sc_row = QHBoxLayout()
        sc_row.setSpacing(10)
        sc_label = QLabel("Suggestions per row:")
        sc_label.setObjectName("SettingsLabel")
        self._sc_spin = QSpinBox()
        self._sc_spin.setObjectName("SettingsSpin")
        self._sc_spin.setRange(1, 6)
        self._sc_spin.setValue(self._suggestion_count)
        self._sc_spin.setFixedWidth(72)
        sc_row.addWidget(sc_label)
        sc_row.addWidget(self._sc_spin)
        sc_row.addStretch()
        body_lyt.addLayout(sc_row)

        # Response length
        rl_row = QHBoxLayout()
        rl_row.setSpacing(10)
        rl_label = QLabel("Response length:")
        rl_label.setObjectName("SettingsLabel")
        self._rl_combo = QComboBox()
        self._rl_combo.setObjectName("SettingsCombo")
        self._rl_combo.setMinimumWidth(160)
        self._rl_combo.addItems(["concise", "balanced", "verbose"])
        rl_idx = self._rl_combo.findText(self._response_length)
        if rl_idx >= 0:
            self._rl_combo.setCurrentIndex(rl_idx)
        rl_row.addWidget(rl_label)
        rl_row.addWidget(self._rl_combo, 1)
        body_lyt.addLayout(rl_row)

        # ── Agent section (Phase 6) ──
        body_lyt.addWidget(self._div())
        sec_agent = QLabel("Agent")
        sec_agent.setObjectName("SettingsSection")
        body_lyt.addWidget(sec_agent)
        agent_desc = QLabel(
            "Configure the multi-step coding agent (see the Agent page)."
        )
        agent_desc.setStyleSheet(
            "color: #9CA3AF; font-size: 9.5px; background: transparent;"
        )
        agent_desc.setWordWrap(True)
        body_lyt.addWidget(agent_desc)

        # Agent mode
        am_row = QHBoxLayout()
        am_row.setSpacing(10)
        am_label = QLabel("Default mode:")
        am_label.setObjectName("SettingsLabel")
        self._agent_mode_combo = QComboBox()
        self._agent_mode_combo.setObjectName("SettingsCombo")
        self._agent_mode_combo.setMinimumWidth(220)
        self._agent_mode_combo.addItems(["plan_apply", "auto_workspace"])
        am_idx = self._agent_mode_combo.findText(self._agent_mode)
        if am_idx >= 0:
            self._agent_mode_combo.setCurrentIndex(am_idx)
        am_row.addWidget(am_label)
        am_row.addWidget(self._agent_mode_combo, 1)
        body_lyt.addLayout(am_row)

        # Agent max steps
        steps_row = QHBoxLayout()
        steps_row.setSpacing(10)
        steps_label = QLabel("Max steps per task:")
        steps_label.setObjectName("SettingsLabel")
        self._agent_steps_spin = QSpinBox()
        self._agent_steps_spin.setObjectName("SettingsSpin")
        self._agent_steps_spin.setRange(1, 100)
        self._agent_steps_spin.setValue(self._agent_max_steps)
        self._agent_steps_spin.setFixedWidth(72)
        steps_row.addWidget(steps_label)
        steps_row.addWidget(self._agent_steps_spin)
        steps_row.addStretch()
        body_lyt.addLayout(steps_row)

        body_lyt.addStretch()
        root.addWidget(body, 1)

        # Footer (themed via #SettingsFoot / #SCloseBtn / #SCancelBtn / #SApplyBtn)
        fd = QFrame()
        fd.setObjectName("SettingsDivider")
        fd.setFixedHeight(1)
        root.addWidget(fd)

        foot = QWidget()
        foot.setObjectName("SettingsFoot")
        foot.setFixedHeight(54)
        foot_lyt = QHBoxLayout(foot)
        foot_lyt.setContentsMargins(22, 0, 22, 0)

        self._preview = QLabel("")
        self._preview.setObjectName("SettingsPreview")
        foot_lyt.addWidget(self._preview)
        foot_lyt.addStretch()

        cancel = QPushButton("Cancel")
        cancel.setObjectName("SCancelBtn")
        cancel.setFixedSize(88, 34)
        cancel.clicked.connect(self.reject)

        apply = QPushButton("Apply")
        apply.setObjectName("SApplyBtn")
        apply.setFixedSize(88, 34)
        apply.clicked.connect(self._apply)

        foot_lyt.addWidget(cancel)
        foot_lyt.addSpacing(8)
        foot_lyt.addWidget(apply)
        root.addWidget(foot)
        # All styling is now driven by the global stylesheet via the matching
        # object names (#SettingsBox, #SettingsTB, #SettingsFoot, #SettingsLabel,
        # #SettingsSection, #SettingsDivider, #SCloseBtn, #SCancelBtn, #SApplyBtn,
        # #SettingsCombo, #SettingsSpin, #SettingsCheck, #ColorCard).

    def _select(self, color_id: str):
        self._color = color_id
        for cid, card in self._cards.items():
            card.set_selected(cid == color_id)
        name = next((t["name"] for t in COLOR_THEMES if t["id"] == color_id), color_id)
        self._preview.setText(f"Selected: {name}")

    def _apply(self):
        self.theme_changed.emit(self._color)
        self.model_changed.emit(self._model_combo.currentText())
        self.tts_toggled.emit(self._tts_check.isChecked())
        self.suggestion_count_changed.emit(self._sc_spin.value())
        self._response_length = self._rl_combo.currentText()
        self.response_length_changed.emit(self._response_length)
        # Agent (Phase 6)
        self._agent_mode = self._agent_mode_combo.currentText()
        self._agent_max_steps = self._agent_steps_spin.value()
        self.agent_mode_changed.emit(self._agent_mode)
        self.agent_max_steps_changed.emit(self._agent_max_steps)
        self.accept()

    def _div(self) -> QFrame:
        """Themed horizontal hairline divider."""
        d = QFrame()
        d.setObjectName("SettingsDivider")
        d.setFixedHeight(1)
        return d

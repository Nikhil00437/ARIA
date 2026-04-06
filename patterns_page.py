# patterns_page.py — Fabric Patterns browser + runner UI page

import threading
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QSplitter, QTextEdit, QSizePolicy,
    QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QTextCursor

from pattern_engine import list_patterns, load_pattern, search_patterns, run_pattern_stream


class PatternCard(QWidget):
    # Single pattern entry in the browser list.
    selected = pyqtSignal(str)   # pattern name

    def __init__(self, name: str, preview: str, parent=None):
        super().__init__(parent)
        self._name = name
        self.setObjectName("PatternCard")
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(3)

        name_label = QLabel(name.replace("_", " ").title())
        name_label.setObjectName("PatternCardName")

        slug_label = QLabel(f"/{name}")
        slug_label.setObjectName("PatternCardSlug")

        preview_label = QLabel(preview)
        preview_label.setObjectName("PatternCardPreview")
        preview_label.setWordWrap(True)

        layout.addWidget(name_label)
        layout.addWidget(slug_label)
        layout.addWidget(preview_label)

    def mousePressEvent(self, event):
        self.selected.emit(self._name)

    def set_active(self, active: bool):
        self.setObjectName("PatternCardActive" if active else "PatternCard")
        self.style().unpolish(self)
        self.style().polish(self)


class PatternsPage(QWidget):
    # Full Patterns page:
    #   Left  — searchable pattern browser
    #   Right — selected pattern details + input + run button + streaming output
    run_requested = pyqtSignal(str, str)   # (pattern_name, user_input)

    def __init__(self, llm_client=None, signals=None, parent=None):
        super().__init__(parent)
        self.setObjectName("PatternsPage")
        self._llm        = llm_client
        self._signals    = signals
        self._current    = None
        self._all_cards: dict[str, PatternCard] = {}
        self._gen        = 0   # generation counter to cancel stale streams

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Accent bar at top
        accent = QFrame()
        accent.setFixedHeight(3)
        accent.setStyleSheet("background: #10b981;")
        # Wrap everything vertically with accent on top
        wrapper = QVBoxLayout()
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.setSpacing(0)
        wrapper.addWidget(accent)

        # Content row
        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(0)

        # Left panel: browser
        left = QWidget()
        left.setObjectName("PatternBrowser")
        left.setFixedWidth(240)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # Search bar
        search_bar = QWidget()
        search_bar.setObjectName("PatternSearchBar")
        search_lyt = QHBoxLayout(search_bar)
        search_lyt.setContentsMargins(10, 8, 10, 8)

        self._search = QLineEdit()
        self._search.setObjectName("PatternSearch")
        self._search.setPlaceholderText("Search patterns…")
        self._search.textChanged.connect(self._on_search)
        search_lyt.addWidget(self._search)
        left_layout.addWidget(search_bar)

        # Count label
        self._count_label = QLabel("Loading…")
        self._count_label.setObjectName("PatternCount")
        self._count_label.setContentsMargins(12, 4, 0, 4)
        left_layout.addWidget(self._count_label)

        # Pattern list scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(6, 4, 6, 8)
        self._list_layout.setSpacing(4)
        self._list_layout.addStretch()

        scroll.setWidget(self._list_container)
        left_layout.addWidget(scroll, 1)

        content_row.addWidget(left)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.VLine)
        div.setObjectName("PatternDivider")
        content_row.addWidget(div)

        # Right panel: runner
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(20, 16, 20, 16)
        right_layout.setSpacing(10)

        # Header
        header_row = QHBoxLayout()
        self._pattern_title = QLabel("Select a pattern")
        self._pattern_title.setObjectName("SectionHeader")
        header_row.addWidget(self._pattern_title)
        header_row.addStretch()

        self._copy_btn = QPushButton("Copy Output")
        self._copy_btn.setObjectName("PatternActionBtn")
        self._copy_btn.clicked.connect(self._copy_output)
        self._copy_btn.hide()
        header_row.addWidget(self._copy_btn)

        self._save_btn = QPushButton("Save .md")
        self._save_btn.setObjectName("PatternActionBtn")
        self._save_btn.clicked.connect(self._save_output)
        self._save_btn.hide()
        header_row.addWidget(self._save_btn)

        right_layout.addLayout(header_row)

        # Pattern description
        self._desc_label = QLabel("Browse patterns on the left, or type /pattern <name> in chat.")
        self._desc_label.setObjectName("ProposalMeta")
        self._desc_label.setWordWrap(True)
        right_layout.addWidget(self._desc_label)

        # System prompt preview (collapsible)
        self._prompt_preview = QTextEdit()
        self._prompt_preview.setObjectName("PatternPromptPreview")
        self._prompt_preview.setReadOnly(True)
        self._prompt_preview.setMaximumHeight(120)
        self._prompt_preview.setPlaceholderText("Pattern system prompt will appear here…")
        self._prompt_preview.hide()
        right_layout.addWidget(self._prompt_preview)

        toggle_btn = QPushButton("▶  Show system prompt")
        toggle_btn.setObjectName("PatternToggleBtn")
        toggle_btn.setCheckable(True)
        toggle_btn.clicked.connect(lambda checked: (
            self._prompt_preview.setVisible(checked),
            toggle_btn.setText("▼  Hide system prompt" if checked else "▶  Show system prompt")
        ))
        toggle_btn.hide()
        self._toggle_btn = toggle_btn
        right_layout.addWidget(toggle_btn)

        # Input area
        input_row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setObjectName("PatternInput")
        self._input.setPlaceholderText("Paste text, URL, or leave blank to run pattern standalone…")
        self._input.returnPressed.connect(self._run)

        self._run_btn = QPushButton("▶  Run Pattern")
        self._run_btn.setObjectName("PatternRunBtn")
        self._run_btn.clicked.connect(self._run)
        self._run_btn.setFixedWidth(130)
        self._run_btn.setEnabled(False)

        input_row.addWidget(self._input)
        input_row.addWidget(self._run_btn)
        right_layout.addLayout(input_row)

        # Output area
        self._output = QTextEdit()
        self._output.setObjectName("PatternOutput")
        self._output.setReadOnly(True)
        self._output.setFont(QFont("Cascadia Code", 9))
        self._output.setPlaceholderText("Pattern output will stream here…")
        right_layout.addWidget(self._output, 1)

        # Status label
        self._status = QLabel("")
        self._status.setObjectName("PatternStatus")
        right_layout.addWidget(self._status)

        content_row.addWidget(right, 1)

        # Assemble
        wrapper.addLayout(content_row, 1)
        layout.addLayout(wrapper)

        # Load patterns async
        QTimer.singleShot(100, self._load_patterns)

    # Pattern loading
    def _load_patterns(self):
        def _run():
            patterns = list_patterns()
            QTimer.singleShot(0, lambda: self._populate_list(patterns))
        threading.Thread(target=_run, daemon=True).start()

    def _populate_list(self, patterns: list):
        # Clear
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            w = item.widget() if item else None
            if w:
                w.setParent(None)
                w.deleteLater()

        self._all_cards.clear()
        for p in patterns:
            card = PatternCard(p["name"], p["preview"])
            card.selected.connect(self._select_pattern)
            self._list_layout.insertWidget(self._list_layout.count() - 1, card)
            self._all_cards[p["name"]] = card

        n = len(patterns)
        self._count_label.setText(f"{n} pattern{'s' if n != 1 else ''}")

    def _on_search(self, query: str):
        if not query.strip():
            for card in self._all_cards.values():
                card.show()
            self._count_label.setText(f"{len(self._all_cards)} patterns")
            return

        results = {p["name"] for p in search_patterns(query)}
        shown = 0
        for name, card in self._all_cards.items():
            visible = name in results
            card.setVisible(visible)
            if visible:
                shown += 1
        self._count_label.setText(f"{shown} match{'es' if shown != 1 else ''}")

    # Pattern selection
    def select_pattern(self, name: str): self._select_pattern(name)     # Public — called from chat_engine slash command.
       
    def _select_pattern(self, name: str):
        # Deactivate previous card
        if self._current and self._current in self._all_cards:
            self._all_cards[self._current].set_active(False)

        self._current = name

        if name in self._all_cards: self._all_cards[name].set_active(True)

        self._pattern_title.setText(name.replace("_", " ").title())

        # Load system prompt
        system_prompt = load_pattern(name)
        if system_prompt:
            self._prompt_preview.setPlainText(system_prompt)
            # Extract first paragraph as description
            lines = [l.strip() for l in system_prompt.splitlines() if l.strip() and not l.startswith("#")]
            desc = lines[0][:200] + "…" if lines else ""
            self._desc_label.setText(desc)
        else: self._desc_label.setText(f"Pattern '{name}' not found in patterns folder.")

        self._run_btn.setEnabled(bool(system_prompt))
        self._toggle_btn.show()
        self._copy_btn.show()
        self._save_btn.show()
        self._output.clear()
        self._status.setText("")

    # Running
    def _run(self):
        if not self._current or not self._llm: return
        user_input = self._input.text().strip()
        self._output.clear()
        self._status.setText("⬡  Running…")
        self._run_btn.setEnabled(False)
        self._gen += 1
        my_gen = self._gen

        def _stream():
            try:
                for chunk in run_pattern_stream(self._current, user_input, self._llm):
                    if self._gen != my_gen:
                        return
                    QTimer.singleShot(0, lambda c=chunk: self._append_chunk(c))
                QTimer.singleShot(0, lambda: self._on_done())
            except Exception as e: QTimer.singleShot(0, lambda: self._on_error(str(e)))

        threading.Thread(target=_stream, daemon=True).start()

    def _append_chunk(self, chunk: str):
        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.End)
        self._output.setTextCursor(cursor)
        self._output.insertPlainText(chunk)
        self._output.moveCursor(QTextCursor.End)

    def _on_done(self):
        self._status.setText("✓  Done")
        self._run_btn.setEnabled(True)
        # Also emit to chat so it appears in chat history
        if self._signals:
            result = self._output.toPlainText()
            self._signals.chat_response.emit("assistant",
                f"**Pattern: {self._current}**\n\n{result}"
            )

    def _on_error(self, msg: str):
        self._status.setText(f"❌ {msg}")
        self._run_btn.setEnabled(True)

    # Actions
    def _copy_output(self):
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(self._output.toPlainText())
        self._status.setText("✓  Copied to clipboard")
        QTimer.singleShot(2000, lambda: self._status.setText(""))

    def _save_output(self):
        from PyQt5.QtWidgets import QFileDialog
        import datetime
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default = f"aria_{self._current}_{ts}.md"
        path, _ = QFileDialog.getSaveFileName(self, "Save Output", default, "Markdown (*.md);;Text (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# {self._current}\n\n")
                f.write(self._output.toPlainText())
            self._status.setText(f"✓  Saved to {path}")

    # Public: wire LLM after boot
    def set_llm(self, llm_client):
        self._llm = llm_client
        if self._llm: self._run_btn.setEnabled(bool(self._current))
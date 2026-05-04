from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QPushButton, QTabWidget, QFileDialog, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from widgets import ConfidenceBadge, Separator

#  Proposal Card
class ProposalCard(QWidget):
    approved = pyqtSignal(str)   # proposal_id
    rejected = pyqtSignal(str)

    def __init__(self, proposal: dict, parent=None):
        super().__init__(parent)
        self._id = proposal["id"]
        self.setObjectName("ProposalCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        # Header
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        title_text = proposal.get("param_label", proposal.get("param_key", "?"))
        title = QLabel(f"⬡  {title_text}")
        title.setObjectName("ProposalTitle")

        badge = ConfidenceBadge(proposal.get("confidence", 0.0))

        src = proposal.get("source", "?")
        source_tag = QLabel(f"[{src}]")
        source_tag.setObjectName("ProposalMeta")

        header_row.addWidget(title, 1)
        header_row.addWidget(badge)
        header_row.addWidget(source_tag)
        layout.addLayout(header_row)
        # Proposal description
        proposal_text = QLabel(proposal.get("proposal_text", ""))
        proposal_text.setObjectName("ProposalText")
        proposal_text.setWordWrap(True)
        layout.addWidget(proposal_text)
        # Proposed value pill
        val_row = QHBoxLayout()
        val_row.setSpacing(6)

        val_key = QLabel("New value")
        val_key.setObjectName("ProposalMeta")

        val_label = QLabel(f"  {proposal.get('param_value')}  ")
        val_label.setStyleSheet(
            "background: rgba(80,200,120,0.10);"
            "color: rgba(80,200,120,0.9);"
            "border: 1px solid rgba(80,200,120,0.30);"
            "border-radius: 6px;"
            "padding: 2px 10px;"
            "font-family: 'Cascadia Code', 'Consolas', monospace;"
            "font-size: 8.5pt;"
            "font-weight: 600;"
        )
        val_row.addWidget(val_key)
        val_row.addWidget(val_label)
        val_row.addStretch()
        layout.addLayout(val_row)
        # Description hint
        desc_text = proposal.get("param_desc", "")
        if desc_text:
            desc = QLabel(desc_text)
            desc.setObjectName("ProposalMeta")
            desc.setWordWrap(True)
            layout.addWidget(desc)

        sep = Separator()
        layout.addWidget(sep)
        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        approve_btn = QPushButton("✓  Approve")
        approve_btn.setObjectName("ApproveBtn")
        approve_btn.clicked.connect(lambda: self.approved.emit(self._id))

        reject_btn = QPushButton("✕  Reject")
        reject_btn.setObjectName("RejectBtn")
        reject_btn.clicked.connect(lambda: self.rejected.emit(self._id))

        btn_row.addWidget(approve_btn)
        btn_row.addWidget(reject_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

#  Ledger Entry
class LedgerEntryWidget(QWidget):
    rollback_requested = pyqtSignal(str)

    def __init__(self, entry: dict, parent=None):
        super().__init__(parent)
        rolled   = entry.get("rolled_back", False)
        rejected = entry.get("rejected", False)
        self.setObjectName("LedgerEntryRolledBack" if rolled else "LedgerEntry")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)
        # Status icon
        if rolled:      icon_text, icon_color = "↩", "rgba(255,180,40,0.9)"
        elif rejected:  icon_text, icon_color = "✕", "rgba(255,80,80,0.9)"
        else:           icon_text, icon_color = "✓", "rgba(80,200,120,0.9)"

        icon = QLabel(icon_text)
        icon.setFixedWidth(18)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(f"color: {icon_color}; background: transparent; font-weight: 700; font-size: 10pt;")
        layout.addWidget(icon)
        # Change description
        label = entry.get("param_label", entry.get("param_key", "?"))
        if not rejected and not rolled: change_html = (
                f"<b>{label}</b>"
                f"  <span style='color:rgba(140,120,255,0.9);'>→</span>  "
                f"<code style='color:rgba(80,200,120,0.9);'>{entry.get('new_value')}</code>"
                f"  <span style='color:rgba(255,255,255,0.35);font-size:8pt;'>"
                f"was <code>{entry.get('old_value')}</code></span>"
            )
        elif rejected: change_html = f"<b>{label}</b>  <span style='color:rgba(255,80,80,0.85);'>rejected</span>"
        else: change_html = f"<b>{label}</b>  <span style='color:rgba(255,180,40,0.85);'>rolled back</span>"

        change_label = QLabel(change_html)
        change_label.setObjectName("ProposalMeta")
        change_label.setTextFormat(Qt.RichText)
        layout.addWidget(change_label, 1)

        # Timestamp
        ts = entry.get("timestamp", "")
        ts_str = ts.strftime("%m/%d  %H:%M") if hasattr(ts, "strftime") else str(ts)[:16]
        ts_label = QLabel(ts_str)
        ts_label.setObjectName("TimelineTime")
        ts_label.setFixedWidth(72)
        ts_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(ts_label)

        # Rollback button
        if not rolled and not rejected:
            entry_id = entry.get("_id", "")
            rb_btn = QPushButton("↩ Rollback")
            rb_btn.setObjectName("RollbackBtn")
            rb_btn.setFixedWidth(86)
            rb_btn.clicked.connect(lambda: self.rollback_requested.emit(entry_id))
            layout.addWidget(rb_btn)

#  Active Modification Widget
class ActiveModWidget(QWidget):
    def __init__(self, entry: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("LedgerEntry")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)

        dot = QLabel("◉")
        dot.setFixedWidth(16)
        dot.setAlignment(Qt.AlignCenter)
        dot.setStyleSheet("color: rgba(80,200,120,0.9); background: transparent; font-size: 9pt;")
        layout.addWidget(dot)

        key   = entry.get("param_label", entry.get("param_key", "?"))
        value = entry.get("new_value", "?")
        label = QLabel(
            f"<b>{key}</b>  "
            f"<code style='color:rgba(80,200,120,0.9);'>{value}</code>"
        )
        label.setObjectName("ProposalText")
        label.setTextFormat(Qt.RichText)
        layout.addWidget(label, 1)

        badge = ConfidenceBadge(entry.get("confidence", 0.0))
        layout.addWidget(badge)

#  Self-Mod Page
class SelfModPage(QWidget):
    approved = pyqtSignal(str)
    rejected = pyqtSignal(str)
    rollback = pyqtSignal(str)
    analyze  = pyqtSignal()
    file_uploaded = pyqtSignal(str)  # file content

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SelfModPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        accent = QFrame()
        accent.setFixedHeight(3)
        accent.setStyleSheet("background: rgba(160,80,255,0.7); border: none;")
        layout.addWidget(accent)

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(20, 20, 20, 16)
        inner_layout.setSpacing(12)
        layout.addWidget(inner, 1)

        # Header
        header_row = QHBoxLayout()

        header = QLabel("Self-Modification")
        header.setObjectName("SectionHeader")
        header_row.addWidget(header)
        header_row.addStretch()

        upload_btn = QPushButton("◇  Upload Conversation")
        upload_btn.setObjectName("AnalyzeBtn")
        upload_btn.clicked.connect(self._on_upload_file)
        header_row.addWidget(upload_btn)

        analyze_btn = QPushButton("◈  Analyze Now")
        analyze_btn.setObjectName("AnalyzeBtn")
        analyze_btn.clicked.connect(self.analyze.emit)
        header_row.addWidget(analyze_btn)

        inner_layout.addLayout(header_row)
        # Description
        desc = QLabel(
            "ARIA monitors your interaction patterns and proposes targeted "
            "configuration changes. All changes require explicit approval and "
            "can be rolled back at any time."
        )
        desc.setObjectName("ProposalMeta")
        desc.setWordWrap(True)
        inner_layout.addWidget(desc)

        sep = Separator()
        inner_layout.addWidget(sep)
        # Tabs
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        self._proposals_tab = self._make_scroll_tab()
        self._active_tab    = self._make_scroll_tab()
        self._ledger_tab    = self._make_scroll_tab()

        self._proposals_layout = self._proposals_tab[1]
        self._active_layout    = self._active_tab[1]
        self._ledger_layout    = self._ledger_tab[1]

        self._tabs.addTab(self._proposals_tab[0], "Proposals  (0)")
        self._tabs.addTab(self._active_tab[0],    "Active  (0)")
        self._tabs.addTab(self._ledger_tab[0],    "Ledger")

        inner_layout.addWidget(self._tabs, 1)
        self._pending_count = 0
    # Tab factory
    def _make_scroll_tab(self):
        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(0, 10, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        container = QWidget()
        content_layout = QVBoxLayout(container)
        content_layout.setContentsMargins(4, 4, 4, 4)
        content_layout.setSpacing(6)
        content_layout.addStretch()

        scroll.setWidget(container)
        outer.addWidget(scroll)
        return tab, content_layout
    # Public API
    def load_proposals(self, proposals: list):
        self._clear_layout(self._proposals_layout)
        self._pending_count = len(proposals)

        if not proposals: self._proposals_layout.insertWidget(
                self._proposals_layout.count() - 1,
                self._empty_label("No pending proposals. Click 'Analyze Now' to scan for patterns.")
            )
        else:
            for p in proposals:
                card = ProposalCard(p)
                card.approved.connect(self._on_approve)
                card.rejected.connect(self._on_reject)
                self._proposals_layout.insertWidget(self._proposals_layout.count() - 1, card)
        self._tabs.setTabText(0, f"Proposals  ({self._pending_count})")

    def load_active_mods(self, mods: list):
        self._clear_layout(self._active_layout)

        if not mods: self._active_layout.insertWidget(
                self._active_layout.count() - 1,
                self._empty_label("No active modifications — all settings are at defaults.")
            )
        else:
            for m in mods: self._active_layout.insertWidget(
                    self._active_layout.count() - 1, ActiveModWidget(m)
                )
        self._tabs.setTabText(1, f"Active  ({len(mods)})")

    def load_ledger(self, entries: list):
        self._clear_layout(self._ledger_layout)
        if not entries: self._ledger_layout.insertWidget(
                self._ledger_layout.count() - 1,
                self._empty_label("No modification history yet.")
            )
        else:
            for e in entries:
                widget = LedgerEntryWidget(e)
                widget.rollback_requested.connect(self._on_rollback)
                self._ledger_layout.insertWidget(self._ledger_layout.count() - 1, widget)

    def add_proposal(self, proposals: list):
        self.load_proposals(proposals)
        self._tabs.setCurrentIndex(0)

    def remove_proposal_card(self, proposal_id: str):
        layout = self._proposals_layout
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                card = item.widget()
                if isinstance(card, ProposalCard) and card._id == proposal_id:
                    card.setParent(None)
                    card.deleteLater()
                    break

        self._pending_count = max(0, self._pending_count - 1)
        self._tabs.setTabText(0, f"Proposals  ({self._pending_count})")

        if self._pending_count == 0: self._proposals_layout.insertWidget(
                self._proposals_layout.count() - 1,
                self._empty_label(
                    "All proposals decided. Click 'Analyze Now' to find more patterns."
                )
            )
    # Signal handlers
    def _on_approve(self, proposal_id: str):
        self.remove_proposal_card(proposal_id)
        self.approved.emit(proposal_id)

    def _on_reject(self, proposal_id: str):
        self.remove_proposal_card(proposal_id)
        self.rejected.emit(proposal_id)

    def _on_rollback(self, entry_id: str): self.rollback.emit(entry_id)
    # Helpers
    def _clear_layout(self, layout):
        while layout.count() > 1:
            item = layout.takeAt(0)
            w = item.widget() if item else None
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def _empty_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("ProposalMeta")
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        label.setContentsMargins(24, 48, 24, 48)
        return label

    def _on_upload_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Upload Conversation File",
            "",
            "Text Files (*.txt *.md);;All Files (*)"
        )
        if not file_path: return
        try:
            with open(file_path, "r", encoding="utf-8") as f: content = f.read()
            if content.strip(): self.file_uploaded.emit(content)
        except Exception as e: print(f"[SelfModPage] Failed to read file: {e}")
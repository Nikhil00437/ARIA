from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QPushButton, QTabWidget
from PyQt5.QtCore import Qt, pyqtSignal
from widgets import ConfidenceBadge, Separator

class ProposalCard(QWidget):
    approved = pyqtSignal(str)   # proposal_id
    rejected = pyqtSignal(str)

    def __init__(self, proposal: dict, parent=None):
        super().__init__(parent)
        self._id = proposal["id"]
        self.setObjectName("ProposalCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        # Header row
        header = QHBoxLayout()
        title = QLabel(f"📝  {proposal.get('param_label', proposal['param_key'])}")
        title.setObjectName("ProposalTitle")
        badge = ConfidenceBadge(proposal.get("confidence", 0.0))
        source_tag = QLabel(f"[{proposal.get('source', '?')}]")
        source_tag.setObjectName("ProposalMeta")

        header.addWidget(title)
        header.addStretch()
        header.addWidget(badge)
        header.addWidget(source_tag)
        layout.addLayout(header)
        # Proposal text
        text = QLabel(proposal.get("proposal_text", ""))
        text.setObjectName("ProposalText")
        text.setWordWrap(True)
        layout.addWidget(text)
        # Proposed value
        val_label = QLabel(f"New value: <b>{proposal.get('param_value')}</b>")
        val_label.setObjectName("ProposalMeta")
        val_label.setTextFormat(Qt.RichText)
        layout.addWidget(val_label)
        # Param description
        desc = QLabel(proposal.get("param_desc", ""))
        desc.setObjectName("ProposalMeta")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        sep = Separator()
        layout.addWidget(sep)
        # Action buttons
        btn_row = QHBoxLayout()
        approve_btn = QPushButton("✅  Approve")
        approve_btn.setObjectName("ApproveBtn")
        approve_btn.clicked.connect(lambda: self.approved.emit(self._id))

        reject_btn = QPushButton("✕  Reject")
        reject_btn.setObjectName("RejectBtn")
        reject_btn.clicked.connect(lambda: self.rejected.emit(self._id))

        btn_row.addWidget(approve_btn)
        btn_row.addWidget(reject_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

class LedgerEntryWidget(QWidget):
    rollback_requested = pyqtSignal(str)   # entry _id

    def __init__(self, entry: dict, parent=None):
        super().__init__(parent)
        rolled = entry.get("rolled_back", False)
        rejected = entry.get("rejected", False)
        self.setObjectName("LedgerEntryRolledBack" if rolled else "LedgerEntry")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)
        # Status icon
        if rolled: icon = "↩️"
        elif rejected: icon = "✕"
        else: icon = "✅"

        icon_label = QLabel(icon)
        icon_label.setFixedWidth(24)
        layout.addWidget(icon_label)
        # Param + value
        label = entry.get("param_label", entry.get("param_key", "?"))
        if not rejected and not rolled: change_text = f"<b>{label}</b>  →  <code>{entry.get('new_value')}</code>  (was: <code>{entry.get('old_value')}</code>)"
        elif rejected: change_text = f"<b>{label}</b>  — rejected"
        else: change_text = f"<b>{label}</b>  — rolled back"
        
        change_label = QLabel(change_text)
        change_label.setObjectName("ProposalMeta")
        change_label.setTextFormat(Qt.RichText)
        layout.addWidget(change_label, 1)
        # Timestamp
        ts = entry.get("timestamp", "")
        if hasattr(ts, "strftime"): ts_str = ts.strftime("%m/%d %H:%M")
        else: ts_str = str(ts)[:16]
        ts_label = QLabel(ts_str)
        ts_label.setObjectName("TimelineTime")
        layout.addWidget(ts_label)
        # Rollback button (only for active approved entries)
        if not rolled and not rejected:
            rb_btn = QPushButton("↩ Rollback")
            rb_btn.setObjectName("RollbackBtn")
            rb_btn.setFixedWidth(90)
            entry_id = entry.get("_id", "")
            rb_btn.clicked.connect(lambda: self.rollback_requested.emit(entry_id))
            layout.addWidget(rb_btn)

class ActiveModWidget(QWidget):
    def __init__(self, entry: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("LedgerEntry")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)

        label = QLabel(f"🔧  <b>{entry.get('param_label', entry.get('param_key'))}</b>  =  <code>{entry.get('new_value')}</code>")
        label.setObjectName("ProposalText")
        label.setTextFormat(Qt.RichText)
        layout.addWidget(label, 1)

        conf = entry.get("confidence", 0.0)
        badge = ConfidenceBadge(conf)
        layout.addWidget(badge)

class SelfModPage(QWidget):
    approved  = pyqtSignal(str)   # proposal_id
    rejected  = pyqtSignal(str)
    rollback  = pyqtSignal(str)   # ledger entry _id
    analyze   = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        # Header
        header_row = QHBoxLayout()
        header = QLabel("🧬  Self-Modification System")
        header.setObjectName("SectionHeader")
        header_row.addWidget(header)
        header_row.addStretch()

        analyze_btn = QPushButton("🔍  Analyze Now")
        analyze_btn.setObjectName("AnalyzeBtn")
        analyze_btn.clicked.connect(self.analyze.emit)
        header_row.addWidget(analyze_btn)
        layout.addLayout(header_row)
        # Description
        desc = QLabel(
            "ARIA monitors your interaction patterns and proposes targeted configuration changes. "
            "All changes require your explicit approval and can be rolled back at any time."
        )
        desc.setObjectName("ProposalMeta")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        sep = Separator()
        layout.addWidget(sep)
        # Tabs
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        self._proposals_tab  = self._make_scroll_tab()
        self._active_tab     = self._make_scroll_tab()
        self._ledger_tab     = self._make_scroll_tab()

        self._proposals_layout = self._proposals_tab[1]
        self._active_layout    = self._active_tab[1]
        self._ledger_layout    = self._ledger_tab[1]

        self._tabs.addTab(self._proposals_tab[0], "📥  Proposals (0)")
        self._tabs.addTab(self._active_tab[0],    "✅  Active (0)")
        self._tabs.addTab(self._ledger_tab[0],    "📜  Ledger")

        layout.addWidget(self._tabs, 1)

        self._pending_count = 0
    # Tab factory
    def _make_scroll_tab(self):
        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(0, 8, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

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
        self._tabs.setTabText(0, f"📥  Proposals ({self._pending_count})")

    def load_active_mods(self, mods: list):
        self._clear_layout(self._active_layout)

        if not mods: self._active_layout.insertWidget(
                self._active_layout.count() - 1,
                self._empty_label("No active modifications — all settings are at defaults.")
            )
        else:
            for m in mods:
                widget = ActiveModWidget(m)
                self._active_layout.insertWidget(self._active_layout.count() - 1, widget)
        self._tabs.setTabText(1, f"✅  Active ({len(mods)})")

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
        # Reload fully for simplicity (proposals lists are small)
        self.load_proposals(proposals)
        # Switch to proposals tab to draw attention
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
        self._tabs.setTabText(0, f"📥  Proposals ({self._pending_count})")

        if self._pending_count == 0:
            self._proposals_layout.insertWidget(
                self._proposals_layout.count() - 1,
                self._empty_label("All proposals decided. Click 'Analyze Now' to find more patterns.")
            )
    # Signal handlers
    def _on_approve(self, proposal_id: str):
        self.remove_proposal_card(proposal_id)
        self.approved.emit(proposal_id)

    def _on_reject(self, proposal_id: str):
        self.remove_proposal_card(proposal_id)
        self.rejected.emit(proposal_id)

    def _on_rollback(self, entry_id: str):
        self.rollback.emit(entry_id)
    # Helpers
    def _clear_layout(self, layout):
        while layout.count() > 1:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
                item.widget().deleteLater()

    def _empty_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("ProposalMeta")
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        label.setContentsMargins(20, 40, 20, 40)
        return label
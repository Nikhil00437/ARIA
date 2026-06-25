"""BrainWidget — small card on the chat surface surfacing ARIA's brain.

Shows:
    * Current pending-proposal count + "Analyze now" button
    * Last-analysis time (or onboarding hint if no analyses yet)
    * Active-preview banner when a sandbox preview is in flight

Hidden entirely when there's nothing to share and no onboarding flag is set.
"""

from __future__ import annotations

from typing import Optional

from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)
from PyQt5.QtCore import Qt, pyqtSignal


class BrainWidget(QFrame):
    """Compact brain summary card. Click anywhere to navigate to Self-Mod."""

    analyze_requested   = pyqtSignal()
    review_requested    = pyqtSignal()    # navigate to Self-Mod Proposals tab
    cancel_preview_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("BrainWidget")
        self.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header
        header = QHBoxLayout()
        header.setSpacing(6)
        icon = QLabel("\u2731")     # six-pointed star (subtle AI hint)
        icon.setStyleSheet(
            "color: #8B8CF7; font-size: 11pt; background: transparent;"
        )
        title = QLabel("ARIA Brain")
        title.setStyleSheet(
            "color: #E6E8EE; font-size: 8.5pt; font-weight: 700;"
            "letter-spacing: 0.5px; background: transparent;"
        )
        self._badge = QLabel("")
        self._badge.setStyleSheet(
            "color: #F59E0B; font-size: 8pt; font-weight: 700; background: transparent;"
        )
        header.addWidget(icon)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self._badge)
        layout.addLayout(header)

        # Body: dynamically updates based on state
        self._body = QLabel("")
        self._body.setStyleSheet(
            "color: #9CA3AF; font-size: 8pt; background: transparent;"
        )
        self._body.setWordWrap(True)
        layout.addWidget(self._body)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self._analyze_btn = QPushButton("Analyze now")
        self._analyze_btn.setObjectName("AnalyzeBtn")
        self._analyze_btn.clicked.connect(self.analyze_requested.emit)
        self._review_btn = QPushButton("Review proposals")
        self._review_btn.setObjectName("ApproveBtn")
        self._review_btn.clicked.connect(self.review_requested.emit)
        self._review_btn.setVisible(False)

        self._cancel_preview_btn = QPushButton("Stop preview")
        self._cancel_preview_btn.setObjectName("RejectBtn")
        self._cancel_preview_btn.clicked.connect(self.cancel_preview_requested.emit)
        self._cancel_preview_btn.setVisible(False)

        btn_row.addWidget(self._analyze_btn)
        btn_row.addWidget(self._review_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._cancel_preview_btn)
        layout.addLayout(btn_row)

    # Public API

    def show_empty(self, last_analysis_ts: Optional[str] = None,
                    onboarding: bool = False) -> None:
        """Show the onboarding hint or a 'last analysis 5 min ago' line."""
        if onboarding:
            self._body.setText(
                "I learn from how you use me. Have a few natural "
                "conversations, then click Analyze now — I'll notice patterns "
                "and suggest tweaks."
            )
        else:
            self._body.setText(
                f"Last analysis: {last_analysis_ts or 'never'}  "
                "No pending suggestions."
            )
        self._badge.setText("")
        self._review_btn.setVisible(False)
        self._cancel_preview_btn.setVisible(False)
        self.setVisible(True)

    def show_pending(self, count: int, last_analysis_ts: Optional[str] = None) -> None:
        """Show N pending proposals + nudge to review."""
        if count <= 0:
            return
        self._body.setText(
            f"{count} pending suggestion{'s' if count != 1 else ''} ready for review"
            + (f" \u00b7  last analysis: {last_analysis_ts}" if last_analysis_ts else "")
        )
        self._badge.setText(f"+{count}" if count > 1 else "+1")
        self._review_btn.setText(f"Review {count}" if count > 1 else "Review")
        self._review_btn.setVisible(True)
        self._cancel_preview_btn.setVisible(False)
        self.setVisible(True)

    def show_preview(self, summary: str) -> None:
        """Show an active-preview banner with a 'Stop preview' button."""
        self._body.setText(summary)
        self._badge.setText("preview")
        self._review_btn.setVisible(False)
        self._cancel_preview_btn.setVisible(True)
        self.setVisible(True)

    def hide_card(self) -> None:
        self.setVisible(False)
"""Agent Task page for ARIA.

Four tabs, modeled on ``selfmod_page.SelfModPage``:
    * Active    \u2014 running/queued/finished tasks (cancel from here)
    * Plan      \u2014 the currently proposed plan awaiting approval
    * Steps     \u2014 live stream of StepCards for the selected task
    * Output    \u2014 final summary + the assistant's terminal answer

The page is a passive view: it owns no engine state, just signals wired up by
``main_window._load_agent_page``. All interaction goes through Qt signals that
``main_window`` translates into ``AgentRunner`` / ``ChatEngine`` calls.

Each tab maintains its own internal layout buffer so switching between tabs
does not lose state. A generation counter (same trick as ``patterns_page``)
cancels stale step streams when the user switches tasks.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtCore import Qt, pyqtSignal

from agent_widgets import ApprovalCard, PlanCard, StepCard, TaskRow
from widgets import Separator


def _short(s: str, limit: int = 200) -> str:
    s = (s or "").strip()
    return s if len(s) <= limit else s[: limit - 3] + "..."


def _pretty(value: Any, limit: int = 300) -> str:
    import json
    try:
        s = json.dumps(value, ensure_ascii=False, default=str, indent=2)
    except (TypeError, ValueError):
        s = str(value)
    return s if len(s) <= limit else s[: limit - 3] + "..."


class AgentTaskPage(QWidget):
    """The Agent page, with Active / Plan / Steps / Output tabs."""

    # Outbound signals (wired in main_window._load_agent_page)
    start_task         = pyqtSignal(str)                # goal text
    cancel_task        = pyqtSignal(str)                # task_id
    task_selected      = pyqtSignal(str)                # task_id (renamed from select_task to avoid clash with QWidget.selectAll-style methods)
    approve_plan       = pyqtSignal(str)                # task_id
    reject_plan        = pyqtSignal(str)                # task_id
    approve_action     = pyqtSignal(str, str)           # approval_id, task_id
    reject_action      = pyqtSignal(str, str)           # approval_id, task_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AgentTaskPage")

        self._gen = 0
        self._selected_task_id: Optional[str] = None
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._steps: Dict[str, List[Dict[str, Any]]] = {}
        self._approvals: Dict[str, Dict[str, Any]] = {}  # approval_id -> action
        self._plan_by_task: Dict[str, str] = {}
        self._summary_by_task: Dict[str, str] = {}
        self._status_by_task: Dict[str, str] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        accent = QLabel()
        accent.setFixedHeight(1)
        accent.setStyleSheet("background: #1c1f26; border: none;")
        layout.addWidget(accent)

        # Header
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(16, 16, 16, 12)
        inner_layout.setSpacing(10)
        layout.addWidget(inner, 1)

        header_row = QHBoxLayout()
        title = QLabel("Agent")
        title.setObjectName("SectionHeader")
        sub = QLabel("plan \u2192 act \u2192 observe coding agent")
        sub.setObjectName("ProposalMeta")
        header_row.addWidget(title)
        header_row.addSpacing(8)
        header_row.addWidget(sub)
        header_row.addStretch()
        inner_layout.addLayout(header_row)

        # New-task input
        new_row = QHBoxLayout()
        new_row.setSpacing(8)
        self._goal_input = QLineEdit()
        self._goal_input.setPlaceholderText("e.g. find every TODO comment in this repo and list them")
        self._goal_input.returnPressed.connect(self._on_start)
        new_btn = QPushButton("\u25b6  Start")
        new_btn.setObjectName("ApproveBtn")
        new_btn.clicked.connect(self._on_start)
        new_row.addWidget(self._goal_input, 1)
        new_row.addWidget(new_btn)
        inner_layout.addLayout(new_row)

        inner_layout.addWidget(Separator())

        # Tabs
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        self._active_tab,  self._active_layout  = self._make_scroll_tab()
        self._plan_tab,    self._plan_layout    = self._make_scroll_tab()
        self._steps_tab,   self._steps_layout   = self._make_scroll_tab()
        self._output_tab,  self._output_layout  = self._make_scroll_tab()
        self._ledger_tab,  self._ledger_layout  = self._make_scroll_tab()

        self._tabs.addTab(self._active_tab,  "Active  (0)")
        self._tabs.addTab(self._plan_tab,    "Plan")
        self._tabs.addTab(self._steps_tab,   "Steps")
        self._tabs.addTab(self._output_tab,  "Output")
        self._tabs.addTab(self._ledger_tab,  "Ledger")
        inner_layout.addWidget(self._tabs, 1)

    # ── Public API (called by main_window slots) ────────────────────────────

    def add_or_update_task(self, task: Dict[str, Any]) -> None:
        """Insert or update a task row in the Active tab (direct caller API)."""
        self._tasks[task["task_id"]] = task
        self._status_by_task[task["task_id"]] = task.get("status", "running")
        self._rebuild_active_tab()

    def on_task_started(self, task_id: str, goal: str) -> None:
        """Slot for the cross-thread ``agent_task_started`` signal.

        The ``AgentRunner`` emits ``(task_id, goal)``; this method turns the
        pair into a task dict and routes it through ``add_or_update_task``.
        Kept separate so the signal connection (which requires the slot's
        signature to match the signal) is unambiguous.
        """
        self.add_or_update_task({
            "task_id": task_id,
            "goal": goal,
            "status": "running",
            "mode": "plan_apply",
            "steps": [],
        })

    def set_plan(self, task_id: str, plan_text: str) -> None:
        """Show a PlanCard for a task awaiting plan approval."""
        self._plan_by_task[task_id] = plan_text
        self._gen += 1
        my_gen = self._gen

        self._clear_layout(self._plan_layout)
        self._plan_layout.insertWidget(
            self._plan_layout.count() - 1,
            self._empty_label("No plan awaiting approval."),
        )
        if not plan_text:
            return

        card = PlanCard(task_id, plan_text)
        card.approved.connect(self.approve_plan.emit)
        card.rejected.connect(self.reject_plan.emit)
        self._plan_layout.insertWidget(self._plan_layout.count() - 1, card)
        self._tabs.setTabText(1, "Plan  (\u00b7)")

    def clear_plan(self) -> None:
        self._clear_layout(self._plan_layout)
        self._plan_layout.insertWidget(
            self._plan_layout.count() - 1,
            self._empty_label("No plan awaiting approval."),
        )
        self._tabs.setTabText(1, "Plan")

    def add_approval(self, approval_id: str, action: Dict[str, Any]) -> None:
        """Insert an ApprovalCard for a per-action approval during a run."""
        self._approvals[approval_id] = action
        card = ApprovalCard(approval_id, action)
        task_id = action.get("task_id", "")
        card.approved.connect(
            lambda aid=approval_id, tid=task_id: self.approve_action.emit(aid, tid)
        )
        card.rejected.connect(
            lambda aid=approval_id, tid=task_id: self.reject_action.emit(aid, tid)
        )
        # In-page approvals appear in the Steps tab for context.
        self._steps_layout.insertWidget(self._steps_layout.count() - 1, card)

    def add_step(self, task_id: str, step: Dict[str, Any]) -> None:
        """Append a step to the Steps tab (if this is the selected task)."""
        self._steps.setdefault(task_id, []).append(step)
        if task_id != self._selected_task_id:
            return
        card = StepCard(step)
        self._steps_layout.insertWidget(self._steps_layout.count() - 1, card)

    def select_task(self, task_id: str) -> None:
        """Switch the Steps + Output tabs to render a specific task."""
        self._gen += 1
        self._selected_task_id = task_id

        # Rebuild steps for this task
        self._clear_layout(self._steps_layout)
        steps = self._steps.get(task_id, [])
        if not steps:
            self._steps_layout.insertWidget(
                self._steps_layout.count() - 1,
                self._empty_label("No steps yet for this task."),
            )
        else:
            for s in steps:
                self._steps_layout.insertWidget(
                    self._steps_layout.count() - 1, StepCard(s)
                )

        # Rebuild output
        self._clear_layout(self._output_layout)
        summary = self._summary_by_task.get(task_id, "")
        task = self._tasks.get(task_id, {})
        status = task.get("status", "running")
        out = QVBoxLayout()
        out.setContentsMargins(12, 12, 12, 12)
        out.setSpacing(8)
        meta = QLabel(
            f"status: {status}  \u00b7  mode: {task.get('mode','plan_apply')}  "
            f"\u00b7  steps: {len(steps)}  \u00b7  task: {task_id[:8]}"
        )
        meta.setStyleSheet("color: #7a96b0; font-size: 8.5pt;")
        out.addWidget(meta)
        body = QTextEdit()
        body.setReadOnly(True)
        body.setStyleSheet(
            "QTextEdit {"
            "  background: #0a0d14; color: #dce6f4;"
            "  border: 1px solid #15181f; font-family: 'Cascadia Code', 'Consolas', monospace;"
            "  font-size: 9pt; padding: 10px;"
            "}"
        )
        body.setPlainText(summary or "(task still running or no summary yet)")
        out.addWidget(body, 1)
        container = QWidget()
        container.setLayout(out)
        self._output_layout.insertWidget(self._output_layout.count() - 1, container)

        # Rebuild ledger (Phase 6): audit log of EXECUTED MUTATIONS only.
        # We pair each "action" step with its "observation" by sequence
        # proximity, then keep only the pairs where the action is a
        # mutating tool (write_file / edit_file / delete_file) AND the
        # observation reports ``executed=True``. The StepCard already
        # renders the request args and the result, so the merged dict
        # gives the user a full audit row.
        self._clear_layout(self._ledger_layout)
        steps = self._steps.get(task_id, [])
        MUTATING_TOOLS = {"write_file", "edit_file", "delete_file"}
        executed_mutations = []
        last_action = None
        for s in steps:
            if s.get("type") == "action":
                last_action = s
            elif s.get("type") == "observation" and last_action is not None:
                tool = last_action.get("tool_name", "")
                if tool in MUTATING_TOOLS and s.get("executed") is True:
                    merged = dict(last_action)
                    merged["tool_result"] = s.get("tool_result")
                    merged["executed"] = True
                    executed_mutations.append(merged)
                last_action = None
        if not executed_mutations:
            self._ledger_layout.insertWidget(
                self._ledger_layout.count() - 1,
                self._empty_label("No executed mutations yet."),
            )
        else:
            for s in executed_mutations:
                self._ledger_layout.insertWidget(
                    self._ledger_layout.count() - 1, StepCard(s)
                )

    def set_summary(self, task_id: str, summary: str) -> None:
        """Update the Output tab summary for a task (called on done)."""
        self._summary_by_task[task_id] = summary
        if self._selected_task_id == task_id:
            self.select_task(task_id)

    def set_status(self, task_id: str, status: str) -> None:
        self._status_by_task[task_id] = status
        task = self._tasks.get(task_id, {})
        task["status"] = status
        self._rebuild_active_tab()

    # ── Internal: tabs / layout helpers ─────────────────────────────────────

    def _make_scroll_tab(self):
        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(0, 4, 0, 0)
        outer.setSpacing(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll)
        return tab, layout

    def _clear_layout(self, layout) -> None:
        while layout.count() > 1:  # keep the trailing stretch
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def _rebuild_active_tab(self) -> None:
        self._clear_layout(self._active_layout)
        if not self._tasks:
            self._active_layout.insertWidget(
                self._active_layout.count() - 1,
                self._empty_label("No agent tasks yet. Start one above."),
            )
            self._tabs.setTabText(0, "Active  (0)")
            return
        # Sort: running/queued first, then by created desc
        order = {"running": 0, "queued": 1, "done": 2, "failed": 3, "cancelled": 4}
        ordered = sorted(
            self._tasks.values(),
            key=lambda t: (order.get(t.get("status", ""), 9), t.get("created", 0)),
        )
        for task in ordered:
            row = TaskRow(task)
            row.cancel_requested.connect(self.cancel_task.emit)
            self._active_layout.insertWidget(
                self._active_layout.count() - 1, row
            )
        # Update tab count
        running = sum(1 for t in self._tasks.values() if t.get("status") in ("running", "queued"))
        self._tabs.setTabText(0, f"Active  ({running} active, {len(self._tasks)} total)")

    def _empty_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("ProposalMeta")
        lbl.setStyleSheet("color: #4a5566; font-style: italic; padding: 12px;")
        lbl.setAlignment(Qt.AlignCenter)
        return lbl

    # ── New-task submission ──────────────────────────────────────────────────

    def _on_start(self) -> None:
        text = self._goal_input.text().strip()
        if not text:
            return
        self._goal_input.clear()
        self.start_task.emit(text)

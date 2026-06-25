"""Reusable widgets for the agent harness UI.

Each card is themable via the global stylesheet (see ``styles.py``). Color
per step-kind is driven by a dynamic ``kind`` property on ``StepCard`` and a
matching ``[kind=...]`` attribute selector in the QSS. The other cards
(``PlanCard``, ``ApprovalCard``, ``TaskRow``) have fixed object names — their
accent colors come from theme tokens (``kind_plan`` / ``warning`` / ``accent``).
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict

from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)
from PyQt5.QtCore import Qt, pyqtSignal

from widgets import Separator


# Shared label/icon maps. Colors come from the theme via the stylesheet;
# these dicts only hold non-color metadata.

_KIND_LABELS = {
    "thought":     "thought",
    "plan":        "plan",
    "action":      "action",
    "observation": "observation",
}

_KIND_ICONS = {
    "thought":     "\u00b7",
    "plan":        "\u25cb",
    "action":      "\u203a",
    "observation": "\u25cc",
}


def _now_ts() -> str:
    return time.strftime("%H:%M:%S")


def _short_text(s: str, limit: int = 200) -> str:
    s = (s or "").strip()
    return s if len(s) <= limit else s[: limit - 3] + "..."


def _pretty(value: Any, limit: int = 300) -> str:
    try:
        s = json.dumps(value, ensure_ascii=False, default=str, indent=2)
    except (TypeError, ValueError):
        s = str(value)
    return s if len(s) <= limit else s[: limit - 3] + "..."


# ── StepCard ───────────────────────────────────────────────────────────────

class StepCard(QFrame):
    """A single step in the plan→act→observe loop."""

    def __init__(self, step: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.setObjectName("StepCard")
        step_type = step.get("type", "thought")
        self.setProperty("kind", step_type)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 10)
        layout.setSpacing(4)

        # Header
        header = QHBoxLayout()
        header.setSpacing(8)
        ts = QLabel(_now_ts())
        ts.setObjectName("StepTime")

        type_lbl = QLabel(
            f"{_KIND_ICONS.get(step_type, '\u00b7')}  {_KIND_LABELS.get(step_type, step_type)}"
        )
        type_lbl.setObjectName("StepKind")
        type_lbl.setProperty("kind", step_type)

        header.addWidget(ts)
        header.addWidget(type_lbl)
        if step.get("tool_name"):
            tn = QLabel(step["tool_name"])
            tn.setObjectName("StepToolName")
            header.addWidget(tn)
        header.addStretch()
        if step_type == "observation" and "executed" in step:
            exec_lbl = QLabel("\u2713 ran" if step.get("executed") else "\u2717 refused")
            exec_lbl.setObjectName("StepExecutedOk" if step.get("executed") else "StepExecutedNo")
            header.addWidget(exec_lbl)
        layout.addLayout(header)

        # Body
        if step.get("content"):
            content = QLabel(_short_text(step["content"], 400))
            content.setObjectName("StepContent")
            content.setWordWrap(True)
            layout.addWidget(content)

        if step.get("tool_args"):
            args_lbl = QLabel("args: " + _pretty(step["tool_args"], 240))
            args_lbl.setObjectName("StepArgs")
            args_lbl.setWordWrap(True)
            layout.addWidget(args_lbl)

        if step.get("tool_result") is not None:
            res_text = _pretty(step["tool_result"], 240)
            res_lbl = QLabel("\u2192 " + res_text)
            res_lbl.setObjectName("StepResult")
            res_lbl.setWordWrap(True)
            layout.addWidget(res_lbl)


# ── PlanCard ───────────────────────────────────────────────────────────────

class PlanCard(QFrame):
    """A proposed agent plan with Approve / Reject buttons."""

    approved = pyqtSignal(str)
    rejected = pyqtSignal(str)

    def __init__(self, task_id: str, plan_text: str, parent=None):
        super().__init__(parent)
        self._task_id = task_id
        self.setObjectName("PlanCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("Proposed plan")
        title.setObjectName("PlanTitle")
        sub = QLabel("review before the agent begins executing")
        sub.setStyleSheet("color: #9CA3AF; font-size: 8pt; background: transparent;")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(sub)
        layout.addLayout(header)

        body = QLabel(plan_text or "(empty plan)")
        body.setObjectName("PlanBody")
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(body)

        layout.addWidget(Separator())

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        approve_btn = QPushButton("Approve and execute")
        approve_btn.setObjectName("ApproveBtn")
        approve_btn.clicked.connect(lambda: self.approved.emit(self._task_id))
        reject_btn = QPushButton("Reject")
        reject_btn.setObjectName("RejectBtn")
        reject_btn.clicked.connect(lambda: self.rejected.emit(self._task_id))
        btn_row.addWidget(approve_btn)
        btn_row.addWidget(reject_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)


# ── ApprovalCard ───────────────────────────────────────────────────────────

class ApprovalCard(QFrame):
    """A one-shot in-feed approval request."""

    approved = pyqtSignal(str)
    rejected = pyqtSignal(str)

    def __init__(self, approval_id: str, action: Dict[str, Any], parent=None):
        super().__init__(parent)
        self._approval_id = approval_id
        self._action = action
        self.setObjectName("ApprovalCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel("Action approval required")
        title.setObjectName("ApprovalTitle")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        summary = QLabel(action.get("summary") or action.get("tool", ""))
        summary.setObjectName("ApprovalSummary")
        summary.setWordWrap(True)
        layout.addWidget(summary)

        if action.get("args"):
            args_lbl = QLabel("args: " + _pretty(action["args"], 240))
            args_lbl.setObjectName("StepArgs")
            args_lbl.setWordWrap(True)
            layout.addWidget(args_lbl)

        if action.get("risk_level"):
            risk = QLabel(f"risk: {action['risk_level']}")
            risk.setObjectName("ApprovalRisk")
            layout.addWidget(risk)

        layout.addWidget(Separator())

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        ok = QPushButton("Approve")
        ok.setObjectName("ApproveBtn")
        ok.clicked.connect(lambda: self.approved.emit(self._approval_id))
        no = QPushButton("Reject")
        no.setObjectName("RejectBtn")
        no.clicked.connect(lambda: self.rejected.emit(self._approval_id))
        btn_row.addWidget(ok)
        btn_row.addWidget(no)
        btn_row.addStretch()
        layout.addLayout(btn_row)


# ── TaskRow ────────────────────────────────────────────────────────────────

class TaskRow(QFrame):
    """One row in the Active tasks list."""

    cancel_requested = pyqtSignal(str)
    selected = pyqtSignal(str)

    def __init__(self, task: Dict[str, Any], parent=None):
        super().__init__(parent)
        self._task_id = task.get("task_id", "")
        self.setObjectName("TaskRow")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        status = task.get("status", "running")
        # Status dot color — the only inline color we keep (per-instance
        # dynamic; not worth a stylesheet selector for a one-shot label).
        status_colors = {
            "running": "#8B8CF7",
            "done":    "#10B981",
            "failed":  "#EF4444",
            "cancelled": "#525866",
        }
        color = status_colors.get(status, "#9CA3AF")

        dot = QLabel("\u25cf")
        dot.setStyleSheet(f"color: {color}; font-size: 10pt; background: transparent;")
        dot.setFixedWidth(14)
        layout.addWidget(dot)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        goal = QLabel(_short_text(task.get("goal", "(no goal)"), 120))
        goal.setObjectName("TaskRowGoal")
        goal.setWordWrap(False)
        sub = QLabel(
            f"status: {status}  \u00b7  mode: {task.get('mode','plan_apply')}  "
            f"\u00b7  steps: {len(task.get('steps', []))}"
        )
        sub.setObjectName("TaskRowMeta")
        text_col.addWidget(goal)
        text_col.addWidget(sub)
        layout.addLayout(text_col, 1)

        if status in ("running", "queued"):
            cancel_btn = QPushButton("Cancel")
            cancel_btn.setObjectName("RejectBtn")
            cancel_btn.clicked.connect(lambda: self.cancel_requested.emit(self._task_id))
            layout.addWidget(cancel_btn)
        else:
            tid = QLabel(self._task_id[:8])
            tid.setObjectName("TaskRowId")
            layout.addWidget(tid)

        self.setCursor(Qt.PointingHandCursor)
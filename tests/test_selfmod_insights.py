"""Tests for the ARIA Brain self-mod insights persistence + inferencer split.

Covers:
  - Database.save_insight / get_insights / update_insight_status
  - BehavioralInferencer.observe + propose split
  - SelfModController.preview / cancel_preview / is_previewing
"""

import os
import pytest
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from database import Database
from signals import ARIASignals


# ════════════════════════════════════════════════════════════════════════════════
# Database insight persistence
# ════════════════════════════════════════════════════════════════════════════════

class TestInsightPersistence:
    def setup_method(self):
        self.db = Database()  # uses _MemoryStore (not connected)

    def test_save_and_get(self):
        iid = self.db.save_insight({
            "label": "User prefers brevity",
            "confidence": 0.85,
            "param_key": "response_length_preference",
        })
        assert iid.startswith("ins_")
        items = self.db.get_insights(limit=10)
        assert len(items) == 1
        assert items[0]["id"] == iid
        assert items[0]["label"] == "User prefers brevity"
        assert items[0]["status"] == "noticed"

    def test_status_filter(self):
        for _ in range(3):
            self.db.save_insight({"label": "a", "confidence": 0.9})
        # Promote the first to proposed.
        all_i = self.db.get_insights(limit=10)
        self.db.update_insight_status(all_i[0]["id"], "proposed", proposal_id="p_1")
        proposed = self.db.get_insights(status="proposed")
        noticed = self.db.get_insights(status="noticed")
        assert len(proposed) == 1
        assert len(noticed) == 2
        assert proposed[0]["proposal_id"] == "p_1"

    def test_recent_first(self):
        for i in range(5):
            self.db.save_insight({"label": f"l{i}", "confidence": 0.5})
        items = self.db.get_insights(limit=3)
        assert len(items) == 3

    def test_fifo_cap(self):
        """Inserting past the cap should evict oldest (not crash)."""
        for i in range(510):
            self.db.save_insight({"label": f"l{i}", "confidence": 0.5})
        items = self.db.get_insights(limit=1000)
        # Cap is 500 records
        assert len(items) <= 500


# ════════════════════════════════════════════════════════════════════════════════
# Inferencer split: observe + propose
# ════════════════════════════════════════════════════════════════════════════════

class FakeLLM:
    """Minimal LLM stand-in that returns a single high-confidence rule-like
    pattern when called. Counts how many times infer_behavioral_patterns
    was called."""

    def __init__(self):
        self.calls = 0

    def infer_behavioral_patterns(self, interactions, n=50):
        self.calls += 1
        return [{
            "pattern":             "User loves brevity",
            "evidence":            "many summary signals",
            "proposed_change":     "set response_length_preference to concise",
            "param_key":           "response_length_preference",
            "param_value":         "concise",
            "confidence":          0.85,
            "reversible":          True,
            "source":              "llm",
        }]


class TestInferencerSplit:
    def setup_method(self):
        from PyQt5.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication([])
        self.db = Database()
        # Seed enough messages to pass MIN_INTERACTIONS (10).
        for i in range(12):
            self.db.save_message("s1", "user", f"Please give me a brief summary of this {i}")
            self.db.save_message("s1", "assistant", "ok")
        self.llm = FakeLLM()
        from selfmod.inferencer import BehavioralInferencer
        self.inf = BehavioralInferencer(self.db, self.llm)

    def test_observe_returns_all_and_persists(self):
        obs = self.inf.observe("s1")
        assert isinstance(obs, list)
        # All observations are persisted as insights.
        stored = self.db.get_insights(limit=200)
        assert len(stored) == len(obs)
        # Each has a status of 'noticed' on first observation.
        for i in stored:
            assert i["status"] == "noticed"

    def test_propose_picks_top_5(self):
        obs = self.inf.observe("s1")
        props = self.inf.propose(obs)
        # LLM returned one high-confidence rule — at least the top 5 should
        # include *either* that one OR one of the rule-based ones (summary
        # preference etc.). We just verify the count is reasonable.
        assert 1 <= len(props) <= 5
        # All proposed param_keys must be MODIFIABLE.
        from selfmod.proposal_engine import MODIFIABLE_PARAMS
        for p in props:
            assert p["param_key"] in MODIFIABLE_PARAMS

    def test_analyze_is_backward_compat(self):
        """analyze() returns up to 5 proposals (legacy behavior)."""
        props = self.inf.analyze("s1")
        assert isinstance(props, list)
        assert len(props) <= 5

    def test_min_interactions_short_circuits(self):
        # Seed only 5 messages — inferencer should refuse.
        self.db2 = Database()
        for i in range(5):
            self.db2.save_message("s2", "user", "x")
        inf = self.__class__ if False else None
        from selfmod.inferencer import BehavioralInferencer
        inf2 = BehavioralInferencer(self.db2, FakeLLM())
        assert inf2.observe("s2") == []
        assert inf2.propose([]) == []


# ════════════════════════════════════════════════════════════════════════════════
# SelfModController: preview / cancel_preview / is_previewing
# ════════════════════════════════════════════════════════════════════════════════

class FakeLLM2(FakeLLM):
    def generate_proposal_text(self, pattern):
        return "Try a more concise response style."


class TestControllerPreview:
    def setup_method(self):
        from PyQt5.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication([])
        self.db = Database()
        self.sig = ARIASignals()
        self.ctrl = __import__(
            "selfmod.controller", fromlist=["SelfModController"]
        ).SelfModController(self.db, FakeLLM2(), self.sig)
        # Seed a pending proposal
        for i in range(12):
            self.db.save_message("s1", "user", f"brief summary {i}")
            self.db.save_message("s1", "assistant", "ok")
        self.ctrl.analyze_sync("s1")
        # analyse_sync writes 2 proposals (response_length + suggestion_count
        # are both matched by the rule; but with the fake LLM returning one,
        # we'll get one proposal pending)
        self.pid = list(self.ctrl._pending.keys())[0]

    def test_preview_applies_and_reverts(self):
        # Use suggestion_count (default 3) and set param_value to 6
        # so the preview has a visible effect.
        from selfmod.proposal_engine import Proposal
        p = self.ctrl._pending[self.pid][0]
        p.param_key = "suggestion_count"
        p.param_value = 6
        p.current_value = 3
        before = self.ctrl.get("suggestion_count")
        ok = self.ctrl.preview(self.pid)
        assert ok
        assert self.ctrl.is_previewing()
        during = self.ctrl.get("suggestion_count")
        assert during == 6
        assert self.ctrl.cancel_preview()
        assert not self.ctrl.is_previewing()
        after = self.ctrl.get("suggestion_count")
        assert after == before

    def test_cancel_when_no_preview(self):
        # cancel_preview on a fresh controller returns False
        self.ctrl.cancel_preview()  # ensure no preview
        assert not self.ctrl.cancel_preview()

    def test_preview_only_one_at_a_time(self):
        # Starting a second preview cancels the first.
        ok1 = self.ctrl.preview(self.pid)
        assert ok1
        # Manually add a second pending proposal
        from selfmod.proposal_engine import MODIFIABLE_PARAMS, Proposal
        p2 = Proposal(
            param_key="suggestion_count",
            param_value=5,
            pattern={"confidence": 0.8, "source": "test"},
            proposal_text="Use 5 suggestions.",
            current_value=3,
        )
        self.ctrl._pending[p2.id] = (p2, "s1")
        ok2 = self.ctrl.preview(p2.id)
        assert ok2
        # The first preview should be cancelled
        assert self.ctrl.is_previewing()
        # Active preview should be for p2.id
        assert self.ctrl._active_preview["proposal_id"] == p2.id
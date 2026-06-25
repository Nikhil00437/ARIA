import threading, datetime, time, uuid
from typing import Optional
from selfmod.inferencer     import BehavioralInferencer
from selfmod.proposal_engine import ProposalEngine
from selfmod.sandbox        import PermissionSandbox
from constants import COL_INSIGHTS

class SelfModController:
    def __init__(self, db, llm_client, signals):
        self._db        = db
        self._llm       = llm_client
        self._signals   = signals
        # The four components
        self.inferencer = BehavioralInferencer(db, llm_client)
        self.engine     = ProposalEngine(llm_client)
        self.sandbox    = PermissionSandbox(db, signals)
        # Pending proposals awaiting user decision (proposal_id → Proposal)
        self._pending: dict = {}
        # Prevent concurrent analysis runs
        self._analyzing = False
        # Track last analysis time
        self._last_analyzed: dict = {}   # session_id → datetime
        # Preview state (Phase 9)
        self._preview_lock = threading.Lock()
        self._active_preview: dict = None  # {"proposal_id": str, "key": str, "old_value": any, "ts": float}

    # Config shortcut
    def get(self, key: str, default=None): return self.sandbox.get(key, default)

    def get_all(self) -> dict: return self.sandbox.get_all()
    # Insights feed (Phase 9)
    def get_insights(self, limit: int = 200, status: Optional[str] = None) -> list:
        return self._db.get_insights(limit=limit, status=status)

    def last_analysis(self, session_id: Optional[str] = None) -> Optional[datetime.datetime]:
        if session_id:
            return self._last_analyzed.get(session_id)
        return max(self._last_analyzed.values()) if self._last_analyzed else None

    # Analysis Trigger
    def analyze_async(self, session_id: str, min_interval_minutes: int = 10):
        if self._analyzing: return
        last = self._last_analyzed.get(session_id)
        if last:
            elapsed = (datetime.datetime.utcnow() - last).total_seconds() / 60
            if elapsed < min_interval_minutes: return

        def _run():
            self._analyzing = True
            try:
                # Phase 9 split: observe (records every pattern) then propose.
                insights = self.inferencer.observe(session_id)
                if not insights:
                    return
                proposals = self.engine.generate_proposals(insights)
                if proposals:
                    for p in proposals:
                        self._pending[p.id] = (p, session_id)
                        # Mark the source insight as "proposed" so the feed shows it.
                        for ins in insights:
                            if ins.get("param_key") == p.param_key:
                                self._db.update_insight_status(ins["id"], "proposed", proposal_id=p.id)
                # Emit signals: insights first, then proposals, then badge.
                self._signals.selfmod_insights_changed.emit(
                    self._db.get_insights(limit=200)
                )
                self._signals.selfmod_proposal.emit([p.to_dict() for p in proposals])
                self._signals.selfmod_badge_changed.emit(len(proposals))
                self._last_analyzed[session_id] = datetime.datetime.utcnow()
            except Exception as e: print(f"[SelfMod] Analysis error: {e}")
            finally: self._analyzing = False
        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def analyze_sync(self, session_id: str) -> list:
        insights = self.inferencer.observe(session_id)
        proposals = self.engine.generate_proposals(insights)
        if proposals:
            for p in proposals:
                self._pending[p.id] = (p, session_id)
                for ins in insights:
                    if ins.get("param_key") == p.param_key:
                        self._db.update_insight_status(ins["id"], "proposed", proposal_id=p.id)
        self._signals.selfmod_insights_changed.emit(self._db.get_insights(limit=200))
        self._signals.selfmod_badge_changed.emit(len(proposals))
        self._last_analyzed[session_id] = datetime.datetime.utcnow()
        return [p.to_dict() for p in proposals]

    def analyze_from_file(self, file_content: str, session_id: str = "file_upload") -> list:
        interactions = self._parse_conversation_text(file_content)
        patterns = self._rule_based_analysis(interactions) if hasattr(self, "_rule_based_analysis") else []
        llm_patterns = self._llm.infer_behavioral_patterns(interactions, n=50)
        for p in llm_patterns:
            if self.inferencer._validate_pattern(p):
                patterns.append(p)
        for p in patterns[: BehavioralInferencer.MAX_OBSERVATIONS]:
            self._db.save_insight(dict(p))
        proposals = self.engine.generate_proposals(patterns)
        for p in proposals:
            self._pending[p.id] = (p, session_id)
        self._signals.selfmod_insights_changed.emit(self._db.get_insights(limit=200))
        self._signals.selfmod_badge_changed.emit(len(proposals))
        return [p.to_dict() for p in proposals]

    # User Decision
    def approve(self, proposal_id: str) -> tuple:
        if proposal_id not in self._pending: raise KeyError(f"Proposal '{proposal_id}' not found or already decided.")
        proposal, session_id = self._pending.pop(proposal_id)
        ledger_entry = self.sandbox.approve(proposal, session_id)
        proposal.status = "approved"
        # Mark source insight approved.
        for ins in self._db.get_insights(limit=200):
            if ins.get("proposal_id") == proposal_id:
                self._db.update_insight_status(ins["id"], "approved")
        self._signals.selfmod_insights_changed.emit(self._db.get_insights(limit=200))
        self._signals.selfmod_badge_changed.emit(len(self._pending))
        return proposal.param_key, proposal.param_value, ledger_entry

    def reject(self, proposal_id: str):
        if proposal_id not in self._pending: raise KeyError(f"Proposal '{proposal_id}' not found or already decided.")
        proposal, session_id = self._pending.pop(proposal_id)
        self.sandbox.reject(proposal, session_id)
        proposal.status = "rejected"
        for ins in self._db.get_insights(limit=200):
            if ins.get("proposal_id") == proposal_id:
                self._db.update_insight_status(ins["id"], "rejected")
        self._signals.selfmod_insights_changed.emit(self._db.get_insights(limit=200))
        self._signals.selfmod_badge_changed.emit(len(self._pending))

    # Preview (Phase 9): apply proposal value temporarily, auto-revert after
    # the next chat turn OR 60s, whichever comes first. Thread-safe.
    def preview(self, proposal_id: str) -> bool:
        with self._preview_lock:
            if self._active_preview is not None:
                # One preview at a time; cancel the previous first.
                self._cancel_active_preview_internal()
            if proposal_id not in self._pending:
                return False
            proposal, _ = self._pending[proposal_id]
            key = proposal.param_key
            try:
                old_value = self.sandbox.config.get(key)
                new_value = proposal.param_value
                # Direct config apply — no ledger entry, just a transient overlay.
                self.sandbox.config._overlay[key] = new_value
            except Exception:
                return False
            self._active_preview = {
                "proposal_id": proposal_id,
                "key":         key,
                "old_value":   old_value,
                "ts":          datetime.datetime.utcnow().timestamp(),
            }
            # Schedule auto-revert.
            self._schedule_preview_revert(60)
            return True

    def cancel_preview(self) -> bool:
        with self._preview_lock:
            return self._cancel_active_preview_internal()

    def is_previewing(self) -> bool:
        return self._active_preview is not None

    def _cancel_active_preview_internal(self) -> bool:
        if self._active_preview is None:
            return False
        key = self._active_preview["key"]
        old = self._active_preview["old_value"]
        # Restore exact previous value (could be base or overlay).
        if self.sandbox.config._base.get(key) == old:
            self.sandbox.config._overlay.pop(key, None)
        else:
            self.sandbox.config._overlay[key] = old
        self._active_preview = None
        return True

    def _schedule_preview_revert(self, seconds: int) -> None:
        """Schedule an auto-revert after ``seconds`` (Phase 9)."""
        def _auto():
            time.sleep(seconds)
            self.cancel_preview()
        threading.Thread(target=_auto, daemon=True).start()
    # Rollback
    def rollback(self, entry_id: str) -> tuple: return self.sandbox.rollback(entry_id)
    # Ledger
    def get_ledger(self) -> list: return self.sandbox.get_ledger()

    def get_active_modifications(self) -> list: return self.sandbox.get_active_modifications()

    def get_pending(self) -> list: return [p.to_dict() for p, _ in self._pending.values()]

    def pending_count(self) -> int: return len(self._pending)

    def _rule_based_analysis(self, interactions):
        """Pass-through to inferencer (kept here so analyze_from_file works
        without re-importing internals)."""
        return self.inferencer._rule_based_analysis(interactions)

    def _parse_conversation_text(self, text):
        return self.inferencer._parse_conversation_text(text)
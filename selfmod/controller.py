import threading, datetime
from selfmod.inferencer     import BehavioralInferencer
from selfmod.proposal_engine import ProposalEngine
from selfmod.sandbox        import PermissionSandbox

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
    # Config shortcut
    def get(self, key: str, default=None): return self.sandbox.get(key, default)

    def get_all(self) -> dict: return self.sandbox.get_all()
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
                patterns  = self.inferencer.analyze(session_id)
                if not patterns: return
                proposals = self.engine.generate_proposals(patterns)
                if not proposals: return
                # Register in pending
                for p in proposals: self._pending[p.id] = (p, session_id)
                # Emit to UI
                self._signals.selfmod_proposal.emit([p.to_dict() for p in proposals])
                self._last_analyzed[session_id] = datetime.datetime.utcnow()
            except Exception as e: print(f"[SelfMod] Analysis error: {e}")
            finally: self._analyzing = False
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        
    def analyze_sync(self, session_id: str) -> list:
        patterns  = self.inferencer.analyze(session_id)
        if not patterns: return []
        proposals = self.engine.generate_proposals(patterns)
        for p in proposals: self._pending[p.id] = (p, session_id)
        return [p.to_dict() for p in proposals]

    def analyze_from_file(self, file_content: str, session_id: str = "file_upload") -> list:
        patterns = self.inferencer.analyze_from_text(file_content)
        if not patterns: return []
        proposals = self.engine.generate_proposals(patterns)
        for p in proposals: self._pending[p.id] = (p, session_id)
        return [p.to_dict() for p in proposals]
    # User Decision
    def approve(self, proposal_id: str) -> tuple:
        if proposal_id not in self._pending: raise KeyError(f"Proposal '{proposal_id}' not found or already decided.")
        proposal, session_id = self._pending.pop(proposal_id)
        ledger_entry = self.sandbox.approve(proposal, session_id)
        proposal.status = "approved"
        return proposal.param_key, proposal.param_value, ledger_entry

    def reject(self, proposal_id: str):
        if proposal_id not in self._pending: raise KeyError(f"Proposal '{proposal_id}' not found or already decided.")
        proposal, session_id = self._pending.pop(proposal_id)
        self.sandbox.reject(proposal, session_id)
        proposal.status = "rejected"
    # Rollback
    def rollback(self, entry_id: str) -> tuple: return self.sandbox.rollback(entry_id)
    # Ledger
    def get_ledger(self) -> list: return self.sandbox.get_ledger()

    def get_active_modifications(self) -> list: return self.sandbox.get_active_modifications()

    def get_pending(self) -> list: return [p.to_dict() for p, _ in self._pending.values()]
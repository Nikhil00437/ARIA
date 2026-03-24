import copy
from typing import Any, Optional
from constants import SELFMOD_LOCKED_PARAMS
from selfmod.proposal_engine import MODIFIABLE_PARAMS, Proposal

# Default runtime config
DEFAULT_CONFIG = {
    "output_mode":               "verbose",
    "smart_search_threshold":    0.75,
    "tts_enabled":               True,
    "silent_mode":               False,
    "default_theme":             "cyber",
    "suggestion_count":          3,
    "custom_shortcuts":          {},
    "preferred_search_sites":    [],
    "confirmation_verbosity":    "full",
    "response_length_preference":"concise",
}

class SandboxConfig:
    def __init__(self):
        self._base    = copy.deepcopy(DEFAULT_CONFIG)
        self._overlay: dict = {}   # Active approved modifications
        
    def get(self, key: str, default=None): return self._overlay.get(key, self._base.get(key, default))

    def get_all(self) -> dict:
        merged = copy.deepcopy(self._base)
        merged.update(self._overlay)
        return merged

    def apply(self, key: str, value: Any) -> tuple:
        if key in SELFMOD_LOCKED_PARAMS: raise ValueError(f"Parameter '{key}' is locked.")
        if key not in MODIFIABLE_PARAMS: raise ValueError(f"Unknown modifiable parameter: '{key}'.")

        old_value = self.get(key)
        self._overlay[key] = value
        return old_value, value

    def revert(self, key: str, old_value: Any):
        if old_value == self._base.get(key): self._overlay.pop(key, None)
        else: self._overlay[key] = old_value

    def get_overlay(self) -> dict: return copy.deepcopy(self._overlay)

class PermissionSandbox:
    def __init__(self, db, signals):
        self._db      = db
        self._signals = signals
        self._config  = SandboxConfig()
        self._load_active_modifications()
    # Config Access
    @property
    def config(self) -> SandboxConfig: return self._config

    def get(self, key: str, default=None): return self._config.get(key, default)

    def get_all(self) -> dict: return self._config.get_all()
    # Approve
    def approve(self, proposal: Proposal, session_id: str) -> dict:
        key   = proposal.param_key
        value = proposal.param_value
        # Final boundary check (defense in depth)
        if key in SELFMOD_LOCKED_PARAMS: raise ValueError(f"BOUNDARY VIOLATION: '{key}' is locked and cannot be modified.")
        # Apply to sandbox config
        old_value, new_value = self._config.apply(key, value)
        # Write to ledger (append-only)
        entry = {
            "proposal_id":   proposal.id,
            "session_id":    session_id,
            "param_key":     key,
            "param_label":   MODIFIABLE_PARAMS.get(key, {}).get("label", key),
            "old_value":     old_value,
            "new_value":     new_value,
            "proposal_text": proposal.proposal_text,
            "confidence":    proposal.confidence,
            "source":        proposal.source,
            "rolled_back":   False,
        }
        entry_id = self._db.ledger_append(entry)
        entry["_id"] = entry_id
        # Emit signal for UI updates
        self._signals.selfmod_applied.emit(key, new_value)
        return entry
    # Reject
    def reject(self, proposal: Proposal, session_id: str):
        self._db.ledger_append({
            "proposal_id":   proposal.id,
            "session_id":    session_id,
            "param_key":     proposal.param_key,
            "action":        "rejected",
            "proposal_text": proposal.proposal_text,
            "rolled_back":   False,
            "rejected":      True,
        })
    # Rollback
    def rollback(self, entry_id: str) -> tuple:
        all_entries = self._db.ledger_get_all()
        entry = next((e for e in all_entries if e.get("_id") == entry_id), None)

        if not entry: raise ValueError(f"Ledger entry '{entry_id}' not found.")
        if entry.get("rolled_back"): raise ValueError(f"Entry '{entry_id}' has already been rolled back.")
        if entry.get("rejected"): raise ValueError(f"Entry '{entry_id}' was a rejection — nothing to roll back.")

        key       = entry["param_key"]
        old_value = entry["old_value"]
        # Revert config
        self._config.revert(key, old_value)
        # Mark ledger entry as rolled back (never deleted)
        self._db.ledger_mark_rolled_back(entry_id)
        # Emit signal
        self._signals.selfmod_rolled_back.emit(entry_id)
        return key, old_value
    # Ledger Queries
    def get_ledger(self, include_rejected: bool = True) -> list:
        entries = self._db.ledger_get_all()
        if not include_rejected:entries = [e for e in entries if not e.get("rejected")]
        return entries

    def get_active_modifications(self) -> list: return self._db.ledger_get_active()
    # Private
    def _load_active_modifications(self):
        try:
            active = self._db.ledger_get_active()
            # Apply in chronological order (oldest first)
            for entry in reversed(active):
                if entry.get("rejected"): continue
                key   = entry.get("param_key")
                value = entry.get("new_value")
                if key and key not in SELFMOD_LOCKED_PARAMS and key in MODIFIABLE_PARAMS:
                    try: self._config.apply(key, value)
                    except ValueError: pass
        except Exception as e: print(f"[Sandbox] Failed to load active modifications: {e}")
import uuid, datetime
from typing import Optional
from constants import SELFMOD_LOCKED_PARAMS

# The complete set of parameters that CAN be modified.
# Anything not in this dict is implicitly locked.
MODIFIABLE_PARAMS = {
    "output_mode": {
        "type":    "choice",
        "choices": ["verbose", "summary"],
        "default": "verbose",
        "label":   "Output Mode",
        "description": "Controls whether ARIA shows full output or condensed bullet points.",
    },
    "smart_search_threshold": {
        "type":    "float",
        "min":     0.4,
        "max":     0.9,
        "default": 0.75,
        "label":   "Smart Search Confidence Threshold",
        "description": "Minimum classifier confidence required to trigger smart_search mode.",
    },
    "tts_enabled": {
        "type":    "bool",
        "default": True,
        "label":   "Text-to-Speech",
        "description": "Whether ARIA speaks responses aloud.",
    },
    "silent_mode": {
        "type":    "bool",
        "default": False,
        "label":   "Silent Mode",
        "description": "When enabled, only errors/warnings/confirmations are spoken.",
    },
    "default_theme": {
        "type":    "choice",
        "choices": ["cyber", "minimal", "classic"],
        "default": "cyber",
        "label":   "Default Theme",
        "description": "Visual theme applied on startup.",
    },
    "suggestion_count": {
        "type":    "int",
        "min":     3,
        "max":     8,
        "default": 3,
        "label":   "Suggestion Count",
        "description": "Number of contextual suggestions shown in the chat panel.",
    },
    "custom_shortcuts": {
        "type":    "dict",
        "default": {},
        "label":   "Custom Shortcuts",
        "description": "User-defined alias → app/URL mappings.",
    },
    "preferred_search_sites": {
        "type":    "list",
        "default": [],
        "label":   "Preferred Search Sites",
        "description": "Sites ARIA prioritizes when ambiguous search intent is detected.",
    },
    "confirmation_verbosity": {
        "type":    "choice",
        "choices": ["full", "brief"],
        "default": "full",
        "label":   "Confirmation Verbosity",
        "description": "How much detail ARIA shows when asking for command confirmation.",
    },
    "response_length_preference": {
        "type":    "choice",
        "choices": ["concise", "detailed"],
        "default": "concise",
        "label":   "Response Length Preference",
        "description": "Whether ARIA leans toward shorter or more comprehensive answers.",
    },
}

class Proposal:
    def __init__(self, param_key: str, param_value, pattern: dict, proposal_text: str):
        self.id           = str(uuid.uuid4())[:8]
        self.param_key    = param_key
        self.param_value  = param_value
        self.pattern      = pattern
        self.proposal_text= proposal_text
        self.confidence   = pattern.get("confidence", 0.0)
        self.source       = pattern.get("source", "unknown")
        self.created_at   = datetime.datetime.utcnow().isoformat()
        self.status       = "pending"   # pending | approved | rejected

    def to_dict(self) -> dict:
        spec = MODIFIABLE_PARAMS.get(self.param_key, {})
        return {
            "id":            self.id,
            "param_key":     self.param_key,
            "param_value":   self.param_value,
            "param_label":   spec.get("label", self.param_key),
            "param_desc":    spec.get("description", ""),
            "proposal_text": self.proposal_text,
            "confidence":    round(self.confidence, 2),
            "source":        self.source,
            "created_at":    self.created_at,
            "status":        self.status,
        }

class ProposalEngine:
    def __init__(self, llm_client): self._llm = llm_client
    # Public API
    def generate_proposals(self, patterns: list) -> list:
        proposals = []
        for pattern in patterns:
            proposal = self._build_proposal(pattern)
            if proposal: proposals.append(proposal)
        return proposals

    def validate_value(self, param_key: str, value) -> tuple:
        # Locked params are never valid targets
        if param_key in SELFMOD_LOCKED_PARAMS: return False, f"Parameter '{param_key}' is locked and cannot be modified."
        spec = MODIFIABLE_PARAMS.get(param_key)
        if not spec: return False, f"Unknown parameter: '{param_key}'."

        ptype = spec["type"]

        if ptype == "choice":
            if value not in spec["choices"]: return False, f"Invalid value '{value}'. Must be one of: {spec['choices']}"
        elif ptype == "float":
            try:
                v = float(value)
                if not (spec["min"] <= v <= spec["max"]): return False, f"Value {v} out of range [{spec['min']}, {spec['max']}]"
            except (TypeError, ValueError): return False, "Value must be a float."
        elif ptype == "int":
            try:
                v = int(value)
                if not (spec["min"] <= v <= spec["max"]): return False, f"Value {v} out of range [{spec['min']}, {spec['max']}]"
            except (TypeError, ValueError): return False, "Value must be an integer."
        elif ptype == "bool":
            if not isinstance(value, bool): return False, "Value must be boolean (true/false)."
        elif ptype == "list":
            if not isinstance(value, list): return False, "Value must be a list."
        elif ptype == "dict":
            if not isinstance(value, dict): return False, f"Value must be a dict."
        return True, ""
    # Internal
    def _build_proposal(self, pattern: dict) -> Optional[Proposal]:
        param_key   = pattern.get("param_key", "")
        param_value = pattern.get("param_value")
        # Boundary check
        if param_key in SELFMOD_LOCKED_PARAMS: return None
        if param_key not in MODIFIABLE_PARAMS: return None
        # Validate value
        valid, err = self.validate_value(param_key, param_value)
        if not valid:
            print(f"[ProposalEngine] Invalid value for {param_key}: {err}")
            return None
        # Generate human-readable proposal text
        proposal_text = self._llm.generate_proposal_text(pattern)
        return Proposal(
            param_key=param_key,
            param_value=param_value,
            pattern=pattern,
            proposal_text=proposal_text,
        )
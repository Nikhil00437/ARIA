import re
from typing import Optional
from constants import SELFMOD_LOCKED_PARAMS

class BehavioralInferencer:
    # Minimum interactions required before analysis runs
    MIN_INTERACTIONS = 10
    # Confidence threshold below which patterns are discarded
    MIN_CONFIDENCE = 0.65

    def __init__(self, db, llm_client):
        self._db  = db
        self._llm = llm_client
    # Public API
    def analyze(self, session_id: str) -> list:
        interactions = self._db.get_recent_interactions(session_id, n=60)
        if len(interactions) < self.MIN_INTERACTIONS: return []
        patterns = []
        # Tier 1: Rule-based fast detection
        rule_patterns = self._rule_based_analysis(interactions)
        patterns.extend(rule_patterns)
        # Tier 2: LLM deep analysis
        llm_patterns = self._llm.infer_behavioral_patterns(interactions, n=50)
        for p in llm_patterns:
            if self._validate_pattern(p): patterns.append(p)
        # Deduplicate by param_key (keep highest confidence)
        patterns = self._deduplicate(patterns)
        # Filter by confidence
        patterns = [p for p in patterns if p.get("confidence", 0) >= self.MIN_CONFIDENCE]
        return patterns[:5]  # Max 5 proposals at a time
    # Rule-Based Analysis
    def _rule_based_analysis(self, interactions: list) -> list:
        patterns = []

        chat_msgs   = [i for i in interactions if i.get("type") == "chat" and i.get("role") == "user"]
        commands    = [i for i in interactions if i.get("type") == "command"]
        contents    = [c.get("content", "").lower() for c in chat_msgs]
        # Pattern: User prefers summary output
        summary_signals = sum(1 for c in contents if re.search(r"tldr|too long|shorter|brief|summary|summarize", c))
        if summary_signals >= 3: patterns.append({
                "pattern":        "User repeatedly requests shorter/summarized output",
                "evidence":       f"Found {summary_signals} messages requesting brevity",
                "proposed_change":"Set output_mode to 'summary'",
                "param_key":      "output_mode",
                "param_value":    "summary",
                "confidence":     min(0.95, 0.65 + summary_signals * 0.05),
                "reversible":     True,
                "source":         "rule",
            })
        # Pattern: User frequently uses smart_search
        search_msgs = sum(1 for c in contents if re.search(r"search .+ on |find .+ on |look up .+ on ", c))
        if search_msgs >= 4:
            # Extract which sites they prefer
            site_counts: dict = {}
            for c in contents:
                for site in ["youtube", "github", "arxiv", "stackoverflow", "huggingface", "reddit"]:
                    if site in c: site_counts[site] = site_counts.get(site, 0) + 1
            preferred = sorted(site_counts, key=lambda s: site_counts[s], reverse=True)[:3]
            if preferred: patterns.append({
                    "pattern":        f"User frequently searches on {', '.join(preferred)}",
                    "evidence":       f"{search_msgs} smart_search interactions detected",
                    "proposed_change":f"Set preferred_search_sites to {preferred}",
                    "param_key":      "preferred_search_sites",
                    "param_value":    preferred,
                    "confidence":     min(0.92, 0.70 + search_msgs * 0.03),
                    "reversible":     True,
                    "source":         "rule",
                })
        # Pattern: User never uses TTS / always in silent context
        tts_signals = sum(1 for c in contents if re.search(r"stop talking|quiet|mute|no voice|don't speak", c))
        if tts_signals >= 2: patterns.append({
                "pattern":        "User has indicated preference for silent operation",
                "evidence":       f"{tts_signals} messages suppressing voice output",
                "proposed_change":"Enable silent_mode, disable TTS",
                "param_key":      "silent_mode",
                "param_value":    True,
                "confidence":     min(0.95, 0.75 + tts_signals * 0.05),
                "reversible":     True,
                "source":         "rule",
            })
        # Pattern: Repeated failed command → needs confirmation_verbosity brief
        failed_cmds = [c for c in commands if not c.get("success")]
        if len(failed_cmds) >= 3: patterns.append({
                "pattern":        "User has experienced multiple failed commands",
                "evidence":       f"{len(failed_cmds)} failed command executions",
                "proposed_change":"Set confirmation_verbosity to 'full' for more guidance",
                "param_key":      "confirmation_verbosity",
                "param_value":    "full",
                "confidence":     0.75,
                "reversible":     True,
                "source":         "rule",
            })
        # Pattern: User prefers detailed responses
        detail_signals = sum(1 for c in contents if re.search(r"more detail|explain more|elaborate|in depth|comprehensive", c))
        if detail_signals >= 3: patterns.append({
                "pattern":        "User consistently requests more detailed responses",
                "evidence":       f"{detail_signals} requests for elaboration",
                "proposed_change":"Set response_length_preference to 'detailed'",
                "param_key":      "response_length_preference",
                "param_value":    "detailed",
                "confidence":     min(0.92, 0.70 + detail_signals * 0.05),
                "reversible":     True,
                "source":         "rule",
            })
        return patterns
    # Validation
    def _validate_pattern(self, pattern: dict) -> bool:
        required = {"param_key", "param_value", "confidence", "reversible"}
        if not required.issubset(pattern.keys()): return False
        if pattern.get("param_key") in SELFMOD_LOCKED_PARAMS: return False
        if not pattern.get("reversible", False): return False
        return True
    # Deduplication
    def _deduplicate(self, patterns: list) -> list:
        seen: dict = {}
        for p in patterns:
            key = p.get("param_key", "")
            if key not in seen or p.get("confidence", 0) > seen[key].get("confidence", 0): seen[key] = p
        return list(seen.values())
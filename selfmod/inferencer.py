import re
import time
import uuid
from typing import Optional
from constants import SELFMOD_LOCKED_PARAMS

class BehavioralInferencer:
    # Minimum interactions required before analysis runs
    MIN_INTERACTIONS = 10
    # Confidence threshold below which patterns are discarded
    MIN_CONFIDENCE = 0.65
    # Cap on insights returned by ``observe()`` to avoid flooding the feed.
    MAX_OBSERVATIONS = 50

    def __init__(self, db, llm_client):
        self._db  = db
        self._llm = llm_client
    # Public API

    def observe(self, session_id: str) -> list:
        """Return ALL noticed patterns for ``session_id``.

        Distinct from :meth:`analyze` (which kept only the top 5 used for
        proposals). ``observe`` writes each noticed pattern to the insights
        feed via ``self._db.save_insight`` so they persist even if they
        never become a proposal.

        Returns the list of saved insight dicts (newest first).
        """
        interactions = self._db.get_recent_interactions(session_id, n=60)
        if len(interactions) < self.MIN_INTERACTIONS:
            return []

        # Tier 1: rule-based
        patterns = self._rule_based_analysis(interactions)

        # Tier 2: LLM deep analysis — only if rule-based already gave us
        # < 5 high-confidence patterns (saves cost when heuristics suffice).
        rule_passed = sum(1 for p in patterns if self._validate_pattern(p))
        if rule_passed < 5:
            llm_patterns = self._llm.infer_behavioral_patterns(interactions, n=50)
            for p in llm_patterns:
                if self._validate_pattern(p):
                    patterns.append(p)

        # Dedup by param_key (keep highest confidence) + filter by threshold.
        patterns = self._deduplicate(patterns)
        patterns = [p for p in patterns if p.get("confidence", 0) >= self.MIN_CONFIDENCE]

        # Persist as insights.
        saved = []
        for p in patterns[: self.MAX_OBSERVATIONS]:
            insight = dict(p)
            insight.setdefault("kind", p.get("source", "rule"))
            insight.setdefault("label", p.get("pattern", p.get("param_key", "?")))
            insight.setdefault("evidence", p.get("evidence", ""))
            insight.setdefault("param_key", p.get("param_key"))
            insight["session_id"] = session_id
            self._db.save_insight(insight)
            saved.append(insight)
        return saved

    def propose(self, patterns: list) -> list:
        """Pick up to 5 modifiable proposals from a list of noticed patterns.

        Equivalent to the top-5 + dedup + threshold filter the old ``analyze``
        applied, but operating on an explicit input list (e.g. the insights
        just observed) instead of re-running inference.
        """
        kept = [p for p in patterns if self._validate_pattern(p)]
        kept = [p for p in kept if p.get("confidence", 0) >= self.MIN_CONFIDENCE]
        kept = self._deduplicate(kept)
        return kept[:5]

    def analyze(self, session_id: str) -> list:
        """Backward-compat shim — returns up to 5 proposals as before."""
        patterns = self.observe(session_id)
        return self.propose(patterns)

    def analyze_from_text(self, raw_text: str) -> list:
        """Observe + propose from a free-text conversation dump."""
        interactions = self._parse_conversation_text(raw_text)
        if len(interactions) < self.MIN_INTERACTIONS:
            return []
        patterns = self._rule_based_analysis(interactions)
        llm_patterns = self._llm.infer_behavioral_patterns(interactions, n=50)
        for p in llm_patterns:
            if self._validate_pattern(p):
                patterns.append(p)
        # Persist observed patterns (no session_id — they're from a file).
        for p in self._deduplicate(patterns)[: self.MAX_OBSERVATIONS]:
            self._db.save_insight(dict(p))
        return self.propose(patterns)

    def _parse_conversation_text(self, text: str) -> list:
        lines = text.split("\n")
        interactions = []
        current_role = None
        current_content = []

        def _flush():
            nonlocal current_role, current_content
            if current_role and current_content:
                content = "\n".join(current_content).strip()
                if content:
                    interactions.append({
                        "type": "chat",
                        "role": current_role,
                        "content": content,
                    })
            current_content = []

        user_patterns = [
            re.compile(r"^(User|Human|You|Customer|Prompt)\s*[:\-\–]\s*", re.IGNORECASE),
            re.compile(r"^#{1,3}\s*(User|Human|You)\b", re.IGNORECASE),
            re.compile(r"^\*\*(User|Human|You)\*\*\s*[:\-\–]?\s*", re.IGNORECASE),
        ]
        assistant_patterns = [
            re.compile(r"^(Assistant|AI|Model|Bot|Aria|ARIA)\s*[:\-\–]\s*", re.IGNORECASE),
            re.compile(r"^#{1,3}\s*(Assistant|AI|Model)\b", re.IGNORECASE),
            re.compile(r"^\*\*(Assistant|AI|Model|Bot|Aria|ARIA)\*\*\s*[:\-\–]?\s*", re.IGNORECASE),
        ]

        for line in lines:
            matched = False
            for pat in user_patterns:
                m = pat.match(line)
                if m:
                    _flush()
                    current_role = "user"
                    line = line[m.end():]
                    matched = True
                    break
            if not matched:
                for pat in assistant_patterns:
                    m = pat.match(line)
                    if m:
                        _flush()
                        current_role = "assistant"
                        line = line[m.end():]
                        matched = True
                        break

            if matched:
                if line.strip():
                    current_content.append(line.strip())
            else:
                if current_role is None:
                    current_role = "user"
                current_content.append(line)

        _flush()
        return interactions
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
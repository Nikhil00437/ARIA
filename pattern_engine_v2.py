# pattern_engine.py — Fabric Pattern Engine for ARIA (v2, with URL fetching)

import os
import re
import threading
from pathlib import Path
from typing import Optional, Generator

from web_fetcher import resolve_input

# Pattern directory
_PATTERNS_DIR = Path(__file__).parent / "patterns"

# Intent keywords → pattern names
PATTERN_INTENT_MAP = {
    r"\b(summarize|summary|tldr|tl;dr)\b":               "summarize",
    r"\bkey (points?|takeaways?|ideas?)\b":              "extract_wisdom",
    r"\b(extract|pull out) (insights?|wisdom|lessons?)": "extract_wisdom",
    r"\b(analyze|analyse) (claims?|arguments?|logic)\b": "analyze_claims",
    r"\bfact.?check\b":                                  "analyze_claims",
    r"\b(improve|fix|enhance|rewrite) (this|my|the) (essay|article|writing|text|post)\b": "improve_writing",
    r"\b(improve|optimize|enhance) (this|my|the) prompt\b": "improve_prompt",
    r"\b(security|threat|vulnerability|pentest)\b":       "create_threat_scenarios",
    r"\b(ideas?|brainstorm|ideate)\b":                   "create_idea_compass",
    r"\b(agile|user stor|sprint)\b":                     "agility_story",
    r"\b(debate|argument|position)\b":                   "analyze_debate",
    r"\b(explain|eli5|layman)\b":                        "explain_docs",
    r"\b(youtube|video) (summary|notes?)\b":             "summarize",
    r"\b(paper|research|academic)\b":                    "summarize",
}

# Core functions
def get_patterns_dir() -> Path: return _PATTERNS_DIR

def list_patterns() -> list[dict]:
    if not _PATTERNS_DIR.exists(): return []
    patterns = []
    for entry in sorted(_PATTERNS_DIR.iterdir()):
        if entry.is_dir():
            sys_md = entry / "system.md"
            if sys_md.exists():
                patterns.append({
                    "name":    entry.name,
                    "path":    str(sys_md),
                    "preview": _read_preview(sys_md),
                })
    return patterns

def load_pattern(name: str) -> Optional[str]:
    sys_md = _PATTERNS_DIR / name / "system.md"
    if not sys_md.exists():
        for entry in _PATTERNS_DIR.iterdir():
            if entry.name.lower() == name.lower() and (entry / "system.md").exists():
                sys_md = entry / "system.md"
                break
        else: return None
    return sys_md.read_text(encoding="utf-8")

def load_user_prompt(name: str) -> Optional[str]:
    user_md = _PATTERNS_DIR / name / "user.md"
    return user_md.read_text(encoding="utf-8") if user_md.exists() else None

def match_intent(text: str) -> Optional[str]:
    text_lower = text.lower()
    for pattern_re, pattern_name in PATTERN_INTENT_MAP.items():
        if re.search(pattern_re, text_lower, re.I):
            if (_PATTERNS_DIR / pattern_name / "system.md").exists(): return pattern_name
    return None

def search_patterns(query: str) -> list[dict]:
    query_lower = query.lower()
    return [
        p for p in list_patterns()
        if query_lower in p["name"].lower() or query_lower in p["preview"].lower()
    ][:20]

def run_pattern_stream(
    name: str,
    user_input: str,
    llm_client,
) -> Generator[str, None, None]:
    # Run a pattern and yield response chunks (streaming).
    # Automatically fetches URLs if user_input contains one.
    system_prompt = load_pattern(name)
    if not system_prompt:
        yield f"❌ Pattern '{name}' not found. Use `/pattern list` to see available patterns."
        return

    # URL resolution
    resolved_input, url = resolve_input(user_input.strip())

    if url:
        # Check if resolve returned an error (starts with ⚠️ 🔒 ❌ ⏱️)
        if resolved_input and resolved_input[0] in ("⚠", "🔒", "❌", "⏱"):
            yield resolved_input   # emit the error message directly
            return
        # Success — tell user we fetched it
        yield f"🌐 Fetched: `{url}`\n\n---\n\n"

    content = resolved_input or load_user_prompt(name) or "Process the above."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": content},
    ]
    yield from llm_client.chat_stream(messages)

# Helpers
def _read_preview(path: Path, max_chars: int = 120) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line[:max_chars] + ("…" if len(line) > max_chars else "")
    except Exception: pass
    return ""
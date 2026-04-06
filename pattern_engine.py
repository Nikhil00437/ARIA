# pattern_engine.py — Fabric Pattern Engine for ARIA
# Loads patterns from ./patterns/<name>/system.md
# Provides: list, load, run (streaming), intent-matching

import os, re, threading
from pathlib import Path
from typing import Optional, Generator

# Pattern directory
_PATTERNS_DIR = Path(__file__).parent / "patterns"

# Intent keywords → pattern names (for auto-suggest)
PATTERN_INTENT_MAP = {
    # summarization
    r"\b(summarize|summary|tldr|tl;dr)\b":              "summarize",
    r"\bkey (points?|takeaways?|ideas?)\b":             "extract_wisdom",
    r"\b(extract|pull out) (insights?|wisdom|lessons?)": "extract_wisdom",
    # analysis
    r"\b(analyze|analyse) (claims?|arguments?|logic)\b": "analyze_claims",
    r"\bfact.?check\b":                                  "analyze_claims",
    r"\b(rate|score|evaluate|assess) (this|the) (content|article|post|video)": "rate_content",
    r"\b(pros? and cons?|tradeoffs?|compare)\b":         "create_idea_compass",
    # writing / improvement
    r"\b(improve|fix|enhance|rewrite) (this|my|the) (essay|article|writing|text|post)\b": "improve_writing",
    r"\b(improve|optimize|enhance) (this|my|the) prompt\b": "improve_prompt",
    r"\bcreate (a )?pattern\b":                          "create_pattern",
    # security
    r"\b(security|threat|vulnerability|pentest|red.?team)\b": "create_threat_scenarios",
    r"\b(analyze|review) (the )?(code|script) for (security|vulnerabilities)\b": "find_hidden_message",
    # productivity / ideas
    r"\b(ideas?|brainstorm|ideate)\b":                   "create_idea_compass",
    r"\b(agile|user stor|sprint)\b":                     "agility_story",
    r"\bpodcast\b":                                      "create_show_intro",
    # youtube / video
    r"\b(youtube|video) (summary|transcript|notes?)\b":  "summarize",
    # academic / research
    r"\b(paper|research|academic|study)\b":              "summarize",
    r"\b(debate|argument|position)\b":                   "analyze_debate",
    # explain
    r"\b(explain|eli5|layman)\b":                        "explain_docs",
}

# Core functions 
def get_patterns_dir() -> Path: return _PATTERNS_DIR

def list_patterns() -> list[dict]:
    # Return list of {name, path, preview} for all available patterns.
    if not _PATTERNS_DIR.exists(): return []
    patterns = []
    for entry in sorted(_PATTERNS_DIR.iterdir()):
        if entry.is_dir():
            sys_md = entry / "system.md"
            if sys_md.exists():
                preview = _read_preview(sys_md)
                patterns.append({
                    "name":    entry.name,
                    "path":    str(sys_md),
                    "preview": preview,
                })
    return patterns

def load_pattern(name: str) -> Optional[str]:
    # Load system.md content for a pattern. Returns None if not found.
    sys_md = _PATTERNS_DIR / name / "system.md"
    if not sys_md.exists():
        # Try case-insensitive match
        for entry in _PATTERNS_DIR.iterdir():
            if entry.name.lower() == name.lower() and (entry / "system.md").exists():
                sys_md = entry / "system.md"
                break
        else: return None
    return sys_md.read_text(encoding="utf-8")

def load_user_prompt(name: str) -> Optional[str]:
    # Load user.md if it exists (some patterns have one).
    user_md = _PATTERNS_DIR / name / "user.md"
    if user_md.exists():
        return user_md.read_text(encoding="utf-8")
    return None

def match_intent(text: str) -> Optional[str]:
    # Return best matching pattern name for user input, or None.
    text_lower = text.lower()
    for pattern_re, pattern_name in PATTERN_INTENT_MAP.items():
        if re.search(pattern_re, text_lower, re.I):
            # Verify pattern actually exists before returning
            if (_PATTERNS_DIR / pattern_name / "system.md").exists():
                return pattern_name
            # Pattern doesn't exist — continue checking other patterns
    return None

def search_patterns(query: str) -> list[dict]:
    # Search pattern names and previews for a query string.
    query_lower = query.lower()
    results = []
    for p in list_patterns():
        if (query_lower in p["name"].lower() or
                query_lower in p["preview"].lower()):
            results.append(p)
    return results[:20]

def run_pattern_stream(
    name: str,
    user_input: str,
    llm_client,
) -> Generator[str, None, None]:
    # Run a pattern and yield response chunks (streaming).
    # llm_client must have a chat_stream(messages) method.
    system_prompt = load_pattern(name)
    if not system_prompt:
        yield f"❌ Pattern '{name}' not found. Use `/pattern list` to see available patterns."
        return

    user_content = user_input.strip() or load_user_prompt(name) or "Process the above."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_content},
    ]
    yield from llm_client.chat_stream(messages)

# Helpers
def _read_preview(path: Path, max_chars: int = 120) -> str:
    # Extract a short description from system.md — first non-empty line after # headers.
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line[:max_chars] + ("…" if len(line) > max_chars else "")
    except Exception: pass
    return ""
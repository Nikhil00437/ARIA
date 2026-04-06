# web_fetcher.py — URL-to-text fetcher for ARIA Pattern Engine
# Uses Jina Reader API (free, no key needed) to convert any public URL
# into clean markdown. Detects login walls and paywalls gracefully.

import re, requests
from typing import Tuple

JINA_BASE    = "https://r.jina.ai/"
FETCH_TIMEOUT = 30   # seconds

# Login / paywall detection keywords
_WALL_PATTERNS = [
    r"\bsign\s*in\b",
    r"\blog\s*in\b",
    r"\blogin\b",
    r"\bcreate\s+an?\s+account\b",
    r"\bsubscribe\s+to\s+(read|access|continue)\b",
    r"\bpaywall\b",
    r"\bpremium\s+(content|article|access)\b",
    r"\baccess\s+denied\b",
    r"\b403\s+forbidden\b",
    r"\bverify\s+you('re|\s+are)\s+human\b",
    r"\bcaptcha\b",
    r"\bcloudflare\b.*\bray\s+id\b",
    r"\bthis\s+content\s+is\s+(for\s+)?(members?|subscribers?)\b",
    r"\byou('ve|\s+have)\s+(reached|hit)\s+(your\s+)?(free\s+)?(article|read)\s+limit\b",
]

_URL_RE = re.compile(
    r"https?://[^\s]+",
    re.IGNORECASE
)

# Public API

def is_url(text: str) -> bool:
    # Return True if text looks like a URL
    return bool(_URL_RE.match(text.strip()))

def extract_url(text: str) -> Tuple[str | None, str]:
    # Extract URL from text. Returns (url, remaining_text).
    # remaining_text is everything after the URL (extra instructions).
    m = _URL_RE.search(text.strip())
    if not m: return None, text
    url = m.group(0).rstrip(".,;)")
    remaining = text[:m.start()].strip() + " " + text[m.end():].strip()
    return url, remaining.strip()

def fetch_url(url: str) -> Tuple[bool, str]:
    # Fetch a URL via Jina Reader. Returns (success, content_or_error_message).
    # success=True  → content is clean markdown ready to feed into a pattern
    # success=False → content is a user-friendly error message
    try:
        headers = {
            "User-Agent":  "ARIA-Desktop/1.0",
            "Accept":      "text/plain, text/markdown, */*",
        }
        r = requests.get(
            f"{JINA_BASE}{url}",
            headers=headers,
            timeout=FETCH_TIMEOUT,
        )

        if r.status_code == 429: return False, (
                "⚠️ Jina Reader rate limit hit. Wait a moment and try again, "
                "or paste the content manually."
            )

        if r.status_code >= 500: return False, (
                f"⚠️ Jina Reader returned a server error ({r.status_code}). "
                "The site may be down or blocking scrapers."
            )

        content = r.text.strip()

        if not content or len(content) < 50: return False, (
                "⚠️ Fetched page appears empty. The site may block automated access. "
                "Try pasting the content manually."
            )

        # Check for login/paywall wall
        wall_hit = _detect_wall(content)
        if wall_hit: return False, (
                f"🔒 This page requires login or a subscription ({wall_hit}).\n\n"
                "**Workaround:** Open the page in your browser, select all text "
                "(Ctrl+A → Ctrl+C), then paste it into the pattern input instead of the URL."
            )

        return True, content

    except requests.exceptions.Timeout: return False, (
            f"⏱️ Request timed out after {FETCH_TIMEOUT}s. "
            "The site may be slow or blocking scrapers."
        )
    except requests.exceptions.ConnectionError: return False, (
            "❌ Could not connect. Check your internet connection or "
            "the URL may be invalid."
        )
    except Exception as e: return False, f"❌ Fetch error: {e}"

def resolve_input(user_input: str) -> Tuple[str, str | None]:
    # Main entry point for pattern_engine.
    # If user_input contains a URL, fetch it and return (resolved_text, url).
    # If fetch fails, return (error_message, url) — caller should emit error.
    # If no URL, return (user_input, None) unchanged.
    url, extra = extract_url(user_input)
    if not url: return user_input, None

    success, content = fetch_url(url)
    if not success: return content, url   # content is the error message here

    # Prepend any extra instructions the user typed alongside the URL
    if extra: return f"{extra}\n\n---\n\n{content}", url
    return content, url

# Internal
def _detect_wall(content: str) -> str | None:
    # Returns a short description of the wall type if detected, else None.
    # Checks only the first 2000 chars — login walls appear early in the page.
    sample = content[:2000].lower()
    for pat in _WALL_PATTERNS:
        m = re.search(pat, sample, re.I)
        if m: return m.group(0)[:40]
    return None
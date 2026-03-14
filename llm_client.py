import json
from openai import OpenAI
from extract import offline_classify
from constants import INTENT_CLASSIFIER_PROMPT, SUMMARIZE_PROMPT, EXPLAIN_PROMPT, URL_GEN_PROMPT, SEARCH_URL_TEMPLATES, SITE_ALIASES

client_llm = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

CHAT_MODEL    = "qwen3-vl-8b-instruct"
INTENT_MODEL  = "oh-dcft-v3.1-claude-3-5-sonnet-20241022"
VALID_MODES = (
    "chat", "command", "wikipedia", "browser", "music", "search",
    "show_apps", "time", "quick_open", "smart_search", "powershell",
    "explain", "history", "rerun", "image_gen",
)

def classify_intent(user_input: str) -> dict:
    offline = offline_classify(user_input)
    if offline: return offline
    try:
        messages = [
            {"role": "system", "content": INTENT_CLASSIFIER_PROMPT},
            {"role": "user",   "content": user_input},
        ]
        completion = client_llm.chat.completions.create(
            model=INTENT_MODEL,
            messages=messages,
            temperature=0.1,
            max_tokens=200,
        )
        raw = completion.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        intent = json.loads(raw)
        assert intent["mode"] in VALID_MODES
        assert 0.0 <= intent["confidence"] <= 1.0
        return intent
    except Exception as e:
        return {
            "mode": "chat",
            "confidence": 0.0,
            "reason": f"Classification error: {e}",
            "action": None,
        }

def summarize_output(raw_output: str) -> str:
    try:
        comp = client_llm.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": SUMMARIZE_PROMPT},
                {"role": "user",   "content": raw_output[:3000]},
            ],
            temperature=0.3,
            max_tokens=400,
        )
        return comp.choices[0].message.content.strip()
    except Exception as e:
        return f"(Summary unavailable: {e})\n\n{raw_output}"

def explain_output(subject: str, context: str = "") -> str:
    try:
        prompt = f"Subject: {subject}"
        if context:
            prompt += f"\n\nOutput/context:\n{context[:2000]}"
        comp = client_llm.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": EXPLAIN_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.5,
            max_tokens=600,
        )
        return comp.choices[0].message.content.strip()
    except Exception as e:
        return f"(Explanation unavailable: {e})"

def chat_completion(messages: list, temperature: float = 0.7, max_tokens: int = 800) -> str:
    comp = client_llm.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return comp.choices[0].message.content.strip()

def generate_search_url(user_input: str) -> dict:
    import re, urllib.parse

    text = user_input.strip()
    lower = text.lower()

    # Regex fast-path
    def _encode(q: str) -> str:
        return urllib.parse.quote_plus(q.strip())

    def _resolve_site(name: str) -> str:
        """Normalise alias → canonical key."""
        name = name.lower().strip()
        return SITE_ALIASES.get(name, name)

    def _make_url(site_key: str, query: str) -> str | None:
        template = SEARCH_URL_TEMPLATES.get(site_key)
        if not template:
            return None
        return template.replace("{query}", _encode(query))

    # Pattern: "search <site> for <query>"  /  "find <query> on <site>"
    m = re.search(
        r"search\s+(\w+)\s+(?:for\s+)?(.+)$",
        lower, re.IGNORECASE
    )
    if m:
        site_key = _resolve_site(m.group(1))
        query    = m.group(2).strip()
        if site_key in SEARCH_URL_TEMPLATES:
            url = _make_url(site_key, query)
            return {"site": site_key, "url": url,
                    "explanation": f"Searching {site_key} for '{query}'"}

    m = re.search(
        r"(?:find|look\s*up)\s+(.+?)\s+on\s+(\w[\w\s]*)$",
        lower, re.IGNORECASE
    )
    if m:
        query    = m.group(1).strip()
        site_key = _resolve_site(m.group(2).strip())
        if site_key in SEARCH_URL_TEMPLATES:
            url = _make_url(site_key, query)
            return {"site": site_key, "url": url,
                    "explanation": f"Searching {site_key} for '{query}'"}

    # Pattern: "open github <username>"  →  direct profile
    m = re.search(r"open\s+github\s+(\S+)", lower)
    if m:
        username = m.group(1).lstrip("@")
        url = f"https://github.com/{username}"
        return {"site": "github", "url": url,
                "explanation": f"Opening GitHub profile: {username}"}

    # Pattern: "open youtube @<handle>"  →  direct channel
    m = re.search(r"open\s+youtube\s+@?(\S+)", lower)
    if m:
        handle = m.group(1).lstrip("@")
        url = f"https://www.youtube.com/@{handle}"
        return {"site": "youtube", "url": url,
                "explanation": f"Opening YouTube channel: @{handle}"}

    # Pattern: "google <query>"
    m = re.search(r"^google\s+(.+)$", lower)
    if m:
        url = _make_url("google", m.group(1).strip())
        return {"site": "google", "url": url,
                "explanation": f"Google search: '{m.group(1).strip()}'"}

    # Pattern: "<site> <query>"  — bare "youtube networkchuck" style
    for site_key, template in SEARCH_URL_TEMPLATES.items():
        pattern = rf"^{re.escape(site_key)}\s+(.+)$"
        m = re.match(pattern, lower)
        if m:
            url = _make_url(site_key, m.group(1).strip())
            return {"site": site_key, "url": url,
                    "explanation": f"Searching {site_key}"}

    # LLM fallback
    try:
        template_lines = "\n".join(
            f"  {k}: {v}" for k, v in SEARCH_URL_TEMPLATES.items()
        )
        system = URL_GEN_PROMPT.replace("{templates}", template_lines)
        raw = chat_completion(
            [{"role": "system", "content": system},
             {"role": "user",   "content": text}],
            temperature=0.1,
            max_tokens=200,
        )
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        if data.get("url"):
            return {
                "site":        data.get("site", "web"),
                "url":         data["url"],
                "explanation": data.get("explanation", f"Opening {data['url']}"),
            }
    except Exception:
        pass

    # Absolute fallback — google everything
    url = _make_url("google", text)
    return {"site": "google", "url": url,
            "explanation": f"Google search: '{text}'"}
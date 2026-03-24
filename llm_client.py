import re, json, requests
from typing import Optional, Generator
from constants import (
    LM_STUDIO_BASE_URL, CHAT_MODEL, CLASSIFIER_MODEL,
    LLM_TIMEOUT, LLM_CHAT_TEMPERATURE, LLM_CLASS_TEMPERATURE,
    SYSTEM_PROMPT, INTENT_CLASSIFIER_PROMPT, SUMMARIZE_PROMPT,
    EXPLAIN_PROMPT, URL_GEN_PROMPT, BEHAVIORAL_INFERENCE_PROMPT,
    PROPOSAL_GENERATION_PROMPT, SEARCH_TEMPLATES, SITE_ALIASES,
)

class LLMClient:
    def __init__(self):
        self._base = LM_STUDIO_BASE_URL
        self._chat_model = CHAT_MODEL
        self._cls_model  = CLASSIFIER_MODEL
    # Connectivity
    def ping(self) -> bool:
        try:
            r = requests.get(f"{self._base}/models", timeout=5)
            return r.status_code == 200
        except Exception: return False
    # Internal helpers
    def _post(self, payload: dict, stream: bool = False) -> requests.Response:
        return requests.post(
            f"{self._base}/chat/completions",
            json=payload,
            timeout=LLM_TIMEOUT,
            stream=stream,
        )

    def _simple(self, model: str, system: str, user: str, temperature: float = 0.7) -> str:
        payload = {
            "model":       model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        }
        r = self._post(payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()

    # Intent Classification
    # Fast offline regex paths — zero LLM cost
    _OFFLINE_PATTERNS = [
        (r"^(hi|hello|hey|howdy|yo)\b",                         "chat",        0.99),
        (r"\bopen\s+\w+\b",                                     "command",     0.90),
        (r"\bplay\s+.+\b",                                      "music",       0.92),
        (r"^https?://",                                         "browser",     0.99),
        (r"\bwhat (time|date) is it\b",                         "time",        0.99),
        (r"\b(show|list) (apps|installed)\b",                   "show_apps",   0.95),
        (r"\b(ram|memory|cpu|disk|port|service|startup)\s*(usage|info|space|list)?\b", "powershell", 0.88),
        (r"\b(search|find|look up)\s+.+\s+on\s+(youtube|github|arxiv|stackoverflow|huggingface|pypi|npm|reddit)\b", "smart_search", 0.95),
        (r"\bwhat is\b|\bexplain\b|\bwho (is|was)\b",          "wikipedia",   0.80),
        (r"\bgenerate.*(image|picture|photo|art)\b",            "image_gen",   0.93),
        (r"\bexplain.*(code|function|class|error|snippet)\b",   "explain",     0.91),
        (r"^/history\b",                                        "history",     0.99),
        (r"^/rerun\s+\d+",                                      "rerun",       0.99),
    ]
    
    def classify_intent(self, message: str) -> dict:
        msg_lower = message.strip().lower()
        # Try offline patterns first
        for pattern, mode, conf in self._OFFLINE_PATTERNS:
            if re.search(pattern, msg_lower): return {"mode": mode, "confidence": conf, "source": "offline"}
        # Fall back to LLM
        try:
            prompt = INTENT_CLASSIFIER_PROMPT.format(message=message)
            raw = self._simple(
                self._cls_model,
                "You are a fast intent classifier. Output only JSON.",
                prompt,
                temperature=LLM_CLASS_TEMPERATURE,
            )
            # Strip markdown fences if present
            raw = re.sub(r"```json|```", "", raw).strip()
            result = json.loads(raw)
            result["source"] = "llm"
            return result
        except Exception as e: return {"mode": "chat", "confidence": 0.5, "source": "fallback", "error": str(e)}
    # Chat (streaming)
    def chat_stream(self, messages: list) -> Generator[str, None, None]:
        payload = {
            "model":       self._chat_model,
            "temperature": LLM_CHAT_TEMPERATURE,
            "stream":      True,
            "messages":    [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        }
        try:
            r = self._post(payload, stream=True)
            r.raise_for_status()
            for line in r.iter_lines():
                if not line: continue
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]": break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"].get("content", "")
                        if delta: yield delta
                    except json.JSONDecodeError: continue
        except Exception as e: yield f"\n\n[LLM Error: {e}]"

    def chat(self, messages: list) -> str:
        payload = {
            "model":       self._chat_model,
            "temperature": LLM_CHAT_TEMPERATURE,
            "messages":    [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        }
        try:
            r = self._post(payload)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e: return f"[LLM Error: {e}]"
    # Summarize 
    def summarize(self, text: str) -> str:
        prompt = SUMMARIZE_PROMPT.format(output=text[:3000])
        try: return self._simple(self._chat_model, "Summarize concisely.", prompt, 0.3)
        except Exception as e: return f"[Summarize Error: {e}]"
    # Explain
    def explain(self, content: str) -> str:
        prompt = EXPLAIN_PROMPT.format(content=content[:4000])
        try: return self._simple(self._chat_model, "You are a technical explainer.", prompt, 0.5)
        except Exception as e: return f"[Explain Error: {e}]"
    # Smart URL generation
    _URL_FAST_PATTERNS = [
        (r"(?:search\s+)?(\w+)\s+for\s+(.+)", "_handle_site_search"),
        (r"(?:go to|open|visit)\s+(https?://\S+)", "_handle_direct_url"),
        (r"(?:go to|open|visit)\s+([\w.]+\.(?:com|org|net|io|dev|ai))", "_handle_bare_domain"),
    ]

    def generate_url(self, query: str) -> Optional[str]:
        q = query.strip()
        # Pattern: "search <site> for <query>" or "<site> for <query>"
        m = re.search(r"(?:search\s+)?(\w+)\s+for\s+(.+)", q, re.I)
        if m:
            site_raw, search_q = m.group(1).lower(), m.group(2).strip()
            site = SITE_ALIASES.get(site_raw, site_raw)
            if site in SEARCH_TEMPLATES: return SEARCH_TEMPLATES[site].replace("{q}", requests.utils.quote(search_q))
        # Pattern: direct URL
        m = re.search(r"(https?://\S+)", q)
        if m: return m.group(1)
        # Pattern: bare domain
        m = re.search(r"([\w-]+\.(?:com|org|net|io|dev|ai|edu|gov))", q, re.I)
        if m: return f"https://{m.group(1)}"
        # LLM fallback
        try:
            url = self._simple(
                self._chat_model,
                "You generate URLs only. Return a single URL, nothing else.",
                URL_GEN_PROMPT.format(query=q),
                temperature=0.1,
            )
            url = url.strip().split()[0]
            if url.startswith("http"): return url
        except Exception: pass
        # Final fallback: Google
        return SEARCH_TEMPLATES["google"].replace("{q}", requests.utils.quote(q))
    # Behavioral Inference
    def infer_behavioral_patterns(self, interactions: list, n: int = 40) -> list:
        if not interactions: return []
        history_str = json.dumps(interactions[:n], indent=2)
        prompt = BEHAVIORAL_INFERENCE_PROMPT.format(n=min(n, len(interactions)), history=history_str)
        try:
            raw = self._simple(
                self._chat_model,
                "You are a behavioral pattern analyzer. Output only JSON arrays.",
                prompt,
                temperature=0.2,
            )
            raw = re.sub(r"```json|```", "", raw).strip()
            patterns = json.loads(raw)
            if isinstance(patterns, list): return patterns
        except Exception as e: print(f"[Behavioral Inference] Error: {e}")
        return []

    def generate_proposal_text(self, pattern: dict) -> str:
        prompt = PROPOSAL_GENERATION_PROMPT.format(
            pattern=pattern.get("pattern", ""),
            proposed_change=pattern.get("proposed_change", ""),
            confidence=pattern.get("confidence", 0.0),
        )
        try: return self._simple(
                self._chat_model,
                "Write concise UI proposal text for the user.",
                prompt,
                temperature=0.4,
            )
        except Exception: return pattern.get("proposed_change", "Configuration change proposed.")
    # Wikipedia
    def wikipedia_lookup(self, query: str) -> str:
        try:
            import urllib.parse
            q = urllib.parse.quote(query)
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{q}"
            r = requests.get(url, timeout=8)
            if r.status_code == 200:
                data = r.json()
                title   = data.get("title", "")
                extract = data.get("extract", "No summary available.")
                page_url= data.get("content_urls", {}).get("desktop", {}).get("page", "")
                return f"**{title}**\n\n{extract}\n\n[Read more]({page_url})"
            else: return f"Wikipedia: No article found for '{query}'."
        except Exception as e: return f"Wikipedia lookup failed: {e}"
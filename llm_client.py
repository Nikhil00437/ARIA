import re, json, time, requests
from typing import Optional, Generator, Dict, List
from constants import (
    LM_STUDIO_BASE_URL, CHAT_MODEL, CLASSIFIER_MODEL,
    LLM_TIMEOUT, LLM_CHAT_TEMPERATURE, LLM_CLASS_TEMPERATURE,
    SYSTEM_PROMPT, INTENT_CLASSIFIER_PROMPT, SUMMARIZE_PROMPT,
    EXPLAIN_PROMPT, URL_GEN_PROMPT, BEHAVIORAL_INFERENCE_PROMPT,
    PROPOSAL_GENERATION_PROMPT, SEARCH_TEMPLATES, SITE_ALIASES,
)
from security import get_rate_limiter

# Approximate tokens per character for English text (varies by model)
CHARS_PER_TOKEN = 3.5

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0  # seconds
MAX_BACKOFF = 30.0  # seconds
BACKOFF_MULTIPLIER = 2.0


class LLMConnectionError(Exception):
    """Raised when LLM connection fails after all retries."""
    pass


class LLMTimeoutError(Exception):
    """Raised when LLM request times out."""
    pass


class LLMRateLimitError(Exception):
    """Raised when rate limit is exceeded."""
    pass


class LLMProviderManager:
    """Manages multiple LLM providers with automatic fallback."""
    
    # Default providers
    DEFAULT_PROVIDERS = [
        {"name": "lm_studio", "base_url": "http://localhost:1234/v1", "enabled": True},
        {"name": "ollama", "base_url": "http://localhost:11434", "enabled": False},
        {"name": "openai_compatible", "base_url": "http://localhost:8000/v1", "enabled": False},
    ]
    
    def __init__(self):
        self._providers = self.DEFAULT_PROVIDERS.copy()
        self._current_provider_idx = 0
        self._provider_status: Dict[str, bool] = {}
    
    def get_current_provider(self) -> Dict:
        """Get the currently active provider."""
        for i, p in enumerate(self._providers):
            if p.get("enabled", False):
                self._current_provider_idx = i
                return p
        # If no enabled provider, return first one
        return self._providers[0]
    
    def get_current_base_url(self) -> str:
        """Get the base URL for the current provider."""
        return self.get_current_provider()["base_url"]
    
    def set_provider_enabled(self, name: str, enabled: bool):
        """Enable or disable a provider."""
        for p in self._providers:
            if p["name"] == name:
                p["enabled"] = enabled
                if enabled:
                    self._current_provider_idx = self._providers.index(p)
                break
    
    def mark_provider_failed(self, name: str):
        """Mark a provider as failed and try the next one."""
        self._provider_status[name] = False
        print(f"[Provider] {name} marked as failed, trying next provider...")
        
        # Find next enabled provider
        for i in range(len(self._providers)):
            next_idx = (self._current_provider_idx + i + 1) % len(self._providers)
            if self._providers[next_idx].get("enabled", False):
                self._current_provider_idx = next_idx
                print(f"[Provider] Switched to: {self._providers[next_idx]['name']}")
                return True
        return False
    
    def mark_provider_success(self, name: str):
        """Mark a provider as working."""
        self._provider_status[name] = True
    
    def get_all_providers(self) -> List[Dict]:
        """Get all available providers."""
        return self._providers.copy()
    
    def add_provider(self, name: str, base_url: str):
        """Add a new provider."""
        self._providers.append({
            "name": name,
            "base_url": base_url,
            "enabled": False
        })
    
    def remove_provider(self, name: str):
        """Remove a provider."""
        self._providers = [p for p in self._providers if p["name"] != name]
    
    def get_provider_status(self, name: str) -> bool:
        """Get the status of a provider."""
        return self._provider_status.get(name, True)  # Default to True (working)

class LLMClient:
    def __init__(self):
        self._provider_manager = LLMProviderManager()
        self._base = self._provider_manager.get_current_base_url()
        self._chat_model = CHAT_MODEL
        self._cls_model  = CLASSIFIER_MODEL
        self._max_context_tokens = 8192  # safe default for most local models
        self._max_retries = 2

    # Connectivity
    def ping(self) -> bool:
        try:
            r = requests.get(f"{self._base}/models", timeout=5)
            if r.status_code == 200:
                self._provider_manager.mark_provider_success(
                    self._provider_manager.get_current_provider()["name"]
                )
                return True
            return False
        except Exception:
            # Try fallback providers
            provider = self._provider_manager.get_current_provider()
            self._provider_manager.mark_provider_failed(provider["name"])
            return False
    
    def get_provider_status(self) -> Dict[str, bool]:
        """Get status of all providers."""
        return {
            p["name"]: self._provider_manager.get_provider_status(p["name"])
            for p in self._provider_manager.get_all_providers()
        }
    
    def switch_provider(self, name: str) -> bool:
        """Manually switch to a specific provider."""
        self._provider_manager.set_provider_enabled(name, True)
        self._base = self._provider_manager.get_current_base_url()
        return self.ping()

    def get_loaded_models(self) -> list:
        try:
            r = requests.get(f"{self._base}/models", timeout=5)
            if r.status_code == 200:
                return [m.get("id", "") for m in r.json().get("data", [])]
        except Exception: pass
        return []

    # Token estimation
    @staticmethod
    def estimate_tokens(text: str) -> int:
        if not text: return 0
        return max(1, int(len(text) / CHARS_PER_TOKEN))

    def set_max_context(self, tokens: int):
        self._max_context_tokens = max(1024, min(tokens, 32768))

    # Internal helpers
    def _post(self, payload: dict, stream: bool = False) -> requests.Response:
        return requests.post(
            f"{self._base}/chat/completions",
            json=payload,
            timeout=LLM_TIMEOUT,
            stream=stream,
        )

    def _post_with_retry(self, payload: dict, stream: bool = False) -> requests.Response:
        """Send request with exponential backoff retry logic."""
        last_err = None
        last_status_code = None
        
        for attempt in range(MAX_RETRIES):
            try:
                r = self._post(payload, stream)
                
                # Check for rate limiting (429)
                if r.status_code == 429:
                    retry_after = int(r.headers.get('Retry-After', 5))
                    wait_time = min(retry_after, MAX_BACKOFF)
                    print(f"[LLM] Rate limited. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    last_status_code = 429
                    continue
                
                # Server errors (5xx) - retry with backoff
                if r.status_code >= 500:
                    last_status_code = r.status_code
                    backoff = min(INITIAL_BACKOFF * (BACKOFF_MULTIPLIER ** attempt), MAX_BACKOFF)
                    print(f"[LLM] Server error {r.status_code}. Retrying in {backoff:.1f}s...")
                    time.sleep(backoff)
                    continue
                
                # Success or client error (4xx except 429) - don't retry
                r.raise_for_status()
                return r
                
            except requests.exceptions.Timeout:
                last_err = "timeout"
                backoff = min(INITIAL_BACKOFF * (BACKOFF_MULTIPLIER ** attempt), MAX_BACKOFF)
                print(f"[LLM] Request timeout. Retrying in {backoff:.1f}s... (attempt {attempt + 1}/{MAX_RETRIES})")
                time.sleep(backoff)
                
            except requests.exceptions.ConnectionError:
                last_err = "connection_error"
                backoff = min(INITIAL_BACKOFF * (BACKOFF_MULTIPLIER ** attempt), MAX_BACKOFF)
                print(f"[LLM] Connection error. Retrying in {backoff:.1f}s... (attempt {attempt + 1}/{MAX_RETRIES})")
                time.sleep(backoff)
                
            except requests.exceptions.HTTPError as e:
                # Client errors (4xx) - generally don't retry
                if e.response is not None:
                    if e.response.status_code == 429:
                        # Already handled above, but just in case
                        last_err = "rate_limit"
                        time.sleep(5)
                        continue
                    elif e.response.status_code < 500:
                        # Client error - don't retry
                        raise
                last_err = str(e)
                backoff = min(INITIAL_BACKOFF * (BACKOFF_MULTIPLIER ** attempt), MAX_BACKOFF)
                time.sleep(backoff)
        
        # All retries exhausted
        if last_status_code == 429:
            raise LLMRateLimitError("LLM rate limit exceeded. Please wait before making more requests.")
        elif last_err == "timeout":
            raise LLMTimeoutError(f"LLM request timed out after {MAX_RETRIES} attempts.")
        else:
            raise LLMConnectionError(f"LLM request failed after {MAX_RETRIES} attempts: {last_err}")

    @staticmethod
    def _sanitize_messages(messages: list) -> list:
        sanitized = []
        found_user = False
        for msg in messages:
            if msg.get("role") == "user":
                found_user = True
            if msg.get("role") == "assistant" and not found_user:
                continue
            sanitized.append(msg)
        if not found_user and sanitized:
            sanitized.insert(0, {"role": "user", "content": "Hello"})
        return sanitized

    def _build_context_messages(self, system_prompt: str, messages: list) -> list:
        """Build messages with token-aware context window management.
        
        Some models (e.g. certain Qwen variants) have broken Jinja templates
        that error on system messages. We prepend the system prompt to the
        first user message instead of using a separate system role.
        """
        system_tokens = self.estimate_tokens(system_prompt)
        available = self._max_context_tokens - system_tokens - 256

        # Work backwards to fit as much context as possible
        result = []
        used_tokens = 0
        for msg in reversed(messages):
            content = msg.get("content", "")
            msg_tokens = self.estimate_tokens(content)
            if used_tokens + msg_tokens > available:
                remaining = available - used_tokens
                if remaining > 50:
                    max_chars = int(remaining * CHARS_PER_TOKEN)
                    truncated = content[-max_chars:]
                    result.insert(0, {"role": msg["role"], "content": f"[...truncated...]\n{truncated}"})
                break
            result.insert(0, msg)
            used_tokens += msg_tokens

        # Inject system prompt into first user message instead of separate system role
        if result:
            if result[0].get("role") == "user":
                result[0] = {
                    "role": "user",
                    "content": f"{system_prompt}\n\n---\n\n{result[0]['content']}",
                }
            else:
                # First message is assistant — prepend a user message with system prompt
                result.insert(0, {"role": "user", "content": system_prompt})
        else:
            result = [{"role": "user", "content": system_prompt}]

        return result

    def _simple(self, model: str, system: str, user: str, temperature: float = 0.7) -> str:
        payload = {
            "model":       model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        }
        r = self._post_with_retry(payload)
        data = r.json()
        if "choices" not in data or not data["choices"]:
            raise ValueError(f"LLM returned no choices: {data}")
        return data["choices"][0]["message"]["content"].strip()

    # Intent Classification
    _OFFLINE_PATTERNS = [
        (r"^(hi|hello|hey|howdy|yo)\b",                         "chat",        0.99),
        (r"\bopen\s+\w+\b",                                     "command",     0.90),
        (r"\bplay\s+.+\b",                                      "music",       0.92),
        (r"^https?://",                                         "browser",     0.99),
        (r"\bwhat (time|date) is it\b",                         "time",        0.99),
        (r"\b(show|list) (apps|installed)\b",                   "show_apps",   0.95),
        (r"\b(ram|memory|cpu|disk|port|service|startup)\s*(usage|info|space|list)?\b", "powershell", 0.88),
        (r"\b(search|find|look up)\s+.+\s+on\s+(youtube|github|arxiv|stackoverflow|huggingface|pypi|npm|reddit)\b", "smart_search", 0.95),
        (r"\bwho (is|was)\b|\bwhat is (the|a|an) \w+\b",       "wikipedia",   0.75),
        (r"\bgenerate.*(image|picture|photo|art)\b",            "image_gen",   0.93),
        (r"\bexplain.*(code|function|class|error|snippet)\b",   "explain",     0.91),
        # Fabric patterns
        (r"^/fabric\b",                                         "fabric",      0.99),
        (r"\bfabric\s+\w+",                                     "fabric",      0.90),
        (r"\b(extract wisdom|extract ideas|extract insights)\b","fabric",      0.92),
        (r"\b(summarize|summarise) (this|it|the following)\b",  "fabric",      0.85),
        (r"\b(improve (my |this |the )?writing|rewrite (this|it))\b", "fabric", 0.83),
        (r"\banalyze (claims|debate|paper|prose)\b",            "fabric",      0.88),
        (r"\bcreate (quiz|outline|tags|threat scenarios)\b",    "fabric",      0.86),
        (r"\b(rate|score) (this|the|my) (content|writing|text)\b", "fabric",  0.84),
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
            raw = re.sub(r"```json|```", "", raw).strip()
            result = json.loads(raw)
            result["source"] = "llm"
            return result
        except Exception as e: return {"mode": "chat", "confidence": 0.5, "source": "fallback", "error": str(e)}

    # Chat (streaming) with token-aware context
    def chat_stream(self, messages: list, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        sys_prompt = system_prompt or SYSTEM_PROMPT
        context_msgs = self._build_context_messages(sys_prompt, messages)
        payload = {
            "model":       self._chat_model,
            "temperature": LLM_CHAT_TEMPERATURE,
            "stream":      True,
            "messages":    context_msgs,
        }
        try:
            r = self._post_with_retry(payload, stream=True)
            for line in r.iter_lines():
                if not line: continue
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]": break
                    try:
                        chunk = json.loads(data)
                        choices = chunk.get("choices")
                        if not choices: continue
                        delta = choices[0]["delta"].get("content", "")
                        if delta: yield delta
                    except (json.JSONDecodeError, KeyError, IndexError): continue
        except LLMRateLimitError as e:
            yield f"\n\n[LLM Error: {e}]"
        except LLMTimeoutError as e:
            yield f"\n\n[LLM Error: {e}]"
        except LLMConnectionError as e:
            yield f"\n\n[LLM Error: {e}]"
        except requests.exceptions.ConnectionError:
            yield "\n\n[LLM Error: Cannot connect to LM Studio. Make sure it's running.]"
        except requests.exceptions.Timeout:
            yield "\n\n[LLM Error: Request timed out. The model may be overloaded.]"
        except Exception as e:
            yield f"\n\n[LLM Error: {e}]"

    def chat(self, messages: list, system_prompt: Optional[str] = None) -> str:
        sys_prompt = system_prompt or SYSTEM_PROMPT
        context_msgs = self._build_context_messages(sys_prompt, messages)
        payload = {
            "model":       self._chat_model,
            "temperature": LLM_CHAT_TEMPERATURE,
            "messages":    context_msgs,
        }
        try:
            r = self._post_with_retry(payload)
            data = r.json()
            if "choices" not in data or not data["choices"]:
                return "[LLM Error: Response contained no choices]"
            return data["choices"][0]["message"]["content"].strip()
        except LLMRateLimitError as e:
            return f"[LLM Error: {e}]"
        except LLMTimeoutError as e:
            return f"[LLM Error: {e}]"
        except LLMConnectionError as e:
            return f"[LLM Error: {e}]"
        except requests.exceptions.ConnectionError:
            return "[LLM Error: Cannot connect to LM Studio. Make sure it's running.]"
        except requests.exceptions.Timeout:
            return "[LLM Error: Request timed out. The model may be overloaded.]"
        except Exception as e:
            return f"[LLM Error: {e}]"

    def chat_with_tools(self, messages: list, tools: list, system_prompt: Optional[str] = None) -> dict:
        sys_prompt = system_prompt or SYSTEM_PROMPT
        context_msgs = self._build_context_messages(sys_prompt, messages)
        payload = {
            "model":       self._chat_model,
            "temperature": LLM_CHAT_TEMPERATURE,
            "messages":    context_msgs,
            "tools":       tools,
            "tool_choice": "auto"
        }
        try:
            r = self._post_with_retry(payload)
            data = r.json()
            if "choices" not in data or not data["choices"]:
                return {"content": "[LLM Error: Response contained no choices]", "tool_calls": []}
            message = data["choices"][0]["message"]
            return {
                "content": message.get("content", ""),
                "tool_calls": message.get("tool_calls", [])
            }
        except LLMRateLimitError as e:
            return {"content": f"[LLM Error: {e}]", "tool_calls": []}
        except LLMTimeoutError as e:
            return {"content": f"[LLM Error: {e}]", "tool_calls": []}
        except LLMConnectionError as e:
            return {"content": f"[LLM Error: {e}]", "tool_calls": []}
        except Exception as e:
            return {"content": f"[LLM Error: {e}]", "tool_calls": []}

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

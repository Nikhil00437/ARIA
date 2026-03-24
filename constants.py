# LM Studio
LM_STUDIO_BASE_URL   = "http://localhost:1234/v1"
CHAT_MODEL           = "qwen3-vl-8b-instruct"
CLASSIFIER_MODEL     = "qwen3-vl-8b-instruct"   # swap for smaller fast model if available
LLM_TIMEOUT          = 30
LLM_CHAT_TEMPERATURE = 0.7
LLM_CLASS_TEMPERATURE= 0.1
# MongoDB
MONGO_URI    = "mongodb://localhost:27017"
MONGO_DB     = "aria_db"
COL_SESSIONS = "sessions"
COL_COMMANDS = "command_logs"
COL_SELFMOD  = "selfmod_ledger"
COL_PROFILE  = "behavioral_profile"
# Themes
THEMES = {
    "cyber": {
        "bg":        "#0a0f0a",
        "bg2":       "#0d1a0d",
        "bg3":       "#112211",
        "accent":    "#00ff88",
        "accent2":   "#00cc66",
        "text":      "#ccffcc",
        "text2":     "#88bb88",
        "dim":       "#446644",
        "border":    "#1a4a1a",
        "sidebar":   "#0d1a0d",
        "chat_bg":   "#0a0f0a",
        "term_bg":   "#050a05",
        "term_text": "#00ff88",
        "warning":   "#ffaa00",
        "error":     "#ff4444",
        "success":   "#00ff88",
        "user_msg":  "#0d2a0d",
        "ai_msg":    "#0a1a0a",
    },
    "minimal": {
        "bg":        "#f5f7fa",
        "bg2":       "#eef1f5",
        "bg3":       "#e5eaf0",
        "accent":    "#2563eb",
        "accent2":   "#1d4ed8",
        "text":      "#1e293b",
        "text2":     "#64748b",
        "dim":       "#94a3b8",
        "border":    "#cbd5e1",
        "sidebar":   "#eef1f5",
        "chat_bg":   "#f5f7fa",
        "term_bg":   "#1e293b",
        "term_text": "#f5f7fa",
        "warning":   "#d97706",
        "error":     "#dc2626",
        "success":   "#16a34a",
        "user_msg":  "#dbeafe",
        "ai_msg":    "#f1f5f9",
    },
    "classic": {
        "bg":        "#1a1a1a",
        "bg2":       "#222222",
        "bg3":       "#2a2a2a",
        "accent":    "#aaaaaa",
        "accent2":   "#888888",
        "text":      "#dddddd",
        "text2":     "#888888",
        "dim":       "#555555",
        "border":    "#333333",
        "sidebar":   "#222222",
        "chat_bg":   "#1a1a1a",
        "term_bg":   "#111111",
        "term_text": "#00ff00",
        "warning":   "#ccaa44",
        "error":     "#cc4444",
        "success":   "#44aa44",
        "user_msg":  "#2a2a2a",
        "ai_msg":    "#1e1e1e",
    },
}
DEFAULT_THEME = "cyber"
# System Prompt
SYSTEM_PROMPT = """You are ARIA — Advanced Runtime Intelligence Assistant. You are a local, private, fast AI assistant running entirely on-device.

Your personality: precise, helpful, slightly dry. You never hallucinate — if unsure, say so.
You assist with system tasks, information retrieval, file operations, code explanation, and general Q&A.
Keep responses concise unless the user asks for detail. Format with markdown when it aids clarity.
Never suggest cloud services or external APIs — you are local-first by design."""
# Intent Classifier Prompt
INTENT_CLASSIFIER_PROMPT = """Classify the user message into exactly one intent mode.

Respond ONLY with valid JSON, no explanation, no markdown:
{"mode": "<MODE>", "confidence": <0.0-1.0>}

Modes:
- chat          : general conversation or question
- command       : run a system command or app
- wikipedia     : factual lookup / "what is X"
- browser       : open a URL or website
- music         : play music
- search        : search the web or a platform
- show_apps     : list installed apps
- time          : current time or date
- quick_open    : open a file or folder
- smart_search  : search a specific site (youtube, github, arxiv, etc)
- powershell    : system info query (RAM, CPU, disk, services, etc)
- explain       : explain code or a concept in detail
- history       : show command history
- rerun         : re-execute a previous command
- image_gen     : generate an image

User message: {message}"""
# Summarize Prompt
SUMMARIZE_PROMPT = """Summarize the following output in 2-4 concise bullet points. Be direct, no preamble:

{output}"""
# Explain Prompt
EXPLAIN_PROMPT = """Explain the following clearly and concisely. Use markdown. Target a developer audience:

{content}"""
# Smart URL Generation Prompt
URL_GEN_PROMPT = """Generate the best search/browse URL for this request. Return ONLY the URL, nothing else.

Request: {query}

Rules:
- Prefer direct URLs over search pages when the target is obvious
- Use HTTPS always
- No markdown, no explanation"""
# Behavioral Inference Prompt
BEHAVIORAL_INFERENCE_PROMPT = """Analyze this interaction history and identify behavioral patterns that suggest the user wants ARIA configured differently.

History (recent {n} interactions):
{history}

Identify up to 5 concrete patterns. For each, respond ONLY with valid JSON array:
[
  {{
    "pattern": "<short description>",
    "evidence": "<what in history supports this>",
    "proposed_change": "<specific config param and new value>",
    "param_key": "<exact key from MODIFIABLE_PARAMS>",
    "param_value": <new value>,
    "confidence": <0.0-1.0>,
    "reversible": true
  }}
]

MODIFIABLE_PARAMS available:
- output_mode: "verbose" | "summary"
- smart_search_threshold: float 0.4-0.9
- tts_enabled: bool
- silent_mode: bool  
- default_theme: "cyber" | "minimal" | "classic"
- suggestion_count: int 3-8
- custom_shortcuts: dict of alias->app/url
- preferred_search_sites: list of site names
- confirmation_verbosity: "full" | "brief"
- response_length_preference: "concise" | "detailed"

Only return the JSON array. No explanation."""
# Modification Proposal Prompt
PROPOSAL_GENERATION_PROMPT = """Given this behavioral pattern, write a clear, human-readable modification proposal for the user to approve or reject.

Pattern: {pattern}
Proposed change: {proposed_change}
Confidence: {confidence}

Write 2 sentences max. First sentence: what ARIA noticed. Second: what it wants to change. Be specific with values.
No markdown, no bullet points, plain text."""
# URL Search Templates
SEARCH_TEMPLATES = {
    "google":       "https://www.google.com/search?q={q}",
    "youtube":      "https://www.youtube.com/results?search_query={q}",
    "github":       "https://github.com/search?q={q}&type=repositories",
    "stackoverflow": "https://stackoverflow.com/search?q={q}",
    "huggingface":  "https://huggingface.co/search/full-text?q={q}",
    "arxiv":        "https://arxiv.org/search/?query={q}&searchtype=all",
    "pypi":         "https://pypi.org/search/?q={q}",
    "npm":          "https://www.npmjs.com/search?q={q}",
    "wikipedia":    "https://en.wikipedia.org/wiki/Special:Search?search={q}",
    "reddit":       "https://www.reddit.com/search/?q={q}",
    "twitter":      "https://twitter.com/search?q={q}",
    "linkedin":     "https://www.linkedin.com/search/results/all/?keywords={q}",
    "amazon":       "https://www.amazon.in/s?k={q}",
    "flipkart":     "https://www.flipkart.com/search?q={q}",
    "maps":         "https://www.google.com/maps/search/{q}",
    "imdb":         "https://www.imdb.com/find?q={q}",
    "docs":         "https://docs.python.org/3/search.html?q={q}",
    "mdn":          "https://developer.mozilla.org/en-US/search?q={q}",
    "dockerhub":    "https://hub.docker.com/search?q={q}",
    "kaggle":       "https://www.kaggle.com/search?q={q}",
}
SITE_ALIASES = {
    "yt": "youtube", "gh": "github", "so": "stackoverflow",
    "hf": "huggingface", "wiki": "wikipedia", "gmap": "maps",
    "fk": "flipkart", "amz": "amazon",
}
# NL → PowerShell translation table
POWERSHELL_PATTERNS = {
    r"(ram|memory) usage":       "Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 10 Name, @{N='RAM_MB';E={[math]::Round($_.WorkingSet64/1MB,1)}}",
    r"cpu usage":                "Get-WmiObject Win32_Processor | Select-Object Name, LoadPercentage",
    r"disk (space|usage)":       "Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{N='Used_GB';E={[math]::Round($_.Used/1GB,2)}}, @{N='Free_GB';E={[math]::Round($_.Free/1GB,2)}}",
    r"running (services|service)": "Get-Service | Where-Object {$_.Status -eq 'Running'} | Select-Object Name, DisplayName",
    r"open ports":               "netstat -ano | findstr LISTENING",
    r"startup (apps|programs)":  "Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location",
    r"(logged.in|current) users": "query user",
    r"wifi passwords?":          "netsh wlan show profiles | Select-String 'All User Profile' | ForEach-Object { $p = ($_ -split ':')[1].Trim(); netsh wlan show profile name=$p key=clear | Select-String 'Key Content' }",
    r"dns (flush|cache)":        "Clear-DnsClientCache; Write-Host 'DNS cache flushed'",
    r"installed (apps|software)": "Get-WmiObject Win32_Product | Select-Object Name, Version | Sort-Object Name",
    r"(ip|network) (info|address)": "ipconfig /all",
    r"(system|pc) info":         "systeminfo | Select-String 'OS|Memory|Processor'",
    r"environment variables":    "Get-ChildItem Env: | Sort-Object Name",
    r"top processes":            "Get-Process | Sort-Object CPU -Descending | Select-Object -First 15 Name, CPU, Id",
}
# Blocked Command Patterns
BLOCKED_PATTERNS = [
    r"format\s+[a-zA-Z]:",
    r"rm\s+-rf\s+/",
    r"del\s+/[fqs]+\s+.*system32",
    r"reg\s+delete.*\\system",
    r"bcdedit",
    r"diskpart",
    r"cipher\s+/w",
    r"net\s+user\s+administrator\s+/delete",
    r"shutdown\s+/r\s+/o",
]
# Confirmation-Required Patterns
CONFIRM_PATTERNS = [
    r"\bdel\b",
    r"\brmdir\b",
    r"\btaskkill\b",
    r"\bshutdown\b",
    r"\brestart\b",
    r"\bformat\b",
    r"\bnetsh\s+reset\b",
    r"stop-process",
    r"remove-item",
]
# Suggestion Map
SUGGESTIONS = {
    "chat":        ["Tell me something interesting", "Explain quantum computing", "What can you do?"],
    "command":     ["Open Task Manager", "List running processes", "Check disk space"],
    "powershell":  ["Show RAM usage", "List running services", "Show open ports"],
    "search":      ["Search GitHub for FastAPI", "Find Python tutorials on YouTube", "Search arXiv for LLM papers"],
    "image_gen":   ["Generate a cyberpunk city", "Create a minimalist logo", "Draw a futuristic robot"],
}
# Self-Modification Boundary — LOCKED params
SELFMOD_LOCKED_PARAMS = {
    "blocked_patterns",
    "confirm_patterns",
    "system_prompt_safety",
    "executor_security",
    "mongo_uri",
    "lm_studio_base_url",
}
# Health Monitor
HEALTH_CHECK_INTERVAL_MS = 300_000   # 5 minutes
HEALTH_RAM_THRESHOLD_MB  = 500       # alert if any process exceeds this
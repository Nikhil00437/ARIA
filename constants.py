# LM Studio
LM_STUDIO_BASE_URL   = "http://localhost:1234/v1"
CHAT_MODEL           = "qwen3.5-9b-uncensored-hauhaucs-aggressive"
CLASSIFIER_MODEL     = "intent"
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
        "bg":        "#07090f",
        "bg2":       "#0b1018",
        "bg3":       "#0f1622",
        "accent":    "#00e5cc",     # electric teal
        "accent2":   "#6366f1",     # indigo
        "text":      "#dce6f4",
        "text2":     "#7a96b0",
        "dim":       "#2e4560",
        "border":    "#13243a",
        "sidebar":   "#050710",
        "chat_bg":   "#0a0e1a",
        "term_bg":   "#03060c",
        "term_text": "#00e5cc",
        "warning":   "#f59e0b",
        "error":     "#ef4444",
        "success":   "#00e5cc",
        "user_msg":  "#0b1d34",
        "ai_msg":    "#090e1c",
        "chat_page":     "#080d1a",
        "terminal_page": "#060c14",
        "timeline_page": "#0c0a1e",
        "warnings_page": "#140a12",
        "selfmod_page":  "#100818",
        "patterns_page": "#081018",
        "sidebar_chat":     "#070d1a",
        "sidebar_terminal": "#060c14",
        "sidebar_timeline": "#0a0a1e",
        "sidebar_warnings": "#140a10",
        "sidebar_selfmod":  "#0e0818",
        "sidebar_patterns": "#061018",
        "glass_chat":     "#0e1628",
        "glass_terminal": "#0c1420",
        "glass_timeline": "#12142a",
        "glass_warnings": "#1a0e18",
        "glass_selfmod":  "#160c20",
        "glass_patterns": "#0c1822",
    },
    "minimal": {
        "bg":        "#f9fbfd",
        "bg2":       "#f0f4f8",
        "bg3":       "#e6ecf2",
        "accent":    "#0284c7",     # sky blue
        "accent2":   "#7c3aed",     # violet
        "text":      "#0c1a2e",
        "text2":     "#445566",
        "dim":       "#94a3b8",
        "border":    "#dde4ee",
        "sidebar":   "#eef2f7",
        "chat_bg":   "#ffffff",
        "term_bg":   "#0c1a2e",
        "term_text": "#e2f0ff",
        "warning":   "#d97706",
        "error":     "#dc2626",
        "success":   "#059669",
        "user_msg":  "#dbeafe",
        "ai_msg":    "#f8fafc",
        "chat_page":     "#f7fafd",
        "terminal_page": "#f5f8fc",
        "timeline_page": "#f8f7fb",
        "warnings_page": "#fbf7f8",
        "selfmod_page":  "#f9f5fb",
        "patterns_page": "#f6f9fb",
        "sidebar_chat":     "#eaf0f8",
        "sidebar_terminal": "#e7eef6",
        "sidebar_timeline": "#ece8f4",
        "sidebar_warnings": "#f2e8ec",
        "sidebar_selfmod":  "#f0e6f6",
        "sidebar_patterns": "#e8f0f6",
        "glass_chat":     "#eef4fa",
        "glass_terminal": "#ebf0f6",
        "glass_timeline": "#f0ecf6",
        "glass_warnings": "#f6eef0",
        "glass_selfmod":  "#f2eaf8",
        "glass_patterns": "#eaf2f8",
    },
    "classic": {
        "bg":        "#101010",
        "bg2":       "#181818",
        "bg3":       "#202020",
        "accent":    "#b0b0b0",     # silver
        "accent2":   "#707070",
        "text":      "#e4e4e4",
        "text2":     "#909090",
        "dim":       "#404040",
        "border":    "#282828",
        "sidebar":   "#0c0c0c",
        "chat_bg":   "#141414",
        "term_bg":   "#080808",
        "term_text": "#00ff41",
        "warning":   "#c8a000",
        "error":     "#c84040",
        "success":   "#40c840",
        "user_msg":  "#1c1c1c",
        "ai_msg":    "#121212",
        "chat_page":     "#111311",
        "terminal_page": "#0e100e",
        "timeline_page": "#121012",
        "warnings_page": "#131010",
        "selfmod_page":  "#101014",
        "patterns_page": "#0e1210",
        "sidebar_chat":     "#0e0e0e",
        "sidebar_terminal": "#0c0e0c",
        "sidebar_timeline": "#100e10",
        "sidebar_warnings": "#110e0e",
        "sidebar_selfmod":  "#0e0e12",
        "sidebar_patterns": "#0c100e",
        "glass_chat":     "#161616",
        "glass_terminal": "#141614",
        "glass_timeline": "#181418",
        "glass_warnings": "#191414",
        "glass_selfmod":  "#14141a",
        "glass_patterns": "#121614",
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
- fabric        : run a Fabric AI pattern (summarize, extract_wisdom, analyze_claims, etc)

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
    "google":        "https://www.google.com/search?q={q}",
    "youtube":       "https://www.youtube.com/results?search_query={q}",
    "github":        "https://github.com/search?q={q}&type=repositories",
    "stackoverflow": "https://stackoverflow.com/search?q={q}",
    "huggingface":   "https://huggingface.co/search/full-text?q={q}",
    "arxiv":         "https://arxiv.org/search/?query={q}&searchtype=all",
    "pypi":          "https://pypi.org/search/?q={q}",
    "npm":           "https://www.npmjs.com/search?q={q}",
    "wikipedia":     "https://en.wikipedia.org/wiki/Special:Search?search={q}",
    "reddit":        "https://www.reddit.com/search/?q={q}",
    "twitter":       "https://twitter.com/search?q={q}",
    "linkedin":      "https://www.linkedin.com/search/results/all/?keywords={q}",
    "amazon":        "https://www.amazon.in/s?k={q}",
    "flipkart":      "https://www.flipkart.com/search?q={q}",
    "maps":          "https://www.google.com/maps/search/{q}",
    "imdb":          "https://www.imdb.com/find?q={q}",
    "docs":          "https://docs.python.org/3/search.html?q={q}",
    "mdn":           "https://developer.mozilla.org/en-US/search?q={q}",
    "dockerhub":     "https://hub.docker.com/search?q={q}",
    "kaggle":        "https://www.kaggle.com/search?q={q}",
}

SITE_ALIASES = {
    "yt": "youtube", "gh": "github", "so": "stackoverflow",
    "hf": "huggingface", "wiki": "wikipedia", "gmap": "maps",
    "fk": "flipkart", "amz": "amazon",
}

# NL → PowerShell translation table
POWERSHELL_PATTERNS = {
    r"(ram|memory) usage":         "Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 10 Name, @{N='RAM_MB';E={[math]::Round($_.WorkingSet64/1MB,1)}}",
    r"cpu usage":                  "Get-WmiObject Win32_Processor | Select-Object Name, LoadPercentage",
    r"disk (space|usage)":         "Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{N='Used_GB';E={[math]::Round($_.Used/1GB,2)}}, @{N='Free_GB';E={[math]::Round($_.Free/1GB,2)}}",
    r"running (services|service)": "Get-Service | Where-Object {$_.Status -eq 'Running'} | Select-Object Name, DisplayName",
    r"open ports":                 "netstat -ano | findstr LISTENING",
    r"startup (apps|programs)":    "Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location",
    r"(logged.in|current) users":  "query user",
    r"wifi passwords?":            "netsh wlan show profiles | Select-String 'All User Profile' | ForEach-Object { $p = ($_ -split ':')[1].Trim(); netsh wlan show profile name=$p key=clear | Select-String 'Key Content' }",
    r"dns (flush|cache)":          "Clear-DnsClientCache; Write-Host 'DNS cache flushed'",
    r"installed (apps|software)":  "Get-WmiObject Win32_Product | Select-Object Name, Version | Sort-Object Name",
    r"(ip|network) (info|address)":"ipconfig /all",
    r"(system|pc) info":           "systeminfo | Select-String 'OS|Memory|Processor'",
    r"environment variables":      "Get-ChildItem Env: | Sort-Object Name",
    r"top processes":              "Get-Process | Sort-Object CPU -Descending | Select-Object -First 15 Name, CPU, Id",
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

# Suggestion Map — large pools, randomly sampled each session
SUGGESTION_POOLS = {
    "chat": [
        "Tell me something interesting",
        "Explain quantum computing like I'm five",
        "What's a mind-blowing fact?",
        "What can you do?",
        "Tell me a short story",
        "What's the coolest tech trend right now?",
        "Explain black holes to me",
        "Give me a random fun fact",
        "What would happen if the internet stopped?",
        "Tell me about the future of AI",
        "What's a skill I can learn in a week?",
        "Explain how dreams work",
        "What's the most underrated invention?",
        "Tell me something weird about space",
        "What's a paradox that breaks your brain?",
        "Explain blockchain simply",
        "What would aliens think of Earth?",
        "Tell me about a historical mystery",
        "What's the meaning of life according to science?",
        "Explain how consciousness works",
    ],
    "command": [
        "Open Task Manager",
        "List running processes",
        "Check disk space",
        "Show my IP address",
        "List all installed programs",
        "Check system uptime",
        "Show network adapters",
        "List USB devices connected",
        "Check Windows version",
        "Show battery health",
        "List startup programs",
        "Check for pending updates",
        "Show clipboard history",
        "List environment variables",
        "Check screen resolution",
    ],
    "powershell": [
        "Show RAM usage",
        "List running services",
        "Show open ports",
        "Get CPU temperature",
        "Show disk health status",
        "List recent event log errors",
        "Show network latency",
        "Get GPU information",
        "List scheduled tasks",
        "Show PowerShell version and modules",
        "Check DNS configuration",
        "Show active network connections",
        "List all user accounts",
        "Show Windows feature status",
        "Get system temperature sensors",
    ],
    "search": [
        "Search GitHub for FastAPI",
        "Find Python tutorials on YouTube",
        "Search arXiv for LLM papers",
        "Find the best VS Code extensions",
        "Search for latest AI breakthroughs",
        "Find open-source alternatives to popular apps",
        "Search for cybersecurity news today",
        "Find trending repositories on GitHub",
        "Search for machine learning datasets",
        "Find the best programming podcasts",
        "Search for web development trends 2026",
        "Find free cloud hosting options",
        "Search for Rust programming resources",
        "Find coding challenge platforms",
        "Search for latest cybersecurity threats",
    ],
    "image_gen": [
        "Generate a cyberpunk city",
        "Create a minimalist logo",
        "Draw a futuristic robot",
        "Generate a neon-lit alleyway",
        "Create an abstract data visualization",
        "Draw a steampunk airship",
        "Generate a synthwave sunset",
        "Create a pixel art character",
        "Draw a crystal cave with bioluminescence",
        "Generate a retro-futuristic spaceship",
        "Create an isometric room design",
        "Draw a magical library",
        "Generate a glitch art portrait",
        "Create a vaporwave aesthetic scene",
        "Draw a floating island in the clouds",
    ],
}

# Legacy SUGGESTIONS dict (kept for backwards compatibility, uses first items from pools)
SUGGESTIONS = {mode: pool[:5] for mode, pool in SUGGESTION_POOLS.items()}

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
HEALTH_CHECK_INTERVAL_MS = 300_000
HEALTH_RAM_THRESHOLD_MB  = 500

# Fabric Integration
# Quick pattern aliases — short keywords → full Fabric pattern names
FABRIC_QUICK_PATTERNS: dict = {
    "summarize":     "summarize",
    "summary":       "summarize",
    "wisdom":        "extract_wisdom",
    "ideas":         "extract_ideas",
    "insights":      "extract_insights",
    "outline":       "create_outline",
    "improve":       "improve_writing",
    "claims":        "analyze_claims",
    "quiz":          "create_quiz",
    "tags":          "create_tags",
    "rate":          "rate_content",
    "explain":       "explain_code",
    "meeting":       "summarize_meeting",
    "paper":         "analyze_paper",
    "threat":        "create_threat_scenarios",
    "tldr":          "create_5_sentence_summary",
    "micro":         "create_micro_summary",
    "essay":         "write_essay",
    "rewrite":       "rewrite_take",
    "analyze":       "analyze_prose",
    "chapters":      "create_video_chapters",
    "mermaid":       "create_mermaid_visualization",
    "markmap":       "create_markmap_visualization",
}

# Fabric binary search paths (tried in order after PATH lookup)
FABRIC_SEARCH_PATHS: list[str] = [
    "~/.local/bin/fabric",
    "~/go/bin/fabric",
    "~/.fabric/fabric",
    r"C:\Users\%USERNAME%\go\bin\fabric.exe",
    r"C:\Program Files\fabric\fabric.exe",
]
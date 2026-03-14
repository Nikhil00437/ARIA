THEMES = {
    "cyber": {
        "bg":        "#0a0a0a",
        "sidebar":   "#0f0f0f",
        "accent":    "#00e676",
        "accent2":   "#00c853",
        "text":      "#d0d0d0",
        "dim":       "#5a5a5a",
        "border":    "#1a1a1a",
        "chat_bg":   "#080808",
        "term_bg":   "#060606",
        "term_text": "#7fbf7f",
    },
    "minimal": {
        "bg":        "#f5f5f5",
        "sidebar":   "#ffffff",
        "accent":    "#1976d2",
        "accent2":   "#1565c0",
        "text":      "#212121",
        "dim":       "#9e9e9e",
        "border":    "#e0e0e0",
        "chat_bg":   "#fafafa",
        "term_bg":   "#263238",
        "term_text": "#80cbc4",
    },
    "classic": {
        "bg":        "#0c0c0c",
        "sidebar":   "#0c0c0c",
        "accent":    "#c8c8c8",
        "accent2":   "#a0a0a0",
        "text":      "#c8c8c8",
        "dim":       "#555555",
        "border":    "#333333",
        "chat_bg":   "#0c0c0c",
        "term_bg":   "#0c0c0c",
        "term_text": "#c8c8c8",
    },
}

SYSTEM_PROMPT = """You are ARIA — an Advanced Runtime Intelligence Assistant running on Windows.
You can chat, execute commands, search Wikipedia, open websites, play music, search files, and more.

CAPABILITIES:
- File operations: dir, copy, move, del, mkdir
- App launching: start app.exe (auto-resolves paths)
- System info: tasklist, systeminfo, ipconfig, time
- Task management: taskkill /im process.exe
- Web search: Wikipedia or browser
- Scripting: Run .bat, .ps1, .py files
- Music player: Find and play .mp3 files
- File search: Search by extension (.pdf, .docx, .py, etc.)
- App listing: Show all installed applications
- Quick access: YouTube, Google, Stack Overflow, Spotify, VS Code, CMD
- PowerShell: Natural language → PowerShell commands
- Explain: Explain any command or output in detail
- Image Generation: Can generate image using stablediffusion, torch, transformer, pillow

COMMAND FORMAT:
When you need to execute a Windows command, respond with JSON:
{"mode": "command", "command": "your windows command here", "explanation": "brief explanation"}

For web searches:
{"mode": "wikipedia", "query": "search term", "explanation": "why searching"}

For opening URLs:
{"mode": "browser", "url": "https://...", "explanation": "why opening"}

For playing music:
{"mode": "music", "action": "play", "explanation": "finding and playing music"}

For file search:
{"mode": "search", "extension": "mp3", "explanation": "searching for files"}

For showing apps:
{"mode": "show_apps", "explanation": "listing installed applications"}

For normal chat:
{"mode": "chat", "message": "your response", "explanation": ""}

For image generation:
{"mode": "image_gen", "message": "prompt", "explanation":""}

RULES:
- Windows commands only (no Linux: ls, grep, etc.)
- Use %USERPROFILE% for user home
- Be concise and helpful
- Default to chat mode when unsure
- Respond in natural language ONLY
- NEVER output JSON
"""

INTENT_CLASSIFIER_PROMPT = """You are an intent classifier for ARIA Windows assistant.

Analyze the user's message and determine the action:
- CHAT: explanation, discussion, questions
- COMMAND: Windows system action (open, run, list, kill, search files)
- WIKIPEDIA: looking up information/facts
- BROWSER: opening a website
- MUSIC: play music from device
- SEARCH: search for files by extension
- SHOW_APPS: list installed applications
- TIME: get current time
- QUICK_OPEN: YouTube, Google, Stack Overflow, Spotify, VS Code, CMD (homepage only, no search query)
- SMART_SEARCH: open a site AND search for something within it (e.g. "search youtube for X", "find X on github", "look up X on stackoverflow", "open github username")
- POWERSHELL: natural language system queries (memory, services, ports, etc.)
- EXPLAIN: explain a command or system output
- HISTORY: show command history
- RERUN: re-run a previous command
- IMAGE_GEN: image generation prompt

Respond with ONLY valid JSON:
{
  "mode": "chat"|"command"|"wikipedia"|"image_gen"|"browser"|"music"|"search"|"show_apps"|"time"|"quick_open"|"smart_search"|"powershell"|"explain"|"history"|"rerun",
  "confidence": 0.0-1.0,
  "reason": "why this mode",
  "action": "specific action or null"
}

Examples:
"open notepad" → {"mode": "command", "confidence": 0.95, "reason": "launch app", "action": "start notepad.exe"}
"who is Einstein" → {"mode": "wikipedia", "confidence": 0.90, "reason": "factual lookup", "action": "Albert Einstein"}
"open youtube" → {"mode": "quick_open", "confidence": 0.95, "reason": "quick link, no search query", "action": "youtube"}
"search youtube for network chuck" → {"mode": "smart_search", "confidence": 0.97, "reason": "site + query", "action": null}
"find pytorch on github" → {"mode": "smart_search", "confidence": 0.96, "reason": "github search", "action": null}
"open github nikhil00437" → {"mode": "smart_search", "confidence": 0.95, "reason": "direct profile url", "action": null}
"look up asyncio on stackoverflow" → {"mode": "smart_search", "confidence": 0.95, "reason": "stackoverflow search", "action": null}
"google how to fix pip" → {"mode": "smart_search", "confidence": 0.93, "reason": "google search query", "action": null}
"play music" → {"mode": "music", "confidence": 0.93, "reason": "play mp3 files", "action": "play"}
"search pdf" → {"mode": "search", "confidence": 0.88, "reason": "find files", "action": "pdf"}
"what time is it" → {"mode": "time", "confidence": 0.97, "reason": "get time", "action": null}
"generate an image" → {"mode": "image_gen", "confidence": 0.98, "reason": "generate image", "action": "generate image"}
"show apps" → {"mode": "show_apps", "confidence": 0.92, "reason": "list applications", "action": null}
"show top memory apps" → {"mode": "powershell", "confidence": 0.91, "reason": "NL system query", "action": "show top memory apps"}
"explain systeminfo" → {"mode": "explain", "confidence": 0.93, "reason": "explain command", "action": "systeminfo"}
"/history" → {"mode": "history", "confidence": 1.0, "reason": "show history", "action": null}
"/rerun 3" → {"mode": "rerun", "confidence": 1.0, "reason": "re-execute command", "action": "3"}
"""

SUMMARIZE_PROMPT = """You are a concise output summarizer for a Windows CLI assistant.
Given raw command output, produce a SUMMARY mode response:
- Use bullet points
- Include key numbers/names
- Max 8 bullets
- Highlight important values
Only output the summary, nothing else."""

EXPLAIN_PROMPT = """You are an expert Windows systems teacher. 
Given a command name or raw system output, explain it clearly:
- What the command does
- Key fields/columns and their meaning
- Any important values to watch
- Common use cases
Be educational but concise."""

SUGGESTION_MAP = {
    "open": ["open notepad", "open calculator", "open explorer", "open cmd",
             "open VS Code", "open YouTube", "open Google", "open Spotify"],
    "search youtube": ["search youtube for ", "search youtube for python tutorial",
                       "search youtube for network chuck", "search youtube for lofi music"],
    "search github":  ["search github for ", "find  on github", "open github "],
    "search google":  ["google how to ", "search google for ", "google what is "],
    "find":           ["find  on github", "find  on stackoverflow", "find  on pypi"],
    "search": ["search pdf", "search py", "search docx", "search mp3",
               "search txt", "search xlsx", "search zip"],
    "kill": ["kill chrome", "kill notepad", "kill explorer", "kill cmd"],
    "show": ["show top memory apps", "show running services",
             "show open ports", "show disk space", "show startup apps"],
    "list": ["list running services", "list stopped services",
             "list installed apps", "list processes", "list users"],
    "/": ["/history", "/rerun "],
    "explain": ["explain systeminfo", "explain tasklist",
                "explain ipconfig", "explain netstat"],
    "play": ["play music"],
    "run": ["run clean"],
}

# URL Search Templates
# Keys are canonical site names; value is the search URL with {query} placeholder.
# The LLM picks the right entry and fills in the query slug.
SEARCH_URL_TEMPLATES = {
    # Video / streaming
    "youtube":      "https://www.youtube.com/results?search_query={query}",
    "twitch":       "https://www.twitch.tv/search?term={query}",
    "vimeo":        "https://vimeo.com/search?q={query}",

    # Dev / tech
    "github":       "https://github.com/search?q={query}&type=repositories",
    "stackoverflow":"https://stackoverflow.com/search?q={query}",
    "pypi":         "https://pypi.org/search/?q={query}",
    "npm":          "https://www.npmjs.com/search?q={query}",
    "dockerhub":    "https://hub.docker.com/search?q={query}",
    "huggingface":  "https://huggingface.co/search/full-text?q={query}",
    "arxiv":        "https://arxiv.org/search/?query={query}&searchtype=all",

    # Search engines
    "google":       "https://www.google.com/search?q={query}",
    "bing":         "https://www.bing.com/search?q={query}",
    "duckduckgo":   "https://duckduckgo.com/?q={query}",

    # Shopping / media
    "amazon":       "https://www.amazon.in/s?k={query}",
    "flipkart":     "https://www.flipkart.com/search?q={query}",
    "spotify":      "https://open.spotify.com/search/{query}",

    # Knowledge / docs
    "wikipedia":    "https://en.wikipedia.org/wiki/Special:Search?search={query}",
    "reddit":       "https://www.reddit.com/search/?q={query}",
    "mdn":          "https://developer.mozilla.org/en-US/search?q={query}",
    "devdocs":      "https://devdocs.io/#q={query}",

    # Maps / local
    "maps":         "https://www.google.com/maps/search/{query}",
    "googlemaps":   "https://www.google.com/maps/search/{query}",
}

# Aliases → canonical key  (handles user shorthand / typos)
SITE_ALIASES = {
    "yt":           "youtube",
    "gh":           "github",
    "so":           "stackoverflow",
    "hf":           "huggingface",
    "ddg":          "duckduckgo",
    "wiki":         "wikipedia",
    "amzn":         "amazon",
    "gmap":         "maps",
    "google maps":  "maps",
    "npm registry": "npm",
}

# URL Generation LLM Prompt
URL_GEN_PROMPT = """You are a URL builder for ARIA, a Windows AI assistant.

Given a user's natural-language request, extract:
1. The target website (pick from the known sites below, or use google as fallback)
2. The search query slug (URL-encoded, spaces → +)

Known sites and their search URL patterns:
{templates}

Rules:
- Use the EXACT template from the list above for the matched site
- Replace {{query}} with the URL-encoded search term (spaces → +, lowercase)
- If the user mentions a username / profile (e.g. "open github nikhil00437"), go directly:
  github profile  → https://github.com/{{username}}
  youtube channel → https://www.youtube.com/@{{handle}}
- If no specific site is mentioned, default to google
- Respond with ONLY valid JSON, no markdown, no explanation:

{
  "site": "youtube",
  "url": "https://www.youtube.com/results?search_query=network+chuck",
  "explanation": "Searching YouTube for Network Chuck"
}
"""
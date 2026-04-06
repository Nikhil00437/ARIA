# ARIA — Advanced Runtime Intelligence Assistant

A local-first, privacy-focused Windows desktop AI assistant with an integrated **Self-Modification System**, **Fabric pattern engine**, and **real-time system monitoring**. Runs entirely on-device using LM Studio — no cloud dependency.

---

## Architecture

```
ARIA/
├── main.py                  # Entry point
├── main_window.py           # Central orchestrator
├── chat_engine.py           # Intent → action pipeline
├── llm_client.py            # LM Studio communication
├── extract.py               # Safety, NL→PS, error diagnosis
├── executor.py              # Command execution
├── database.py              # MongoDB persistence
├── voice_engine.py          # TTS (pyttsx3) + STT (faster-whisper)
├── image_generation.py      # Stable Diffusion via diffusers
├── fabric_client.py         # Fabric CLI integration
├── pattern_engine.py        # Local pattern engine
├── web_fetcher.py           # URL-to-text via Jina Reader
├── signals.py               # PyQt5 signal bridge + HealthMonitor
├── sidebar.py               # Navigation panel
├── pages.py                 # Chat, Terminal, Timeline, Warnings
├── patterns_page.py         # Fabric/Local patterns browser
├── selfmod_page.py          # Self-Modification UI
├── quick_panel.py           # Quick actions + system stats
├── settings_dialog.py       # Theme picker dialog
├── styles.py                # Dynamic QSS theme generator
├── title.py                 # Frameless title bar
├── widgets.py               # Reusable UI components
├── constants.py             # All config, prompts, suggestion pools
├── requirements.txt
├── patterns/                # 70+ local pattern templates
└── selfmod/
    ├── __init__.py
    ├── inferencer.py        # Behavioral Intent Inferencer
    ├── proposal_engine.py   # Modification Proposal Engine
    ├── sandbox.py           # Permission-Gated Sandbox + Rollback Ledger
    └── controller.py        # Self-Mod orchestrator
```

---

## Setup

### 1. Prerequisites
- Python 3.10+
- [LM Studio](https://lmstudio.ai) running locally on port 1234
- MongoDB running locally on port 27017
- Windows 10/11

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. LM Studio setup
- Load `qwen3.5-9b` (or any compatible model) as the chat model
- Enable the local server (default: `http://localhost:1234`)
- Optionally load a smaller/faster model as the classifier

### 4. Run
```bash
python main.py
```

---

## Intent Modes

| Mode | Trigger | Handler |
|---|---|---|
| `chat` | General conversation | LLM streaming chat |
| `command` | "open X", "run X" | App resolver + executor |
| `wikipedia` | "what is X", "who is X" | MediaWiki REST API |
| `browser` | Direct URLs | Default browser |
| `music` | "play X" | Spotify / YouTube |
| `search` | "search X" | Smart URL builder (20+ platforms) |
| `smart_search` | "search X on GitHub" | Platform-specific URLs |
| `show_apps` | "show installed apps" | System app enumeration |
| `quick_open` | "quick open X" | Fast app launcher |
| `powershell` | "show RAM usage", "list services" | NL→PS translation (14 patterns) |
| `explain` | "explain this code" | LLM explanation |
| `image_gen` | "generate image of X" | Stable Diffusion 2.1 |
| `fabric` | "/fabric summarize" | Fabric CLI pattern execution |
| `time` | "what time is it" | System clock |
| `history` | `/history` | MongoDB query |
| `rerun` | `/rerun N` | Re-execute command N |

---

## Features

### Self-Modification System
ARIA monitors your interaction patterns and proposes targeted configuration changes. All changes require explicit approval and are fully reversible.

**Components:**
- **Behavioral Intent Inferencer** — Two-tier analysis (rule-based fast detection + LLM deep analysis) on the last 60 interactions
- **Modification Proposal Engine** — Translates patterns into scoped, validated proposals with human-readable descriptions
- **Permission-Gated Sandbox** — Layered config (defaults + active modifications) with boundary enforcement
- **Rollback Ledger** — Append-only MongoDB ledger; every change recorded with before/after state; one-click rollback

**Modifiable Parameters:**
| Parameter | Type | Default | Description |
|---|---|---|---|
| `output_mode` | choice | `verbose` | Full output vs condensed bullets |
| `smart_search_threshold` | float | `0.75` | Classifier confidence for smart_search |
| `tts_enabled` | bool | `true` | Text-to-speech on/off |
| `silent_mode` | bool | `false` | Only speak errors/confirmations |
| `default_theme` | choice | `cyber` | Startup theme |
| `suggestion_count` | int | `3` | Number of suggestion buttons (3–8) |
| `custom_shortcuts` | dict | `{}` | Alias → app/URL mappings |
| `preferred_search_sites` | list | `[]` | Prioritized search platforms |
| `confirmation_verbosity` | choice | `full` | Command confirmation detail |
| `response_length_preference` | choice | `concise` | Response length bias |

**Permanently Locked:** `blocked_patterns`, `confirm_patterns`, `system_prompt_safety`, `executor_security`, `mongo_uri`, `lm_studio_base_url`

### Fabric Pattern Integration
Full integration with the [Fabric](https://github.com/danielmiessler/fabric) CLI tool:
- 60+ patterns across 8 categories (analysis, extraction, summarization, writing, security, coding, content, AI & prompts)
- Streaming execution with real-time output
- Quick pattern aliases: Summarize, Extract, Analyze, Improve
- Pattern browser with search, preview, and save-to-file

### Local Pattern Engine
Built-in pattern system loading templates from `patterns/` directory:
- 70+ local patterns with `system.md` and optional `user.md`
- Intent-matching regex map for auto-suggestion
- Streaming execution through the LLM

### Suggestion Buttons
Context-aware suggestion chips above the input field:
- 5 categories: chat, command, powershell, search, image_gen
- 15–20 prompts per pool, randomly sampled each session
- Configurable count via self-modification (3–8 buttons)

### Quick Actions Panel
Right-side panel with a 2×3 grid of quick actions:
- **Summarize** — Summarize selected text or conversation
- **Extract** — Extract key insights and wisdom
- **Analyze** — Analyze claims and arguments
- **Improve** — Improve writing quality
- **Terminal** — Quick navigate to terminal
- **Browse** — Quick open browser

### System Health Monitoring
- Periodic checks every 5 minutes for CPU spikes (>75% warning, >90% error), RAM hogs (>500MB), and disk usage
- Warnings displayed in the Warnings page and sidebar badge
- Real-time CPU/RAM mini bars in the sidebar

### Voice I/O
- **Text-to-Speech** via pyttsx3 with female voice preference
- **Speech-to-Text** via faster-whisper `tiny` model (int8, CPU)
- Voice toggle and mic button in the sidebar
- Silent mode: only speak errors and confirmations

### Image Generation
- Stable Diffusion 2.1 via `diffusers`
- Auto-detects CUDA, CPU fallback supported
- Saves generated images to Desktop with timestamps

### Web Fetcher
- URL-to-text conversion via Jina Reader API (free, no API key)
- Login/paywall detection
- Clean markdown output

### Themes
- **Cyber** — Dark green terminal aesthetic (default)
- **Minimal** — Light blue clean design
- **Classic** — Monochrome dark
- Instant theme switching with full preview

### Session Management
- Create, list, and switch between sessions
- Full message history persistence in MongoDB
- Up to 40 messages retained in active memory

---

## Slash Commands

| Command | Action |
|---|---|
| `/help` | Show all commands |
| `/history` | Last 10 commands with status |
| `/rerun N` | Re-run command #N |
| `/snapshot` | System health snapshot |
| `/selfmod` | Trigger behavioral analysis now |
| `/mods` | Show active modifications |

---

## Notes
- Image generation requires a CUDA GPU for reasonable performance. CPU fallback works but is slow.
- STT uses faster-whisper `tiny` model (CPU, int8). Upgrade to `base` or `small` for better accuracy.
- All data stays local: MongoDB, LM Studio, and the Stable Diffusion model run on your machine.
- Fabric CLI is optional — auto-discovered if installed, patterns still work without it via the local pattern engine.

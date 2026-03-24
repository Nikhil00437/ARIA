# ARIA — Advanced Runtime Intelligence Assistant

A local-first, privacy-focused Windows desktop AI assistant with an integrated **Self-Modification System**. Runs entirely on-device using LM Studio — no cloud dependency.

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
├── signals.py               # PyQt5 signal bridge + HealthMonitor
├── sidebar.py               # Navigation panel
├── pages.py                 # Chat, Terminal, Timeline, Warnings
├── selfmod_page.py          # Self-Modification UI
├── styles.py                # Dynamic QSS theme generator
├── title.py                 # Frameless title bar
├── widgets.py               # Reusable UI components
├── constants.py             # All config, prompts, templates
├── requirements.txt
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
- Load `qwen3-vl-8b-instruct` (or any compatible model) as the chat model
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
| `search` | "search X" | Smart URL builder |
| `smart_search` | "search X on GitHub" | Platform-specific URLs |
| `powershell` | "show RAM usage", "list services" | NL→PS translation |
| `explain` | "explain this code" | LLM explanation |
| `image_gen` | "generate image of X" | Stable Diffusion 2.1 |
| `time` | "what time is it" | System clock |
| `history` | `/history` | MongoDB query |
| `rerun` | `/rerun N` | Re-execute command N |

---

## Self-Modification System

### Overview
ARIA monitors your interaction patterns and proposes targeted configuration changes. All changes require explicit approval and are fully reversible.

### Components

**1. Behavioral Intent Inferencer** (`selfmod/inferencer.py`)
- Analyzes the last 60 interactions (chat + commands)
- Two-tier: rule-based fast detection + LLM deep analysis
- Detects patterns like: repeated brevity requests, preferred search sites, mute preferences, failure patterns

**2. Modification Proposal Engine** (`selfmod/proposal_engine.py`)
- Translates patterns into scoped, validated `Proposal` objects
- Enforces boundary rules (locked params can never appear in proposals)
- Generates human-readable proposal text via LLM

**3. Permission-Gated Sandbox** (`selfmod/sandbox.py`)
- Single source of truth for runtime config
- Layered: defaults → persisted active modifications
- All changes require explicit user approval in the UI

**4. Rollback Ledger** (`selfmod/sandbox.py`)
- Append-only MongoDB collection — no entry is ever deleted
- Every approved modification recorded with before/after state
- One-click rollback per entry from the Ledger tab

### Modifiable Parameters
| Parameter | Type | Default | Description |
|---|---|---|---|
| `output_mode` | choice | `verbose` | Full output vs condensed bullets |
| `smart_search_threshold` | float | `0.75` | Classifier confidence for smart_search |
| `tts_enabled` | bool | `true` | Text-to-speech on/off |
| `silent_mode` | bool | `false` | Only speak errors/confirmations |
| `default_theme` | choice | `cyber` | Startup theme |
| `suggestion_count` | int | `3` | Chat suggestion count |
| `custom_shortcuts` | dict | `{}` | Alias → app/URL mappings |
| `preferred_search_sites` | list | `[]` | Prioritized search platforms |
| `confirmation_verbosity` | choice | `full` | Command confirmation detail |
| `response_length_preference` | choice | `concise` | Response length bias |

### Permanently Locked (never modifiable)
`blocked_patterns`, `confirm_patterns`, `system_prompt_safety`, `executor_security`, `mongo_uri`, `lm_studio_base_url`

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

## Themes
- **Cyber** — Dark green terminal aesthetic (default)
- **Minimal** — Light blue clean design  
- **Classic** — Monochrome dark

> yeah don't try minimal if you're used to dark mode
> i tried and my i'm blind for like 20 sec
---

## Notes
- Image generation requires a CUDA GPU for reasonable performance. CPU fallback works but is slow.
- STT uses faster-whisper `tiny` model (CPU, int8). Upgrade to `base` or `small` for better accuracy.
- All data stays local: MongoDB, LM Studio, and the Stable Diffusion model run on your machine.

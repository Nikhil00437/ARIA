# ARIA — Advanced Runtime Intelligence Assistant

> A fully local, privacy-first AI desktop assistant for Windows. No cloud. No subscriptions. No data leaving your machine.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![PyQt5](https://img.shields.io/badge/GUI-PyQt5-green?logo=qt&logoColor=white)
![LM Studio](https://img.shields.io/badge/LLM-LM%20Studio-purple)
![MongoDB](https://img.shields.io/badge/Database-MongoDB-47A248?logo=mongodb&logoColor=white)
![License](https://img.shields.io/github/license/Nikhil00437/ARIA)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)

---

## What is ARIA?

ARIA is a **local-first AI desktop assistant** built with PyQt5 that runs entirely on your own hardware using [LM Studio](https://lmstudio.ai) for LLM inference. It converts natural language into system actions, generates images via Stable Diffusion, responds with a voice engine, and persists conversations in MongoDB — all without sending a single byte to an external server.

Think of it as a privacy-respecting alternative to cloud AI assistants, engineered from scratch as a modular Python desktop application.

---

## Features

| Feature | Description |
|---|---|
| 💬 **Local LLM Chat** | Conversational AI powered by any model loaded in LM Studio |
| 🎨 **Image Generation** | Stable Diffusion integration — generate images inline in the chat |
| 🔊 **Voice Engine** | Text-to-speech responses via the built-in voice module |
| 🗄️ **Persistent Memory** | Full conversation history stored locally in MongoDB |
| ⚙️ **System Automation** | Natural language → Windows system commands via `executor.py` |
| 📄 **Document Extraction** | Read and process file content with `extract.py` |
| 🔒 **Zero Cloud Dependency** | All inference runs locally — no API keys, no subscriptions |
| 🧩 **Modular Architecture** | 15 decoupled modules — easy to extend or swap components |

---

## Architecture

ARIA is split into 15 focused modules, each with a single responsibility:

```
ARIA/
├── main.py                  # Entry point — bootstraps the application
├── main_window.py           # Root PyQt5 window, layout orchestration
├── pages.py                 # Page/view management (chat, settings, etc.)
├── sidebar.py               # Navigation sidebar component
├── widgets.py               # Reusable UI widgets
├── styles.py                # Global stylesheet definitions
├── signals.py               # Qt signal/slot definitions across modules
├── chat_engine.py           # Core chat loop — assembles prompt, calls LLM, routes response
├── llm_client.py            # LM Studio API client (OpenAI-compatible endpoint)
├── voice_engine.py          # Text-to-speech engine
├── image_generation_try.py  # Stable Diffusion image generation
├── executor.py              # Natural language → system command execution
├── extract.py               # File/document content extraction
├── database.py              # MongoDB connection, conversation persistence
└── constants.py             # App-wide configuration and constants
```

---

## Prerequisites

- Windows 10 / 11
- Python 3.10+
- [LM Studio](https://lmstudio.ai) — installed and running with a model loaded
- [MongoDB Community](https://www.mongodb.com/try/download/community) — running locally on default port `27017`
- (Optional) Stable Diffusion — for image generation

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/Nikhil00437/ARIA.git
cd ARIA

# 2. Create a virtual environment
python -m venv venv
venv\Scripts\activate      # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start LM Studio and load your preferred model
#    Enable the local server (default: http://localhost:1234)

# 5. Ensure MongoDB is running
#    Default connection: mongodb://localhost:27017

# 6. Launch ARIA
python main.py
```

---

## Configuration

Edit `constants.py` to configure your setup:

```python
# LM Studio endpoint (default)
LM_STUDIO_URL = "http://localhost:1234/v1"

# MongoDB connection
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "aria_db"

# Voice engine settings
VOICE_RATE = 175       # Speech speed (words per minute)
VOICE_VOLUME = 1.0     # Volume (0.0 – 1.0)
```

---

## How It Works

```
User types message
        │
        ▼
  chat_engine.py          ← Assembles system prompt + conversation history
        │
        ▼
  llm_client.py           ← Sends to LM Studio (OpenAI-compatible API)
        │
        ▼
  Response received
        │
    ┌───┴────────────────────────────────┐
    │                                    │
    ▼                                    ▼
voice_engine.py              executor.py / image_generation_try.py
(text response)              (if system command or image prompt detected)
    │                                    │
    └───────────────┬────────────────────┘
                    ▼
             database.py          ← Saves exchange to MongoDB
                    │
                    ▼
          UI updated (PyQt5)
```

---

## Tech Stack

| Component | Technology |
|---|---|
| GUI Framework | PyQt5 |
| LLM Inference | LM Studio (OpenAI-compatible local API) |
| Image Generation | Stable Diffusion |
| Voice Engine | pyttsx3 / Windows SAPI |
| Database | MongoDB (pymongo) |
| Language | Python 3.10+ |

---

## Roadmap

- [ ] Plugin system for custom command modules
- [ ] Model switching from within the UI
- [ ] RAG (Retrieval-Augmented Generation) over local documents
- [ ] Hotkey activation (always-on-screen mode)
- [ ] Settings panel for voice/model/database config
- [ ] Linux support

---

## Contributing

Contributions are welcome. To get started:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'Add your feature'`
4. Push and open a Pull Request

Please keep new features modular — one concern per file, consistent with the existing architecture.

---

## License

MIT License — see [LICENSE](./LICENSE) for details.

---

## Author

**Nikhil Bisht**

[![GitHub](https://img.shields.io/badge/GitHub-Nikhil00437-181717?logo=github)](https://github.com/Nikhil00437)
[![HuggingFace](https://img.shields.io/badge/HuggingFace-Nikhil1581-FFD21E?logo=huggingface&logoColor=black)](https://huggingface.co/Nikhil1581)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-nikhil--bisht-0A66C2?logo=linkedin)](https://www.linkedin.com/in/nikhil-bisht-986047298/)

---

*If ARIA was useful or interesting, leaving a ⭐ on the repo is appreciated.*

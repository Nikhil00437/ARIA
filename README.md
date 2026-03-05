# ARIA – Advanced Runtime Intelligence Assistant

![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python&logoColor=white)
![PyQt5](https://img.shields.io/badge/GUI-PyQt5-green?logo=qt&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)
![MongoDB](https://img.shields.io/badge/Database-MongoDB-47A248?logo=mongodb&logoColor=white)

ARIA is a desktop AI assistant for Windows that combines local LLMs, system automation, and a modern PyQt interface. It allows users to control their computer using natural language while also supporting chat, automation, macros, image generation, and voice output.

---

## Features

* Natural language command execution
* Local LLM-powered intent classification
* Windows command and PowerShell automation
* Desktop GUI built with PyQt5
* Command history and session logging
* Macro creation and execution
* File search and quick application launch
* Local image generation using Stable Diffusion
* Voice output (text-to-speech)
* MongoDB-based conversation persistence

---

## Architecture Overview

ARIA processes user input through an AI-assisted pipeline:

1. User enters text in the desktop interface
2. Intent classification determines the action type
3. Commands are translated into system operations
4. Execution engine runs commands or triggers AI features
5. Results are returned to the GUI and stored in history

This architecture allows ARIA to behave as both a chatbot and a system automation agent.

---

## Tech Stack

### Core

* Python
* PyQt5

### AI / ML

* Local LLMs (LM Studio)
* Hugging Face / Transformers
* Stable Diffusion (Diffusers + PyTorch)

### System Integration

* Windows Command Execution
* PowerShell Automation

### Data Storage

* MongoDB

### Other Libraries

* OpenAI compatible API client
* pyttsx3 (Text-to-Speech)

---

## Project Structure

```
ARIA/
│
├── main.py                 # Application entry point
├── main_window.py          # Main GUI window
├── chat_engine.py          # Core request routing logic
├── llm_client.py           # LLM communication
├── voice_engine.py         # Text-to-speech engine
├── image_generation_try.py # Stable Diffusion image generation
├── extract.py              # Command execution and translation
├── database.py             # MongoDB logging and storage
│
├── pages.py                # GUI pages
├── sidebar.py              # Sidebar navigation
├── widgets.py              # Custom UI widgets
├── styles.py               # Theme system
├── constants.py            # Prompts and configuration
└── signals.py              # Application signal bridge
```

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Nikhil00437/ARIA.git
cd ARIA
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

If a requirements file is not present, install manually:

```bash
pip install pyqt5 pymongo pyttsx3 wikipedia diffusers transformers torch
```

### 3. Setup MongoDB

Make sure MongoDB is running locally:

```
mongodb://localhost:27017
```

ARIA will automatically create the required collections.

### 4. Setup Local LLM

Run a local model using **LM Studio** and ensure the API endpoint is accessible.

Default endpoint used:

```
http://localhost:1234/v1
```

### 5. Run the application

```bash
python main.py
```

---

## Example Commands

ARIA can understand commands like:

```
open notepad
show running services
search pdf
show top memory apps
open youtube
flush dns
```

It can also answer general questions or generate images.

---

## Image Generation

ARIA includes local image generation using Stable Diffusion.

Example prompt:

```
a cyberpunk city at night with neon lights
```

Generated images are saved automatically.

---

## Macros

You can create reusable command workflows.

Example:

```
create macro cleanup
→ search pdf
→ open explorer
```

Macros can be executed later using natural language.

---

## Contributing

Contributions are welcome! Here's how to get started:

1. **Fork** the repository
2. **Create a branch** for your feature or fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Commit** your changes with a clear message:
   ```bash
   git commit -m "Add: description of your change"
   ```
4. **Push** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
5. **Open a Pull Request** against the `main` branch

Please keep PRs focused — one feature or fix per PR makes review much easier.

---

## Future Improvements

* Voice input (speech recognition)
* Cross-platform support
* Plugin system for custom skills
* RAG-based knowledge retrieval
* Better agent planning capabilities

---

## Author

**Nikhil** — AI & Data Science Undergraduate

GitHub: [https://github.com/Nikhil00437](https://github.com/Nikhil00437)

---

## License

This project is open-source and available under the [MIT License](LICENSE).

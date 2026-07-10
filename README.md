
# 🐧 Project Nova - The Autonomous Linux Companion

<p align="center">
  <img src="https://img.shields.io/badge/Version-0.1.0_Genesis-orange?style=for-the-badge&logo=linux" alt="Version">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/C/Rust-Sentinel%20Daemon-000000?style=for-the-badge&logo=c" alt="C/Rust">
  <img src="https://img.shields.io/badge/AI%20Engine-Qwen%202.5%20Coder%203B-FF6F00?style=for-the-badge" alt="AI Model">
  <img src="https://img.shields.io/badge/Budget-$0.00%20FOSS-4CAF50?style=for-the-badge" alt="Budget">
  <img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" alt="License">
</p>

<p align="center">
  <strong>A Fully Autonomous, Zero-Budget, Offline-First AI Agent for Linux. System-Native, Self-Evolving, and Unrestricted (with SUDO Consent).</strong>
</p>

---

## ✨ Features at a Glance

| Category | Features |
|----------|----------|
| 🧠 **AI Engine** | Qwen 2.5 Coder 3B (Offline), Nomic-Embed-Text, Local Vector DB, Context Summarization |
| 🐧 **System Integration** | 100% Linux Native, Systemd Daemon, D-Bus IPC, ALSA/PipeWire Audio, Cross-Distro Support |
| 🛡️ **Security & SUDO** | 5-Tier Risk Classification, AST Bash Parsing, Bubblewrap Sandboxing, Explicit Consent Protocol |
| 🔄 **Memory & Evolution** | ChromaDB Long-Term Memory, DBSCAN Habit Clustering, Proactive Automation Suggestions |
| 🌐 **Connectivity** | Offline-First Architecture, Permissioned Internet Updates, DuckDuckGo Search Integration |
| 👂 **Background Listener** | < 5MB RAM Footprint, C/Rust Optimized, Custom Wake Word ("NOVA"), Instant Cortex Wake-up |

---

## 🚀 Quick Start Guide

### Prerequisites

Ensure you are running a **Linux Distribution** (Kali, Ubuntu, Arch, Fedora, etc.) and have the following:

- **Python** 3.11+ and `pip`
- **CMake** & **Build Essentials** (for compiling the Sentinel listener)
- **Ollama** (for local LLM inference)
- **PortAudio** & **ALSA/PipeWire** development libraries

### Installation Steps

```bash
# 1. Clone the Project Nova repository
git clone https://github.com/manjiltimalsina/project-nova.git
cd project-nova

# 2. Make the universal installer executable
chmod +x install.sh

# 3. Run the automated setup (Detects distro, installs deps, pulls models)
./install.sh
```

The `install.sh` script automatically:
- ✅ Detects your Linux distribution via `/etc/os-release`
- ✅ Installs system dependencies (`apt`, `pacman`, or `dnf`)
- ✅ Compiles the C/Rust Sentinel daemon for < 5MB RAM usage
- ✅ Sets up the Python virtual environment for the Cortex
- ✅ Lets you choose the LLM backend during setup, including Ollama or a local llama.cpp-style path
- ✅ Lets you choose an open-source model preset or enter a custom model name during setup
- ✅ Registers and enables `nova-sentinel.service` via `systemd`

### Access the Agent

| Interface | Trigger / Command |
|-----------|-------------------|
| **Voice Activation** | Say the wake word: **"NOVA"** (Customizable) |
| **CLI Activation** | Run `nova-cli` in any terminal |
| **System Tray** | Left-click the Nova icon in your DE's system tray |
| **Check Status** | `systemctl status nova-sentinel` |

---

## 🎯 Complete Feature Walkthrough

### Step 1: The Sentinel (Background Listener) 👂

When you restart your PC, Nova is already there. The **Sentinel** is a highly optimized C/Rust daemon that starts via `systemd`.

- **Ultra-Lightweight:** Consumes **< 5MB of RAM** and near-zero CPU.
- **Audio Buffer:** Maintains a circular audio buffer in memory using `mmap` to avoid heap allocation overhead.
- **Wake Word Detection:** Uses a tiny, compiled ONNX model (via `openwakeword`) to listen for "NOVA".
- **IPC Trigger:** The moment "NOVA" is detected, it sends an Inter-Process Communication signal via **D-Bus** or a Unix Domain Socket to instantly wake up the Cortex, then flushes the audio buffer.

---

### Step 2: The Cortex (AI Processing) 🧠

Once awakened, the **Cortex** (Python async event loop) spins up.

- **Lazy Loading:** The Cortex is dead by default. It only loads the heavy AI models into RAM when triggered.
- **Speech-to-Text:** Uses `faster-whisper` (CTranslate2 backend) to transcribe your voice command locally.
- **LLM Inference:** Routes the text to **Qwen 2.5 Coder 3B** (running via Ollama or `llama-cpp-python`).
- **Context Management:** Uses a sliding window + summarization technique to keep the 32k context window efficient and prevent "lost in the middle" syndrome.

---

### Step 3: Tool Routing & Execution 🛠️

Nova doesn't just chat; it acts. Qwen 2.5 Coder is fine-tuned for logical routing and code generation.

- **Function Calling:** The LLM outputs strict JSON to call registered tools (e.g., `execute_bash`, `read_file`, `search_web`).
- **Pydantic Validation:** All tool parameters are validated before execution to prevent malformed inputs.
- **Parallel Execution:** The async event loop can execute multiple non-blocking tools simultaneously (e.g., reading a file while checking the weather).

---

### Step 4: The Shield & SUDO Protocol 🛡️

This is Nova's most critical feature. It can do *anything*, but it respects your authority.

- **AST Parsing:** Before running any bash command, the Shield parses the Abstract Syntax Tree to detect destructive flags (`rm -rf`, `dd`, `mkfs`).
- **5-Tier Risk Classification:**
  - **Tier 0 (Safe):** `ls`, `cat`, reading memory. *Executes immediately.*
  - **Tier 1 (User Write):** Creating files in `/home`. *Executes and logs.*
  - **Tier 2 (Network):** `curl`, web search. *Pauses for consent.*
  - **Tier 3 (System Mod):** `apt install`, `systemctl`. *Pauses for SUDO consent.*
  - **Tier 4 (Destructive):** `rm -rf /`, formatting drives. *Requires typing "CONFIRM" to proceed.*
- **Sandboxing:** Untrusted scripts are executed inside `bubblewrap` (`bwrap`) or `systemd-nspawn` namespaces.

---

### Step 5: Memory & Habit Learning 🔄

Nova evolves with you. It doesn't just remember; it learns patterns.

- **Vector DB (ChromaDB):** Stores long-term memory, user preferences, and past project contexts using `nomic-embed-text`.
- **Habit Tracker:** A background SQLite database logs every tool execution.
- **DBSCAN Clustering:** Every Sunday, a cron job analyzes the logs to find temporal patterns (e.g., "User runs `git pull` and `npm run build` every Monday at 9 AM").
- **Proactive Suggestions:** Nova will inject these habits into its context and say, *"I notice you usually compile with `gcc -O3`. Should I use that flag?"*

---

### Step 6: Permissioned Internet Updates 🌐

Nova is offline-first, but not offline-only.

- **Trigger:** The LLM realizes it lacks information (e.g., "How to configure the new Nvidia driver in Kali 2026.3?").
- **The Handshake:** Nova pauses and outputs: *"I do not have this information in my local weights. May I search the internet?"*
- **Execution:** Upon approval, it uses `duckduckgo-search`, scrapes the top results using `BeautifulSoup`, and injects the text into the context window.
- **Self-Update:** Highly relevant data is embedded and saved to ChromaDB for future offline use.

---

## 🏗️ System Architecture

```text
project-nova/
│
├── nova-sentinel/                # The <5MB Background Listener (C/Rust)
│   ├── src/
│   │   ├── main.c                # Entry point, ALSA/PipeWire setup
│   │   ├── audio_buffer.c        # Circular buffer implementation (mmap)
│   │   └── wake_word.c           # ONNX inference for wake word detection
│   ├── CMakeLists.txt            # Build configuration
│   └── README.md
│
├── nova-cortex/                  # The AI Brain & Orchestrator (Python)
│   ├── nova/
│   │   ├── core/
│   │   │   ├── event_loop.py     # Asyncio main loop
│   │   │   ├── ipc_server.py     # Listens to Sentinel D-Bus/Socket triggers
│   │   │   └── state.py          # Global state management
│   │   ├── llm/
│   │   │   ├── engine.py         # Ollama / llama-cpp-python wrapper
│   │   │   ├── prompts.py        # System prompts and few-shot tool examples
│   │   │   └── context.py        # Sliding window and summarization logic
│   │   ├── audio/
│   │   │   ├── stt.py            # faster-whisper integration
│   │   │   └── tts.py            # Piper TTS integration
│   │   ├── tools/
│   │   │   ├── registry.py       # The @nova_tool decorator system
│   │   │   ├── bash_executor.py  # Core command execution tool
│   │   │   ├── file_ops.py       # Read/write/search files
│   │   │   └── web_search.py     # DuckDuckGo integration
│   │   ├── shield/
│   │   │   ├── classifier.py     # AST parser and 5-tier risk assignment
│   │   │   ├── sandbox.py        # bubblewrap/systemd-nspawn wrapper
│   │   │   └── consent.py        # CLI prompts for user authorization
│   │   ├── memory/
│   │   │   ├── vector_db.py      # ChromaDB wrapper
│   │   │   ├── embeddings.py     # nomic-embed-text wrapper
│   │   │   └── habit_tracker.py  # SQLite logging and DBSCAN clustering
│   │   └── ui/
│   │       └── cli.py            # Rich library terminal UI
│   ├── tests/                    # Pytest unit and integration tests
│   └── pyproject.toml            # Python dependencies (uv/poetry)
│
├── services/
│   ├── nova-sentinel.service     # Systemd unit for the listener
│   └── nova-cortex.service       # Systemd unit for the brain (dbus-activated)
│
├── install.sh                    # Universal distro-agnostic installer
├── uninstall.sh                  # Clean removal script
├── ProjectNova.md                # THIS MASTER DOCUMENT
└── README.md                     # Quick start and project overview
```

---

## ⚙️ Environment Configuration

### Cortex Configuration (`nova-cortex/.env`)

Create the environment file for the AI engine:

```env
# LLM Configuration
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5-coder:3b
LLM_BASE_URL=http://localhost:11434

# Embeddings Configuration
EMBEDDING_MODEL=nomic-embed-text

# Memory & Vector DB
VECTOR_DB_PATH=./data/chroma_db
SQLITE_DB_PATH=./data/nova_memory.sqlite

# Security & Shield
SANDBOX_ENABLED=true
DEFAULT_RISK_TIER_OVERRIDE=0
AUTO_APPROVE_TIER_0=true

# Internet & Search
ENABLE_WEB_SEARCH=true
SEARCH_PROVIDER=duckduckgo
MAX_SEARCH_RESULTS=3
```

---

## 🐛 Troubleshooting

### Sentinel Consuming Too Much RAM
```bash
# Check Sentinel memory usage
ps -o pid,rss,comm -p $(pgrep nova-sentinel)

# If > 10MB, ensure the ONNX model is compiled with optimizations
cd nova-sentinel/build
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)
```

### Ollama Connection Refused
```bash
# Ensure Ollama is running
systemctl status ollama

# Restart Ollama service
sudo systemctl restart ollama

# Verify model is pulled
ollama list | grep qwen2.5-coder
```

### Wake Word Not Detecting
1. Check microphone permissions: `sudo usermod -aG audio $USER` (then reboot).
2. Verify ALSA/PipeWire input device in `nova-sentinel/config.json`.
3. Test audio input: `arecord -d 5 test.wav && aplay test.wav`.

### Cross-Distro Dependency Issues
```bash
# Manually trigger the distro-detection logic
cat /etc/os-release

# If install.sh fails, install manually based on your distro:
# Debian/Kali/Ubuntu:
sudo apt install portaudio19-dev python3-dev libsndfile1 cmake build-essential

# Arch/Manjaro:
sudo pacman -Syu portaudio python sndfile cmake base-devel

# Fedora:
sudo dnf install portaudio-devel python3-devel libsndfile cmake gcc gcc-c++ make
```

---

## 🗺️ Ground-Zero Execution Roadmap

As a solo developer, the project follows strict **Deep Work Sprints**.

### Phase 1: The Foundation & The Listener (Days 1 - 15)
- **Day 1-3:** Initialize Git repo, set up Python `uv`/`poetry`, configure project structure.
- **Day 4-7:** Build the C/Rust Listener. Implement ALSA capture, circular buffer, and `openwakeword` ONNX integration. Profile to < 5MB RAM.
- **Day 8-10:** Implement IPC (Unix Domain Socket / D-Bus) between Sentinel and Cortex.
- **Day 11-15:** Build the Python Cortex event loop. Integrate `llama-cpp-python`. Load Qwen 2.5 Coder 3B. Write `systemd` service files.

### Phase 2: Voice, Tools, and the Shield (Days 16 - 30)
- **Day 16-18:** Integrate `faster-whisper` (STT) and `Piper` (TTS). Route audio from Sentinel to Cortex.
- **Day 19-22:** Build the `@nova_tool` decorator registry. Implement basic file and bash tools.
- **Day 23-26:** Build the Shield. Implement AST bash parsing, 5-tier risk classification, and CLI consent prompts.
- **Day 27-30:** End-to-End Voice Loop testing. Refine JSON parsing for LLM tool calls.

### Phase 3: Memory, Evolution, and Internet (Days 31 - 45)
- **Day 31-34:** Initialize ChromaDB. Implement `nomic-embed-text` pipeline.
- **Day 35-38:** Build Context Injection. Retrieve and inject top 3 memories into the system prompt.
- **Day 39-41:** Build the Habit Tracker (SQLite) and the weekly DBSCAN clustering cron job.
- **Day 42-45:** Implement the `duckduckgo-search` tool. Build the "Permission Handshake" UI.

### Phase 4: Cross-Distro Packaging & Polish (Days 46 - 60)
- **Day 46-50:** Write the universal `install.sh` script with `os-release` detection.
- **Day 51-54:** Implement Mock OS environments for CI/CD testing. Handle edge cases (OOM, mic disconnects).
- **Day 55-58:** Polish the CLI UI using the `Rich` library (spinners, colors, markdown rendering).
- **Day 59-60:** Finalize documentation, record demo video, push to GitHub, and launch on r/Linux and Hacker News.

---

## 📞 Support & Contact

Project Nova is an independent, zero-budget, open-source initiative built from the ground up. 

If you are interested in the architecture, want to collaborate, have technical feedback, or represent an organization interested in supporting the continued development of this open-source AI infrastructure, please reach out directly.

**Lead Developer & Architect:** Manjil Timalsina  
**Email:** [timalsinamanjil04@gmail.com](mailto:timalsinamanjil04@gmail.com)  
**GitHub:** [@manjiltimalsina](https://github.com/Manjil740)

---

<div align="center">

### 🎯 Autonomy without Compromise. Intelligence without Limits.

**[http://github.com/manjiltimalsina/project-nova](http://github.com/Manjil740/project-nova)**

---

Built with ❤️ and 100% FOSS for the Linux Community by Manjil Timalsina

</div>
# 🚀 Project Nova: The Autonomous Linux Companion

**Version:** 0.1.0 (Genesis)  
**Status:** 🟢 Active Development (Ground Zero)  
**License:** MIT License  
**Lead Developer & Architect:** Manjil Timalsina  
**Contact:** [timalsinamanjil04@gmail.com](mailto:timalsinamanjil04@gmail.com)  
**Target Environment:** All Linux Distributions (Primary Dev: Kali Linux)  
**Budget Constraint:** Strictly $0.00 (100% FOSS & Free-Tier)

---

## 📖 1. Executive Philosophy & Core Directives

**Project Nova** is not a chatbot. It is a fully autonomous, system-level AI agent designed to act as a digital extension of the Linux user. It operates with deep system awareness, capable of executing complex workflows, managing files, writing code, and adapting to the user's behavioral patterns over time.

### 1.1 The Core Directives
1. **Absolute Autonomy with Explicit Consent:** Nova can perform *any* task on the system, up to and including `sudo` root operations. However, it operates on a strict "Trust but Verify" protocol. High-risk actions require explicit, manual user authorization.
2. **Zero-Budget, 100% Offline-First:** The core brain (Qwen 2.5 Coder 3B) runs entirely locally. No telemetry, no cloud APIs, no subscription fees. Privacy is absolute.
3. **Continuous Self-Evolution:** Nova does not just execute; it learns. By analyzing user habits and utilizing permissioned internet access, it updates its knowledge base and proactively suggests automations.
4. **System-Native & Invisible:** The agent exists as a persistent, ultra-lightweight background daemon (< 5MB RAM). It does not consume GPU/CPU cycles until the exact microsecond it is summoned by the wake word.

---

## 🏗 2. Deep-Dive System Architecture

To achieve the goal of a <5MB background listener while housing a 3B parameter LLM, we cannot use a monolithic Python script. We must use a **Micro-Service Architecture** running on a single machine, utilizing strict process isolation and lazy-loading.

### 2.1 The Four-Layer Architecture

#### Layer 1: The "Sentinel" (Background Listener Daemon)
* **Purpose:** Listens to the microphone 24/7 for the wake word ("NOVA").
* **Memory Constraint:** Must consume < 5MB RAM.
* **Technical Implementation:** 
  * We cannot use heavy Python libraries (like PyAudio + standard Whisper) for the always-on listener. 
  * **Solution:** The Sentinel is written in **C** or uses **Rust** (via `pyo3` if wrapping in Python) to interface directly with ALSA/PipeWire. 
  * It uses a tiny, highly optimized Wake Word model (like `openwakeword` compiled to ONNX, or a custom trained <2MB CNN model). 
  * It maintains a circular audio buffer in memory using `mmap` to avoid heap allocation overhead.
  * When the wake word is detected, it sends an IPC (Inter-Process Communication) signal via **D-Bus** or a local Unix Domain Socket to wake up Layer 2, then immediately flushes the audio buffer to Layer 2 for full processing.

#### Layer 2: The "Cortex" (AI Orchestration & LLM Engine)
* **Purpose:** Processes full voice/text commands, runs the LLM, and manages context.
* **Technical Implementation:**
  * Written in **Python 3.11+** using `asyncio` for non-blocking I/O.
  * **Lazy Loading:** This process is *dead* (not running) by default. It is spawned by `systemd` or the Sentinel only when triggered.
  * **LLM Engine:** Uses `llama-cpp-python` or `Ollama` (via API) to load **Qwen 2.5 Coder 3B (Q4_K_M quantization)**. 
  * **Audio Processing:** Uses `faster-whisper` (CTranslate2 backend) for Speech-to-Text (STT) and `Piper TTS` for Text-to-Speech (TTS). These are loaded into VRAM/RAM only during an active session and unloaded immediately after.

#### Layer 3: The "Hands" (Execution & Tool Router)
* **Purpose:** Translates LLM intent into actual system commands.
* **Technical Implementation:**
  * Uses a custom **Function Calling / Tool Use** framework. Qwen 2.5 Coder is exceptionally good at generating JSON for tool calls.
  * Tools are registered as Python decorators (e.g., `@nova_tool(name="execute_bash", risk_level=3)`).
  * The Cortex parses the LLM's JSON output, validates the schema using `Pydantic`, and routes the execution to the Hands.

#### Layer 4: The "Shield" (Security, SUDO & Sandboxing)
* **Purpose:** Prevents the AI from destroying the system.
* **Technical Implementation:**
  * Every tool call passes through the Shield before execution.
  * **AST Parsing:** For bash commands, the Shield uses Python's `ast` module or a custom bash parser to analyze the command tree. It looks for destructive flags (`rm -rf /`, `mkfs`, `dd if=`).
  * **Privilege Separation:** The Cortex runs as the standard user. If a `sudo` command is approved by the user, the Shield spawns a separate, isolated subprocess using `pkexec` or `sudo`, passing the command via standard input to prevent shell injection.

---

## 🧠 3. AI Strategy: Qwen 2.5 Coder 3B & Memory

### 3.1 The Brain: Qwen 2.5 Coder 3B
* **Why this model?** At 3 Billion parameters, it is small enough to run at 20+ tokens/second on a modern CPU (using 4-bit GGUF quantization) or instantly on a 4GB VRAM GPU. It is specifically fine-tuned on massive code repositories, making it vastly superior to general models (like Llama 3 8B) for system automation, bash scripting, and logical routing.
* **Context Window Management:** The model has a 32k context window. To prevent "lost in the middle" syndrome and save RAM, we use a **Sliding Window + Summarization** technique. Older interactions are compressed by a smaller model (e.g., Qwen 1.5 0.5B) into a single paragraph and injected into the system prompt.

### 3.2 Long-Term Memory & Habit Learning (The "Evolution")
Nova doesn't just remember; it learns patterns. Since we cannot fine-tune the 3B model on the fly (requires massive compute), we use **Heuristic Tracking + RAG (Retrieval-Augmented Generation)**.

1. **The Habit Tracker (Heuristic Engine):**
   * A background SQLite database logs every tool execution with a timestamp, duration, and context.
   * Every Sunday at midnight, a cron job runs a Python script that analyzes this log.
   * It uses **DBSCAN clustering** to find temporal patterns (e.g., "User runs `git pull` and `npm run build` together every day at 9 AM").
   * These patterns are converted into "Habit Prompts" and stored in the Vector DB.
2. **The Vector DB (ChromaDB):**
   * Stores user preferences, past project contexts, and the generated "Habit Prompts".
   * When a new query arrives, the Cortex embeds the query using `nomic-embed-text`, queries ChromaDB, and injects the top 3 most relevant memories/habits into the Qwen system prompt.
   * *Result:* Nova proactively says, "I see you usually compile with `gcc -O3`. Should I use that flag for this new C file?"

### 3.3 The "Permissioned Internet" Self-Update
Nova is offline-first, but not offline-only. 
* **Trigger:** The LLM realizes it lacks information (e.g., "How to configure the new Nvidia driver in Kali 2026.3?").
* **The Handshake:** Nova pauses and outputs: *"I do not have this information in my local weights. May I search the internet?"*
* **Execution:** Upon user approval, the Cortex uses the `duckduckgo-search` Python library. 
* **Data Ingestion:** It scrapes the top 3 results using `BeautifulSoup` and `readability-lxml`, extracts the raw text, chunks it, and feeds it directly into the context window. 
* **Memory Update:** If the information is highly relevant (e.g., a new system configuration), it is embedded and saved to ChromaDB for future offline use.

---

## 🛡 4. Security, Sandboxing, and the "SUDO" Protocol

This is the most critical component. An autonomous agent with system access is a massive security risk if not architected correctly.

### 4.1 The 5-Tier Risk Classification
Every tool and command is statically classified into a Risk Tier.

| Tier | Description | Examples | Nova's Action |
| :--- | :--- | :--- | :--- |
| **0** | **Read-Only / Safe** | `ls`, `cat`, `pwd`, checking weather, reading memory. | Executes immediately. No prompt. |
| **1** | **User-Space Write** | Creating files in `/home/user`, editing local configs. | Executes immediately, but logs the action. |
| **2** | **Network / External** | `curl`, `wget`, sending an email, searching the web. | Pauses. CLI prompts: *"Allow network access? [Y/N]"* |
| **3** | **System Modification** | `apt install`, `systemctl restart`, modifying `/etc/`. | Pauses. CLI prompts: *"Requires SUDO. Authorize? [Y/N]"* |
| **4** | **Destructive / Critical** | `rm -rf`, `dd`, `mkfs`, modifying `/boot`. | Pauses. CLI prompts: *"⚠️ CRITICAL RISK. Type the word 'CONFIRM' to proceed."* |

### 4.2 Technical Implementation of the Shield
1. **JSON Schema Enforcement:** We do not let the LLM output raw bash directly. We force Qwen to output a strict JSON structure:
   ```json
   {
     "thought": "I need to list the files in the current directory.",
     "tool": "execute_bash",
     "parameters": {"command": "ls -la", "risk_tier": 0}
   }
   ```
2. **Dynamic Risk Escalation:** Even if the LLM claims a command is Tier 0, the Shield parses the bash command. If it detects `sudo` or `rm`, it dynamically overrides the LLM's classification to Tier 3 or 4.
3. **The Sandbox:** For executing untrusted code (e.g., "Write and run a python script to test this API"), Nova uses **`bubblewrap` (`bwrap`)** or **`systemd-nspawn`** to create a temporary, unprivileged namespace. The script runs in an isolated environment with no network access and a read-only mount of the root filesystem.

---

## 🗺 5. Ground-Zero Execution Roadmap (Micro-Sprints)

As a solo developer, we do not use Agile/Scrum. We use **Deep Work Sprints**. Here is the exact day-by-day technical execution plan.

### Phase 1: The Sentinel & Core Loop (Days 1 - 15)
* **Day 1-2:** Initialize Git repo. Set up Python virtual environment. Configure `pyproject.toml` with `Poetry` or `uv` for dependency management.
* **Day 3-5:** **Build the C/Rust Listener.** Write the ALSA audio capture script. Implement the circular buffer. Integrate the `openwakeword` ONNX model. Profile memory to ensure it stays under 5MB.
* **Day 6-8:** **IPC Mechanism.** Implement the Unix Domain Socket or D-Bus service so the Listener can trigger the Python Cortex.
* **Day 9-11:** **The Cortex Event Loop.** Build the async Python core. Integrate `llama-cpp-python`. Load Qwen 2.5 Coder 3B (Q4_K_M). Test basic text-in, text-out streaming.
* **Day 12-15:** **Systemd Integration.** Write the `nova-sentinel.service` and `nova-cortex.service` files. Configure them to start on boot. Ensure the Cortex service is `Type=oneshot` or `dbus-activated` so it sleeps when not in use.

### Phase 2: Voice, Tools, and the Shield (Days 16 - 30)
* **Day 16-18:** **Audio Pipeline.** Integrate `faster-whisper` for STT. Route the audio captured by the Sentinel to the Cortex, transcribe it, and pass it to the LLM. Integrate `Piper TTS` for audio output.
* **Day 19-22:** **Tool Router.** Build the `@nova_tool` decorator system. Implement basic tools: `read_file`, `write_file`, `list_directory`.
* **Day 23-26:** **The Bash Executor & Shield.** Implement the `execute_bash` tool. Build the AST parser for risk classification. Implement the CLI prompt for Tier 2, 3, and 4 authorizations.
* **Day 27-30:** **End-to-End Voice Loop.** Connect everything. User says "NOVA", Sentinel wakes Cortex, Cortex transcribes, LLM generates tool call, Shield approves, bash executes, result is spoken back via TTS.

### Phase 3: Memory, Evolution, and Internet (Days 31 - 45)
* **Day 31-34:** **Vector DB Setup.** Initialize ChromaDB locally. Implement the embedding pipeline using `nomic-embed-text`.
* **Day 35-38:** **Context Injection.** Modify the LLM system prompt to dynamically retrieve and inject relevant memories from ChromaDB before every query.
* **Day 39-41:** **Habit Tracker.** Build the SQLite logging mechanism. Write the weekly DBSCAN clustering script to identify user routines.
* **Day 42-45:** **Internet Module.** Implement the `duckduckgo-search` tool. Build the "Permission Handshake" UI in the CLI. Implement the HTML-to-text parser for context injection.

### Phase 4: Cross-Distro Packaging & Polish (Days 46 - 60)
* **Day 46-50:** **The Universal Installer.** Write `install.sh`. This script must detect the distro (Kali, Ubuntu, Arch, Fedora) using `/etc/os-release` and install dependencies via `apt`, `pacman`, or `dnf`. It must also compile the C listener and download the GGUF models.
* **Day 51-54:** **Error Handling & Edge Cases.** Implement robust try/except blocks. Handle microphone disconnects, OOM (Out of Memory) kills, and LLM hallucinations (JSON parsing failures).
* **Day 55-58:** **CLI UI Polish.** Use the `Rich` library to make the terminal output beautiful. Add loading spinners, colored risk-tier warnings, and markdown rendering for LLM responses.
* **Day 59-60:** **Documentation & Launch.** Finalize `README.md`. Record a demo video. Push to GitHub. Post to r/Linux, r/KaliLinux, and Hacker News.

---

## 📂 6. Exhaustive Repository Structure

```text
project-nova/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                # Linting, type checking, and unit tests
│   │   └── release.yml           # Automated binary builds for the Sentinel
│   └── ISSUE_TEMPLATE/           # Bug reports and Feature requests
├── assets/
│   ├── models/                   # Git LFS for tiny wake-word models
│   └── sounds/                   # Wake word confirmation beep (optional)
├── docs/
│   ├── ARCHITECTURE.md           # Deep dive into the 4-layer architecture
│   ├── SECURITY_MODEL.md         # Detailed explanation of the Shield and SUDO tiers
│   └── CONTRIBUTING.md           # Guidelines for future contributors
├── nova-sentinel/                # The <5MB Background Listener (C/Rust)
│   ├── src/
│   │   ├── main.c                # Entry point, ALSA setup
│   │   ├── audio_buffer.c        # Circular buffer implementation
│   │   └── wake_word.c           # ONNX inference for wake word
│   ├── CMakeLists.txt            # Build configuration
│   └── README.md
├── nova-cortex/                  # The AI Brain & Orchestrator (Python)
│   ├── nova/
│   │   ├── __init__.py
│   │   ├── core/
│   │   │   ├── event_loop.py     # Asyncio main loop
│   │   │   ├── ipc_server.py     # Listens to Sentinel triggers
│   │   │   └── state.py          # Global state management
│   │   ├── llm/
│   │   │   ├── engine.py         # llama-cpp-python wrapper
│   │   │   ├── prompts.py        # System prompts and few-shot examples
│   │   │   └── context.py        # Sliding window and summarization logic
│   │   ├── audio/
│   │   │   ├── stt.py            # faster-whisper integration
│   │   │   └── tts.py            # Piper TTS integration
│   │   ├── tools/
│   │   │   ├── registry.py       # The @nova_tool decorator system
│   │   │   ├── bash_executor.py  # The core command execution tool
│   │   │   ├── file_ops.py       # Read/write/search files
│   │   │   └── web_search.py     # DuckDuckGo integration
│   │   ├── shield/
│   │   │   ├── classifier.py     # AST parser and risk tier assignment
│   │   │   ├── sandbox.py        # bubblewrap/systemd-nspawn wrapper
│   │   │   └── consent.py        # CLI prompts for user authorization
│   │   ├── memory/
│   │   │   ├── vector_db.py      # ChromaDB wrapper
│   │   │   ├── embeddings.py     # nomic-embed-text wrapper
│   │   │   └── habit_tracker.py  # SQLite logging and DBSCAN clustering
│   │   └── ui/
│   │       └── cli.py            # Rich library terminal UI
│   ├── tests/                    # Pytest unit and integration tests
│   ├── pyproject.toml            # Python dependencies (uv/poetry)
│   └── main.py                   # Cortex entry point
├── services/
│   ├── nova-sentinel.service     # Systemd unit for the listener
│   └── nova-cortex.service       # Systemd unit for the brain
├── install.sh                    # Universal distro-agnostic installer
├── uninstall.sh                  # Clean removal script
├── ProjectNova.md                # THIS MASTER DOCUMENT
└── README.md                     # Quick start and project overview
```

---

## 🐧 7. Cross-Distro Compatibility & The Universal Installer

A major challenge is ensuring Nova works on Kali, Ubuntu, Arch, and Fedora without manual dependency hell. The `install.sh` script is the solution.

### 7.1 Dependency Resolution Strategy
The installer will read `/etc/os-release` to determine the `ID` and `ID_LIKE`.

Before any model setup begins, the installer will also present a small interactive menu so the user can choose the LLM backend and the model source. The default path will prefer Ollama for the simplest offline-first flow, but the installer should also allow a local llama.cpp-style backend or a custom open-source model identifier when needed.

```bash
# Pseudo-code for install.sh dependency resolution
DISTRO_ID=$(grep ^ID= /etc/os-release | cut -d= -f2 | tr -d '"')

case "$DISTRO_ID" in
    kali|ubuntu|debian)
        sudo apt update
        sudo apt install -y portaudio19-dev python3-dev libsndfile1 cmake build-essential
        ;;
    arch|manjaro)
        sudo pacman -Syu --noconfirm portaudio python sndfile cmake base-devel
        ;;
    fedora|rhel)
        sudo dnf install -y portaudio-devel python3-devel libsndfile cmake gcc gcc-c++ make
        ;;
    *)
        echo "Unsupported distro. Please install dependencies manually."
        exit 1
        ;;
esac
```

### 7.2 Model Management
The installer will automatically check if `ollama` is installed. If not, it installs it. It then pulls the required models silently:
```bash
ollama pull qwen2.5-coder:3b
ollama pull nomic-embed-text
```

### 7.3 Systemd Service Activation
The installer will copy the `.service` files to `/etc/systemd/system/`, reload the daemon, and enable the Sentinel to start on boot:
```bash
sudo cp services/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now nova-sentinel.service
```

---

## 🧪 8. Testing Strategy for a System Agent

Testing an AI agent that executes bash commands is notoriously difficult. We cannot rely solely on standard unit tests.

### 8.1 The Mock OS Environment
For CI/CD and local unit testing, we cannot let the AI run real commands. 
* We will create a `MockFileSystem` and `MockShell` in Python.
* When the `bash_executor` tool is called during tests, it routes to the `MockShell`, which records the command and returns a predefined output, preventing actual system modification.

### 8.2 E2E "Sandbox" Testing
For End-to-End testing, we will use **Docker**. 
* The test suite will spin up a lightweight Alpine or Ubuntu Docker container.
* The test will inject a voice/text command into Nova running inside the container.
* It will assert that the correct files were created or modified *inside the container*, ensuring the logic works without risking the host Kali machine.

---

## 🚀 9. Immediate Next Steps for Manjil (Today)

You are starting from absolute zero. Here is your exact checklist for the next 48 hours to get the repository live and the foundation poured.

### Step 1: Repository Initialization (Hour 1)
1. Create the GitHub repository `project-nova`.
2. Clone it locally to your Kali machine.
3. Create the directory structure exactly as defined in Section 6.
4. Initialize the Python project:
   ```bash
   cd nova-cortex
   python3 -m venv venv
   source venv/bin/activate
   pip install uv
   uv init
   uv add llama-cpp-python faster-whisper piper-tts chromadb duckduckgo-search rich pydantic
   ```

### Step 2: The First Commit (Hour 2)
1. Copy this entire `ProjectNova.md` into the root directory.
2. Create a basic `README.md` that points to `ProjectNova.md`.
3. Add a comprehensive `.gitignore` (ignore `venv/`, `__pycache__/`, `*.gguf`, `.env`).
4. Commit and push:
   ```bash
   git add .
   git commit -m "feat: initialize project nova master blueprint and structure"
   git push origin main
   ```

### Step 3: Build the Sentinel Prototype (Days 2-4)
1. Do not worry about C/Rust yet. For the absolute first prototype, write the Sentinel in Python using `pyaudio` and `openwakeword`.
2. Accept that it will use 100MB+ RAM initially. **Get it working first, optimize later.**
3. Write a simple script that prints "WAKE WORD DETECTED" when you say "NOVA".
4. Once the logic is proven, *then* rewrite it in C to drop the RAM to <5MB.

---

<div align="center">

**Project Nova: Autonomy without Compromise. Intelligence without Limits.**

*Designed, Architected, and Built by Manjil Timalsina*  
*Contact: [timalsinamanjil04@gmail.com](mailto:timalsinamanjil04@gmail.com)*

</div>
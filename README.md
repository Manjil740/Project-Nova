# Project Nova

Project Nova is a Linux-only, offline-first local AI system designed to run fully on your machine without depending on cloud APIs. It combines a local LLM backend, Python runtime services, filesystem tooling, memory persistence, consent checks, and optional wake-word / overlay features into a single coherent assistant experience.

This repository is not a cross-platform app. It is intentionally built for modern Linux desktops and servers, with Unix domain sockets, systemd user services, local Ollama/llama.cpp backends, and Linux-native tooling.

---

## Project overview

Project Nova is designed around a few core principles:

- Fully local and offline-first
- Linux-only by design
- Runtime built around a Unix socket IPC contract
- Safe tool execution with review/consent gating
- Local memory, embeddings, and habit tracking
- Optional wake-word and UI overlay layers
- Simple setup for developers and Linux users

The runtime is organized as a modular Python package under:

- `nova-cortex/nova/`
- `nova-cortex/pyproject.toml`

The project root also contains the installation and service entry points:

- `install.sh` — headless CLI setup script
- `installer.py` — graphical installer
- `uninstall.sh` — headless cleanup script
- `uninstaller.py` — graphical uninstaller
- `services/` — systemd service templates

---

## Repository structure

```text
Project-Nova/
├── install.sh
├── installer.py
├── uninstall.sh
├── uninstaller.py
├── nova-open-terminal.sh
├── prompt.md
├── progress.md
├── TODO.md
├── HANDOFF.md
├── README.md
├── services/
│   ├── nova-cortex.service
│   └── nova-listener.service
├── nova-cortex/
│   ├── pyproject.toml
│   ├── README.md
│   └── nova/
│       ├── __init__.py
│       ├── main.py
│       ├── audio/
│       │   ├── __init__.py
│       │   ├── stt.py
│       │   ├── wake.py
│       │   └── tts.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   ├── errors.py
│       │   ├── event_loop.py
│       │   ├── events.py
│       │   ├── ipc_server.py
│       │   ├── platform.py
│       │   ├── report.py
│       │   ├── state.py
│       │   └── storage.py
│       ├── llm/
│       │   ├── client.py
│       │   ├── engine.py
│       │   ├── output.py
│       │   ├── pipeline.py
│       │   ├── prompts.py
│       │   └── schema.py
│       ├── memory/
│       │   ├── __init__.py
│       │   ├── embeddings.py
│       │   ├── habit_tracker.py
│       │   └── vector_db.py
│       ├── screen/
│       │   ├── __init__.py
│       │   └── capture.py
│       ├── shield/
│       │   ├── __init__.py
│       │   ├── classifier.py
│       │   ├── consent.py
│       │   └── sandbox.py
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── file_ops.py
│       │   └── registry.py
│       └── ui/
│           ├── __init__.py
│           ├── overlay.py
│           └── state_engine.py
└── services/
```

---

## How Nova works

### 1. Core runtime

The main runtime lives in the `nova.core` layer:

- `event_loop.py` starts the Cortex runtime
- `ipc_server.py` exposes the Unix socket and routes tool calls
- `state.py` tracks runtime state and counters
- `config.py` loads `.env` options and runtime configuration
- `platform.py` reads Linux distro details from `/etc/os-release`

Nova uses a single local IPC contract as the main interface. New features such as a wake-word listener or a UI overlay do not replace this core runtime; they connect to it as clients.

### 2. Tool router

The dispatcher is in `nova/tools/registry.py`.

It accepts commands such as:

- `status`
- `system_info`
- `list_directory`
- `read_file`
- `write_file`
- `execute_command`
- `memory_store`
- `memory_search`
- `screen_capture`

The router is the enforcement boundary for local actions.

### 3. Local LLM layer

The project expects a local back end such as:

- Ollama
- llama.cpp

This is configured through `nova/core/config.py` and the LLM bridge in:

- `nova/llm/client.py`
- `nova/llm/pipeline.py`
- `nova/llm/output.py`

The runtime is intended to keep all inference local to the machine. No mandatory cloud API is required.

### 4. Memory system

The memory stack uses:

- ChromaDB for persistent embeddings and semantic storage
- SQLite for habit tracking and local behavioral logs
- local embeddings through Ollama, typically `nomic-embed-text`

The memory modules are:

- `nova/memory/vector_db.py`
- `nova/memory/embeddings.py`
- `nova/memory/habit_tracker.py`

The project can store context from prior conversations and recent actions for future retrieval and learning.

### 5. Shield and consent model

Safety is intentionally implemented in the project’s own design:

- `nova/shield/classifier.py` assigns risk tiers
- `nova/shield/consent.py` decides whether a user approval is required
- `nova/shield/sandbox.py` checks for local sandboxing availability like `bubblewrap`

This matters for commands that could modify files or access system-level functions.

### 6. Wake-word and speech layer

The optional voice side includes:

- `nova/audio/wake.py` for wake-word detection
- `nova/audio/tts.py` for local speech output
- `nova/audio/stt.py` for transcription scaffolding

This is a Linux-only audio layer intended to run with local packages and user services.

### 7. Overlay UI

The overlay is a presentation-only layer:

- `nova/ui/state_engine.py`
- `nova/ui/overlay.py`

It reads Nova state and exposes user-friendly status strings such as “Listening…”, “Thinking…”, or “Opening Firefox…”. It does not replace the core runtime.

---

## Linux-only requirements

This project is designed for Linux only. That means:

- no Windows/macOS code paths
- no cross-platform branches for other OSes
- Unix domain socket IPC
- systemd user services
- Linux package manager assumptions (`apt`, `dnf`, `pacman`)
- X11 and Wayland awareness for overlays and capture tools

This is a hard project rule, not a preference.

---

## Setup guide

## Prerequisites

Before installing, make sure your system has:

- Python 3.11+
- `bash`
- `curl`
- `git`
- a working local package manager (`apt`, `dnf`, or `pacman`)
- a local LLM runtime such as Ollama or llama.cpp

You do not need to install all features at once. The project supports a staged setup.

## Recommended setup flow

### Option A — easiest path for most Linux users (Highly recommended)

1. Open a terminal in the project root.
2. Run:

```bash
cd / Project-Nova/Project-Nova
chmod +x install.sh
./install.sh
```

3. Follow the interactive prompts.
4. Choose your backend:
   - Ollama (recommended)
   - llama.cpp
   - custom/manual setup
5. Select a model or reuse an existing local model.
6. Let the installer generate `.env` values and install the local package.
7. Confirm the runtime and IPC checks pass.

### Option B — graphical installer

If you prefer a simpler desktop workflow:

```bash
cd / Project-Nova/Project-Nova
python3 -m venv venv
source venv/bin/activate
pip3 install PySide6
python3 installer.py
```

This opens a basic GUI selection screen for:

- backend selection
- model selection
- `.env` generation
- runtime install flow

### Option C — headless / developer mode

If you want a directly scripted install path:

```bash
cd Project-Nova/Project-Nova
python3 installer.py --headless --backend ollama --model qwen2.5-coder:3b
```

---

## Installing the local LLM backend

### Ollama (recommended)

Install it with the official installer:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Then start the service:

```bash
ollama serve
```

Pull a model(recommend):

```bash
ollama pull qwen2.5-coder:3b
```
# NOTE: User are free to use anymodel from ollama official site
or:

```bash
ollama pull llama3.2:3b
```

### llama.cpp

If using llama.cpp, make sure the CLI/server binary is installed and available in PATH, for example:

```bash
llama-server --help
```

or

```bash
llama-cli --help
```

Then match the selected backend and model in the config.

---

## Environment configuration

The project writes a `.env` file in the project’s `nova-cortex/` directory.

Typical entries look like this:

```env
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5-coder:3b
LLM_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text
SANDBOX_ENABLED=true
MEMORY_ENABLED=true
CHROMA_DB_PATH=~/.local/share/nova/chroma_db
EMBEDDING_BATCH_SIZE=8
DATA_DIR=~/.local/share/nova
```

This file is read by `NovaConfig.load()` and used by the runtime.

---

## Running Nova

From the project root:

```bash
cd / Project-Nova/Project-Nova
PYTHONPATH=nova-cortex python3 -m nova.main
```

This starts the local runtime and opens the main system loop.

If you want to run the open-terminal helper:

```bash
bash nova-open-terminal.sh
```

---

## Systemd services

The project includes service definitions in `services/`.

### Core service

`services/nova-cortex.service` starts the main runtime.

### Wake listener service

`services/nova-listener.service` starts the wake-word client and sends socket events to the main Nova runtime when the keyword is detected.

To install user services for the current user, run:

```bash
systemctl --user daemon-reload
systemctl --user enable --now nova-cortex.service
systemctl --user enable --now nova-listener.service
```

Check status:

```bash
systemctl --user status nova-cortex.service
systemctl --user status nova-listener.service
```

---

## Troubleshooting

### 1. Python package import issues

If Python cannot import `nova`:

```bash
cd / Project-Nova/Project-Nova
export PYTHONPATH=$(pwd)/nova-cortex
python3 -m nova.main
```

### 2. Local LLM is not detected

Check whether Ollama is installed and running:

```bash
ollama list
ollama serve
```

If using `llama.cpp`, verify the binary is on your PATH:

```bash
which llama-server
which llama-cli
```

### 3. `.env` not generated

Generate it manually or rerun the installer:

```bash
cd / Project-Nova/Project-Nova
python3 installer.py
```

### 4. Service fails to start

Check logs:

```bash
journalctl --user -u nova-cortex.service -f
journalctl --user -u nova-listener.service -f
```

### 5. Path issues / blocked actions

Nova intentionally restricts file resolution to the project root. If you attempt to access paths outside the project folder, it will reject them with a `path_outside_workspace` error.

### 6. Resolve local dependencies

If the runtime complains about missing libraries, install them using pip or your distro package manager:

```bash
python3 -m pip install -e nova-cortex
```

For the optional wake-word detector, use a supported Python version and install the voice extra:

```bash
python3.12 -m pip install -e nova-cortex[voice]
```

If you are on Python 3.13, the core project still installs normally, but `openwakeword` will remain unavailable because the dependency currently has no compatible Linux wheel for that interpreter.

Core packages are:

```bash
python3 -m pip install PySide6 chromadb scikit-learn requests
```

---

## Recommended initial validation commands

Run these after setup:

```bash
cd / Project-Nova/Project-Nova
python3 -m py_compile installer.py uninstaller.py
bash -n install.sh
bash -n uninstall.sh
PYTHONPATH=nova-cortex python3 -m compileall nova-cortex/nova
```

Then test the runtime:

```bash
cd / Project-Nova/Project-Nova
PYTHONPATH=nova-cortex python3 -m nova.main
```

---

## Uninstalling

Headless uninstall:

```bash
cd / Project-Nova/Project-Nova
bash uninstall.sh
```

Graphical uninstall:

```bash
cd / Project-Nova/Project-Nova
python3 uninstaller.py
```

This removes generated runtime files, `.env`, and user service files while leaving your local Ollama install intact unless you choose to remove it manually.

---

## Important safety notes

Project Nova can perform:

- local file reads and writes
- shell command execution
- local model calls
- optional wake-word and overlay actions

Because of this, it includes an approval gate for risky operations. Treat the system as a local assistant with real power, not as a sandboxed toy. 

Always review prompts before approving execution actions.

---

## Current project status

The repository is currently in a staged implementation state with the main areas working or scaffolded:

- runtime core
- tool router
- system profile detection
- local LLM bridge
- local memory components
- safety gating
- optional screen capture
- packaging and installer flow

The project remains deliberate about staying local, Linux-native, and privacy-respecting.

---

## Contribution / continuation notes

This project is designed for continuation across sessions. If you are resuming work, the main files to read first are:

- `prompt.md`
- `progress.md`
- `TODO.md`
- `nova-cortex/nova/core/event_loop.py`
- `nova-cortex/nova/tools/registry.py`
- `nova-cortex/nova/llm/client.py`
- `nova-cortex/nova/memory/`

---

## Final note

Project Nova is intended to be a local Linux assistant that remains private, controlled, and understandable. It is not meant to be a cloud-connected service or a cross-platform abstraction layer. The goal is to provide a practical local AI runtime that runs on your own machine with transparency and safety in mind.




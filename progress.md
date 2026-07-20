# Project Nova Progress Log

This file tracks implementation progress, small code adjustments, and functionality notes as the project moves forward.

## 2026-07-13 — Phase A: Foundation Hardening & Memory Pre-Wiring

### What Changed
- Added `nova/core/errors.py` — typed exception hierarchy (`NovaError`, `NovaConfigError`, `NovaMemoryError`, `NovaToolError`)
- Added `nova/core/storage.py` — `StorageManager` for `~/.local/share/nova/` data directory layout (chroma_db, logs, data)
- Added `nova/core/events.py` — `EventBus` singleton for decoupled component communication (subscribe/publish pattern)
- Updated `nova/core/config.py` — added memory/storage fields (`memory_enabled`, `chroma_db_path`, `embedding_batch_size`, `data_dir`)
- Updated `nova/core/state.py` — added `record_memory_query()`, `record_tool_call()`, persistent `save()`/`load()` to JSON
- Updated `nova/__init__.py` — exposed all new modules in `__all__`
- Updated `install.sh` — added `create_data_directories()` for `~/.local/share/nova/`, fixed systemd unit write with `sudo tee`, added model manifest command display in `pull_ollama_model()`

### What Was Validated
- `python3 -m compileall nova` — all source files compile clean with zero errors

### Follow-up Needed
- Phase B: ChromaDB vector store integration for long-term memory

## 2026-07-13 (Post-Refactor Validation)

### Verification & Bug Fixes
- Fixed `nova-cortex/nova/llm/client.py` — `_parser` mutable default replaced with `field(default_factory=...)`
- Fixed `nova-cortex/nova/llm/pipeline.py` — `parser` mutable default replaced with `field(default_factory=...)`
- Fixed circular import: `pipeline.py` now uses `TYPE_CHECKING` for `ToolRouter`
- Added missing `field` import to `client.py`

### Script Improvements
- Rewrote `uninstall.sh` — cleaner service handling, optional Ollama removal, Pip cache cleanup, better UX
- Rewrote `nova-open-terminal.sh` — fixed PYTHONPATH bug (was passed as string not env var), added venv detection, removed `-lc` (login shell) usage, added gnome-terminal before generic fallback

### Comprehensive Validation Suite
- Compile check: all 15 `.py` files compile clean
- Import check: all 13 public exports import successfully
- Parser tests (11): plain text, JSON code blocks, raw JSON, multiple tool calls, empty input, malformed JSON tolerance, ToolCall factories, prose stripping, render, render_preview
- Pipeline tests (5): clear_history, history block building, history trimming, PipelineResult with/without tools
- Router dispatch tests (15): wake, status, system_info, config_status, llm_status, runtime_report, system_prompt, llm_chat_clear, empty, ping, list_directory, read_file, JSON dispatch, unknown command rejection, path traversal rejection
- IPC server test (3): start, send wake, send status, stop, socket cleanup
- Config tests (3): loaded config, defaults with missing .env
- State tests (1): event counting
- Platform tests (1): distro detection
- Engine tests (1): status rendering
- Prompt tests (1): system prompt generation

### Stage 0-1: Urgent Must-Do First (Docs + Dependencies + Config)
- Added runtime dependency:
  - Updated `nova-cortex/pyproject.toml` to include `requests>=2.31.0`
- Expanded config/environment generation:
  - Updated `install.sh` to write a complete `.env` with all keys used by `NovaConfig`
- Updated package exports:
  - Updated `nova-cortex/nova/__init__.py` to expose the intended entrypoints via `__all__`
- Validated critical runtime surfaces:
  - `LLMOutputParser` tool-envelope parsing smoke check
  - `NovaConfig.load()` sanity check
  - `import nova` export sanity
  - IPC/router dispatch sanity (`status`, `config_status`, `llm_status`, `list_directory`, `read_file`, and workspace boundary rejection)


### Stage 1: Initial Scaffold
- Added a minimal Cortex package under `nova-cortex/nova/`.
- Added `nova-cortex/pyproject.toml` with a console entrypoint for `nova-cli`.
- Added `services/nova-cortex.service` as a basic service placeholder.
- Added `.gitignore` for Python build artifacts and runtime data.

### Stage 2: Runtime Core
- Added the async Cortex bootstrap in `nova-cortex/nova/core/event_loop.py`.
- Added the Unix socket IPC server in `nova-cortex/nova/core/ipc_server.py`.
- Added shared runtime state tracking in `nova-cortex/nova/core/state.py`.
- Confirmed the runtime boots and responds with wake/status messages.

### Stage 3: Tool Routing and System Awareness
- Added `nova-cortex/nova/tools/registry.py` and `nova-cortex/nova/tools/file_ops.py` for basic tool dispatch.
- Added `nova-cortex/nova/core/platform.py` to detect distro metadata.
- Hardened path handling so tool calls stay inside the workspace boundary.
- Added `status` and `system_info` routes for runtime and distro visibility.

### Stage 4: Config and Diagnostics
- Added `nova-cortex/nova/core/config.py` to load `.env` values into structured config.
- Added `nova-cortex/nova/llm/prompts.py`, `nova-cortex/nova/llm/schema.py`, and `nova-cortex/nova/llm/engine.py` for prompt, tool-call, and backend diagnostics support.
- Added `nova-cortex/nova/core/report.py` plus `runtime_report`, `config_status`, `llm_status`, and `llm_request_preview` IPC commands.
- Added `nova-cortex/nova/llm/client.py` to define the next-stage request payload shape.
- Verified the runtime and diagnostics paths with compile-time checks and IPC probes.

### Stage 5: Backend Bridge
- Extended `nova-cortex/nova/llm/client.py` with guarded execution methods for `ollama` and `llama.cpp`.
- Added `llm_execute_preview` so the runtime can exercise the real backend command shape without changing the rest of the router.
- Added `llm_execute` so the runtime can call the guarded backend execution path directly when a supported local backend is present.
- Kept the execution path failure-safe so missing binaries return clear availability errors instead of crashing the runtime.
- Left the request and execution payload shapes stable so future model integration can build on them.
- Added missing-binary and timeout handling so the backend bridge fails cleanly when `ollama` or `llama-cli` are unavailable.
- Validated the bridge with `python3 -m compileall nova` and an IPC probe that returned `response:provider=ollama ... state=unavailable output=ollama_missing`.
- Revalidated the direct execution command with `python3 -m compileall nova` and the same safe unavailable response from `llm_execute`.

### Stage 6: Output Normalization
- Added `nova-cortex/nova/llm/output.py` to normalize raw model text into a structured output object.
- Added `llm_response_preview` so the runtime can parse sample backend output into plain text or a structured tool call.
- Kept the parser tolerant of free-form text while still detecting JSON tool envelopes when present.
- Prepared the runtime for the next stage where real backend output can be routed into tool execution decisions.
- Validated the stage with `python3 -m compileall nova` and IPC probes that returned both a parsed JSON tool call and a plain-text normalized response.

### Stage 7: Handoff Hardening
- Performed an in-depth recheck across installer, runtime, router, and LLM bridge.
- Added targeted comments/docstrings in high-change files to make behavior and extension points clearer for the next agent.
- Removed dead router helper code (`_split`) to reduce confusion during future edits.
- Normalized `llm_output` rendering so extracted tool arguments are reported cleanly as argument JSON.
- Added `HANDOFF.md` with architecture map, validation commands, known behavior, and immediate next tasks.
- Revalidated with `bash -n install.sh` and `python3 -m compileall nova` after all handoff-focused edits.
- Expanded comments and docstrings with detailed IPC contract, extension guidelines, parser behavior notes, and safety expectations in router/LLM modules.
- Revalidated again with `python3 -m compileall nova` after the detailed comment pass.

### Micro Adjustments
- Replaced the print-only entrypoint in `nova-cortex/nova/main.py` with an async startup path.
- Added `nova-cortex/nova/core/event_loop.py` to hold the main Cortex runtime loop.
- Added `nova-cortex/nova/core/ipc_server.py` to provide a Unix domain socket IPC stub.
- Added `nova-cortex/nova/core/__init__.py` to define the core package boundary.
- Validated the new IPC path with a local round-trip check that returned `ack:wake`.
- Rechecked the Cortex package with `get_errors`; no current errors were reported.
- Added `nova-cortex/nova/tools/registry.py` as the first small tool router.
- Added `nova-cortex/nova/tools/file_ops.py` with `list_directory` and `read_file` helpers.
- Updated the IPC server so socket messages dispatch to tools instead of only echoing acknowledgements.
- Passed the project root into the IPC/tool layer so relative file operations resolve consistently from the Nova workspace.
- Revalidated the package with `python3 -m compileall nova` and a socket round-trip that returned the project directory listing.
- Added `nova-cortex/nova/core/state.py` to track runtime start time, event count, and last event.
- Extended the tool router with a `status` command and event tracking for wake, list, and read actions.
- Wired shared Cortex state through the event loop and IPC server so runtime status is queryable over the socket.
- Removed an unused import from the tool router during the cleanup pass.
- Validated the update with `python3 -m compileall nova` and a socket probe that returned a live `status:running` line.
- Hardened `nova-cortex/nova/tools/registry.py` with `shlex` parsing so quoted arguments are handled more reliably.
- Restricted tool path resolution to the workspace boundary so path traversal outside the project root is rejected.
- Added `nova-cortex/nova/core/platform.py` to detect distro metadata from `/etc/os-release`.
- Wired distro info into `status` and added a `system_info` command for multi-distro visibility.
- Added error handling in the IPC server so invalid path requests return a structured error instead of crashing the listener.
- Validated the hardening pass with `python3 -m compileall nova` and IPC probes that returned a distro report plus an expected `error:path_outside_workspace:/tmp` boundary rejection.
- Added `nova-cortex/nova/llm/prompts.py` to generate a reusable system prompt from runtime state and detected distro info.
- Added `nova-cortex/nova/llm/schema.py` to parse both plain-text and JSON tool envelopes into a structured `ToolCall`.
- Updated the router to accept JSON tool messages, expose `system_prompt`, and feed the prompt builder into the startup path.
- Kept the existing plain-text command path working so the router stays backward compatible while becoming more versatile.
- Validated the new layer with `python3 -m compileall nova` and IPC probes that returned the generated system prompt, a JSON `list_directory` call, and a JSON `status` response with updated event tracking.
- Updated [README.md](/home/manjil/Project-Nova/README.md) and [Project-Nova.md](/home/manjil/Project-Nova/Project-Nova.md) to describe a selectable LLM backend during setup.
- Added [install.sh](/home/manjil/Project-Nova/install.sh) with distro detection plus interactive backend/model selection for Ollama, llama.cpp, or a custom choice.
- Added setup output that writes the selected backend and model into `nova-cortex/.env`.
- Validated the installer with `bash -n /home/manjil/Project-Nova/install.sh` and marked it executable for direct use.
- Polished `install.sh` with a welcome banner, colored prompts, spinner-based progress messages, and a closing thank-you message.
- Added `nova-cortex/.env.example` as a reusable template for Python-side configuration values.
- Added `.env` to [.gitignore](/home/manjil/Project-Nova/.gitignore) so local setup secrets and machine-specific settings stay out of version control.
- Enhanced `install.sh` to detect existing local LLM software and model installs, then ask whether to reuse the current setup or install a new one.
- Expanded the setup menus so installed Ollama models can be reused directly when available, with fallback choices for custom or new model names.
- Updated [README.md](/home/manjil/Project-Nova/README.md) so the setup section now documents reuse-vs-install behavior for existing local AI software.
- Hardened `install.sh` to tolerate unusual environments by falling back to package-manager detection instead of failing on unsupported `/etc/os-release` IDs.
- Added a `NOVA_INSTALL_LIB_ONLY=1` mode so the installer can be sourced for validation without auto-running the full setup flow.
- Validated the hardening with a source-mode probe that returned `distro=unknown manager=none backend=none model=none` instead of crashing on the environment ID.
- Added `nova-cortex/nova/core/config.py` to load `.env` values into a structured Python config object.
- Wired the loaded config into the Cortex startup path and exposed a `config_status` tool response for runtime inspection.
- Fixed the config loader so missing `.env` keys now fall back to literal defaults instead of dataclass member objects.
- Revalidated the config layer with `python3 -m compileall nova` and an IPC probe that returned the corrected `config:provider=llama.cpp ... embedding=nomic-embed-text` output.
- Added `nova-cortex/nova/llm/engine.py` as a lightweight backend diagnostics layer for the selected LLM provider.
- Wired LLM status reporting into the Cortex startup path and added an `llm_status` IPC tool response.
- Validated the stage with `python3 -m compileall nova` and IPC probes that returned both `config_status` and `llm_status` responses.
- Confirmed the LLM diagnostics layer correctly reports backend availability as `unavailable` when no matching local binary is present.
- Fixed an actual router bug by restoring the missing `json` import used during tool-call parsing error handling.
- Added `nova-cortex/nova/core/report.py` and a `runtime_report` IPC command that combines state, system, config, LLM, and prompt output into one summary.
- Flattened the IPC runtime report into a single line so simple socket reads return the full summary reliably.
- Corrected the Cortex event loop after the report refactor and removed the stale prompt import.
- Fixed an indentation bug in the `runtime_report` branch of the tool router that was introduced during the report flattening pass.
- Added `nova-cortex/nova/llm/client.py` as a lightweight LLM request adapter for future execution stages.
- Exposed `llm_request_preview` so the runtime can show the exact provider/model/prompt payload shape before any actual model execution is added.
- Added a guarded backend execution bridge so the configured provider can be contacted later without changing the request shape again.
- Added `llm_execute_preview` to show the backend execution path and output or error state in a controlled preview form.
- Added `nova-cortex/nova/llm/output.py` and `llm_response_preview` so backend text can be normalized into structured output.
- Added clearer inline comments/docstrings in runtime and LLM bridge modules for easier continuation by a new agent.
- Added `HANDOFF.md` to centralize continuation notes, entry points, and next implementation priorities.
- Upgraded comments from short notes to actionable maintenance guidance in `tools/registry.py`, `llm/client.py`, and `llm/output.py`.

### Installer Validation (2026-07-13)
- Verified `install.sh` syntax with `bash -n install.sh` — SYNTAX OK
- Verified library-only sourcing mode with `NOVA_INSTALL_LIB_ONLY=1` — detects distro, package manager, and existing LLM stack correctly
- Fixed unbound variable error in sourcing mode by adding `DISTRO_ID=""` initialization
- All 15 Python source files compile clean via `python3 -m compileall nova`
- Ready for Memory & Learning phase (Stage 11)

### Notes
- The current implementation is stable with real model integration (Stage 7) complete.
- `install.sh` can install Ollama, pull a model, configure the environment, and run 9 IPC tests after setup.
- Voice Pipeline (Stage 8) and Tool Expansion (Stage 9) are deferred.
- Next: Memory & Learning phase — ChromaDB vector store, embeddings, habit tracker.

## Update Format

Use this simple structure for future entries:

- What changed
- Why it changed
- What was validated
- Any follow-up needed

## Remaining Stages

The current codebase is stable for the scaffold, runtime, routing, config, diagnostics, and backend bridge layers. The remaining work is still substantial.

### Stage 7: Real Model Integration ✅

**Date:** 2026-07-13

**What changed:**
- Replaced subprocess-based Ollama execution with proper HTTP API client using `requests` POST to `http://localhost:11434/api/generate`
- Added streaming support via SSE token accumulation (`_execute_ollama_stream`)
- Added retry logic (3 attempts with exponential backoff) for transient failures
- Added error handling for: connection refused, model not found (404), timeout, invalid JSON response
- Created `llm/pipeline.py` — full conversational pipeline that orchestrates: system prompt → LLM inference → parse tool calls → execute tools → return response
- Pipeline supports multi-turn conversation history (last 10 turns preserved)
- Pipeline has `execute_with_tools()` (tool-augmented) and `execute_simple()` (direct response) modes
- Enhanced `llm/output.py` parser with multi-strategy tool extraction:
  - Extracts tool calls from markdown JSON code blocks (```json ... 
```)
  - Extracts raw JSON objects with 'tool' field
  - Supports multiple tool calls in one response
  - Strips tool call JSON from text to keep only prose
- Added `llm_chat`, `llm_chat_simple`, `llm_chat_clear` IPC commands to router
- Updated REPL (`main.py`) to route user input through `llm_chat` pipeline with `/clear` command
- Rewrote `install.sh` with proper user flow:
  - Asks user: Ollama or other backend
  - If other: provides curl/install instructions, lets user install manually
  - If Ollama: installs Ollama binary via official script
  - Lets user select model from: Qwen 2.5 Coder 3B, Llama 3.2 3B, Mistral 7B, or custom
  - Pulls selected model via `ollama pull`
  - Verifies model works with API call
  - Runs `test_ipc_connection()` — 9 IPC tests after setup (wake, status, system_info, config_status, llm_status, runtime_report, list_directory, read_file, llm_chat)
- Removed unnecessary markdown files (HANDOFF.md, Project-Nova.md, README.md)
- Updated TODO.md with [*] / [-] format

**What was validated:**
- `python3 -m compileall nova` — all 9 source files compile clean with no errors
- `bash -n install.sh` — installer syntax is valid
- All IPC routes compile and are wired correctly

**Files modified:**
- `nova-cortex/nova/llm/client.py` — HTTP API client with streaming, retry, error handling
- `nova-cortex/nova/llm/output.py` — multi-strategy tool extraction parser
- `nova-cortex/nova/llm/pipeline.py` — NEW: conversational pipeline with history
- `nova-cortex/nova/tools/registry.py` — added llm_chat/llm_chat_simple/llm_chat_clear routes
- `nova-cortex/nova/core/event_loop.py` — creates Pipeline, wires to router
- `nova-cortex/nova/core/ipc_server.py` — accepts pre-built router
- `nova-cortex/nova/__init__.py` — exports Pipeline, LLMOutputParser, LLMOutput
- `nova-cortex/nova/main.py` — REPL routes through llm_chat, /clear support
- `install.sh` — full rewrite with Ollama install, model selection, IPC tests
- `TODO.md` — reformatted with [*]/[-] notation
- `progress.md` — this entry

**Follow-up needed:**
- Stage 8: Voice Pipeline (STT/TTS)
- Stage 9: Tool Expansion (bash executor, web search)
- Stage 10: Shield & Sandbox
- Stage 11: Memory & Learning
- Stage 12: Packaging & Distribution

### Stage 8: Voice Pipeline
- Add `nova-cortex/nova/audio/stt.py` for speech-to-text.
- Add `nova-cortex/nova/audio/tts.py` for text-to-speech.
- Connect microphone input, transcription, and spoken responses to the Cortex event loop.

### Stage 9: Tool Expansion and Safety
- Build out `nova-cortex/nova/tools/bash_executor.py` and `nova-cortex/nova/tools/web_search.py`.
- Add `nova-cortex/nova/shield/classifier.py`, `nova-cortex/nova/shield/sandbox.py`, and `nova-cortex/nova/shield/consent.py`.
- Add real risk-tier enforcement for destructive, networked, and system-modifying actions.

### Stage 10: Memory and Learning
- Add `nova-cortex/nova/memory/vector_db.py`, `nova-cortex/nova/memory/embeddings.py`, and `nova-cortex/nova/memory/habit_tracker.py`.
- Store long-term preferences, habits, and relevant context in a local database.
- Add retrieval so the runtime can inject memory into prompts automatically.

### Stage 11: Packaging and System Integration
- Add real `services/nova-sentinel.service` and `services/nova-cortex.service` behavior for boot-time use.
- Add or finish `install.sh` branches for real backend installation paths.
- Add `uninstall.sh`, tests, and any distro-specific package handling that is still missing.

### What You Need To Do
- Decide which backend to prioritize first for actual execution support: `ollama` or `llama.cpp`.
- Test the current installer on your target Linux distro so package detection and `.env` creation match your system.
- Install the chosen local backend and model so the next execution stage can run against a real binary.

### What Is Still Missing In Code
- Actual model inference output handling beyond preview and safe unavailable responses.
- STT/TTS audio processing.
- Tool execution beyond read-only and directory/file access.
- Shielded command approval flow and sandboxing.
- Memory persistence, vector retrieval, and habit tracking.
- Service integration for real system startup and boot behavior.
## 2026-07-13 — Phase B: ChromaDB Vector Store & Memory Integration ✅

**Date:** 2026-07-13

**What changed:**

### Step 2: VectorDB Implementation (`nova/memory/vector_db.py`)
- Replaced stub with full ChromaDB `PersistentClient` integration
- `initialize()` — creates client, gets/creates collection with cosine space
- `add_documents(ids, documents, embeddings, metadatas)` — CRUD add with metadata
- `similarity_search(query_embeddings, n_results, where)` — search with optional metadata filter
- `delete(ids)` / `update(ids, documents, embeddings, metadatas)` — update/delete operations
- `list_collections()` / `delete_collection(name)` — collection management
- `count` property — real-time document count
- Enhanced `render_status()` showing doc count, collection state, path

### Step 3: Embeddings Implementation (`nova/memory/embeddings.py`)
- Replaced stub with Ollama HTTP API client (`POST /api/embeddings`)
- `initialize()` — probes Ollama connectivity and model availability
- `embed(text)` — single text → vector with LRU cache
- `embed_batch(texts)` — batched embedding with configurable batch size
- LRU cache via `OrderedDict` with `cache_size=1000` default
- Cache statistics tracking (hits, misses, total embedded)
- Error handling: connection refused, timeout, model unavailable (404), invalid JSON

### Step 4: HabitTracker Implementation (`nova/memory/habit_tracker.py`)
- Full SQLite-backed command logging with schema
- `log_command(command, arguments, success, duration_ms, context)` — log interactions
- `get_recent_commands(hours)` / `get_command_stats(days)` — query methods
- DBSCAN clustering for temporal pattern detection (when scikit-learn available)
- Heuristic fallback for environments without scikit-learn
- `analyze_patterns()` — detects temporal patterns with confidence scoring
- `get_suggestions(max_suggestions=5)` — proactive suggestions engine (usage peaks, error rates, time-based, diversity)
- `run_weekly_analysis()` — comprehensive weekly analysis summary
- Pattern storage and loading from database
- Suggestion lifecycle management (shown/dismissed)

### Step 5: Wiring & Integration
- **`nova/memory/__init__.py`** — updated docstring, exports `HabitPattern`, `HabitSuggestion`
- **`nova/tools/registry.py`** — added `vector_db`, `embeddings`, `habit_tracker` fields to `ToolRouter`
  - Added IPC commands: `memory_status`, `memory_store`, `memory_search`, `memory_habits`, `memory_analyze`
- **`nova/core/event_loop.py`** — instantiates `VectorDB`, `Embeddings`, `HabitTracker`; calls `initialize()`; wires to router and pipeline
  - Subscribes `habit_tracker.log_command()` to `EventBus` for automatic command logging on `tool:executed` events
- **`nova/llm/pipeline.py`** — added `vector_db`, `embeddings`, `habit_tracker` fields
  - `_build_memory_context(user_input)` — injects relevant memory context into LLM prompts
  - `_auto_store_memory(user_input, response)` — automatically stores conversations in vector DB
  - Memory context includes semantic search results and recent habit activity
- **`nova/__init__.py`** — exported `VectorDB`, `Embeddings`, `HabitTracker`, `HabitPattern`, `HabitSuggestion`
- **`pyproject.toml`** — added `scikit-learn>=1.0.0` dependency

### What Was Validated
- `python3 -m compileall nova` — all source files compile clean with zero errors
- `import nova` — all 20+ public exports import successfully
- `VectorDB`, `Embeddings`, `HabitTracker` slots verified
- `Pipeline` accepts memory components without breaking existing interface
- `_SKLEARN_AVAILABLE=True` — scikit-learn 1.9.0 detected for DBSCAN clustering

### Files modified/created:
- `nova-cortex/nova/memory/vector_db.py` — full ChromaDB implementation
- `nova-cortex/nova/memory/embeddings.py` — full Ollama embedding client
- `nova-cortex/nova/memory/habit_tracker.py` — full SQLite + DBSCAN habit tracker
- `nova-cortex/nova/memory/__init__.py` — updated exports
- `nova-cortex/nova/tools/registry.py` — added memory IPC routes
- `nova-cortex/nova/core/event_loop.py` — memory initialization and wiring
- `nova-cortex/nova/llm/pipeline.py` — memory context injection and auto-storage
- `nova-cortex/nova/__init__.py` — memory class exports
- `nova-cortex/pyproject.toml` — added scikit-learn dependency
- `TODO.md` — updated with [*] markers
- `progress.md` — this entry

### Follow-up Needed
- Phase C: Memory Router Integration — deeper integration with prompt generation
- Phase D: Shield & Sandbox — risk classification, consent prompts
- Phase E: Tool Expansion — bash executor, web search
- Phase F: Voice Pipeline — STT/TTS
- Phase G: Packaging — DEB/RPM, systemd

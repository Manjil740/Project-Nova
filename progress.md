# Project Nova Progress Log

This file tracks implementation progress, small code adjustments, and functionality notes as the project moves forward.

## 2026-07-10

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

### Notes
- The current implementation is still a scaffold. It now boots a minimal async runtime and accepts local socket triggers, but it does not yet load an LLM, STT/TTS, or tool router.
- Future updates should append new dated entries here with both code changes and behavior changes.

## Update Format

Use this simple structure for future entries:

- What changed
- Why it changed
- What was validated
- Any follow-up needed

## Remaining Stages

The current codebase is stable for the scaffold, runtime, routing, config, diagnostics, and backend bridge layers. The remaining work is still substantial.

### Stage 7: Real Model Integration
- Implement a real response path for `ollama` and `llama.cpp` instead of only preview and availability reporting.
- Convert backend output into structured tool decisions and normal assistant text.
- Add streaming support if the chosen backend can provide incremental tokens.

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
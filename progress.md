# Project Nova Progress Log

This file tracks implementation progress, small code adjustments, and functionality notes as the project moves forward.

## 2026-07-10

### Stage 1: Initial Scaffold
- Added a minimal Cortex package under `nova-cortex/nova/`.
- Added `nova-cortex/pyproject.toml` with a console entrypoint for `nova-cli`.
- Added `services/nova-cortex.service` as a basic service placeholder.
- Added `.gitignore` for Python build artifacts and runtime data.

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

### Notes
- The current implementation is still a scaffold. It now boots a minimal async runtime and accepts local socket triggers, but it does not yet load an LLM, STT/TTS, or tool router.
- Future updates should append new dated entries here with both code changes and behavior changes.

## Update Format

Use this simple structure for future entries:

- What changed
- Why it changed
- What was validated
- Any follow-up needed
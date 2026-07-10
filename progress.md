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

### Notes
- The current implementation is still a scaffold. It now boots a minimal async runtime and accepts local socket triggers, but it does not yet load an LLM, STT/TTS, or tool router.
- Future updates should append new dated entries here with both code changes and behavior changes.

## Update Format

Use this simple structure for future entries:

- What changed
- Why it changed
- What was validated
- Any follow-up needed
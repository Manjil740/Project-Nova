# Project Nova — Handoff

## Architecture overview
- Core runtime: `nova-cortex/nova/core/`
  - `event_loop.py` starts the Cortex app and memory initialization
  - `ipc_server.py` exposes a Unix-domain socket for tool dispatch
  - `state.py` tracks runtime state and counters
  - `config.py` loads `.env` values into a structured config
  - `platform.py` reads Linux distro information from `/etc/os-release`
- LLM bridge: `nova-cortex/nova/llm/`
  - `client.py` handles local backend adapters
  - `output.py` normalizes mixed text/tool responses
  - `pipeline.py` executes conversational tool-aware flow
- Tools: `nova-cortex/nova/tools/`
  - `registry.py` routes tool calls and now enforces the Guard/Shield gate
  - `file_ops.py` provides file and shell operations
- Safety: `nova-cortex/nova/shield/`
  - `classifier.py` assigns risk tiers
  - `consent.py` requires explicit approval for risky actions
  - `sandbox.py` reports Linux sandbox availability
- Voice/UI: `nova-cortex/nova/audio/` and `nova-cortex/nova/ui/`
  - wake-word listener, TTS, STT scaffolding
  - overlay/state engine for a transparent presentation layer

## Current validated state
- The Nova runtime compiles successfully.
- The Unix-socket IPC contract remains active.
- The shield gate blocks dangerous writes without consent and allows them with explicit approval.
- The graphical installer and uninstaller entrypoints are present and callable via Python GUI or CLI headless mode.

## Validation commands
- `cd / Project-Nova/Project-Nova && PYTHONPATH=nova-cortex python3 -m compileall nova-cortex/nova`
- `cd / Project-Nova/Project-Nova && bash -n install.sh && bash -n uninstall.sh`
- `cd / Project-Nova/Project-Nova && PYTHONPATH=nova-cortex python3 - <<'PY' ...` router smoke tests for consent enforcement

## Known limitations
- `openwakeword` and `PySide6` must be installed in the target environment before live voice and overlay use.
- `bubblewrap` is required for active sandbox isolation; on machines without it, sandboxing is reported as unavailable.
- Memory integration is still not fully wired into every prompt or persistence flow.

## Immediate next task
- Continue with the Stage 9B screen-awareness path or the memory integration layer, depending on the user’s preference.

# Project Nova Handoff

This file is for the next development agent to continue work quickly.

## Current Runtime State

- The Cortex runtime boots and listens over a Unix socket.
- Commands are routed through `nova-cortex/nova/tools/registry.py`.
- `.env` config is loaded by `nova-cortex/nova/core/config.py`.
- LLM bridge supports:
  - request preview
  - guarded execute preview
  - guarded execute
  - output normalization preview

## Key Entry Points

- `nova-cortex/nova/main.py`: process entrypoint.
- `nova-cortex/nova/core/event_loop.py`: app bootstrap and service lifecycle.
- `nova-cortex/nova/core/ipc_server.py`: Unix socket server.
- `nova-cortex/nova/tools/registry.py`: command router.
- `nova-cortex/nova/llm/client.py`: backend bridge (ollama/llama.cpp).
- `nova-cortex/nova/llm/output.py`: output parser for tool envelopes.

## Known Behavior

- If local model binaries are missing, LLM execution returns `state=unavailable`.
- `runtime_report` is flattened to one line for simple clients.
- Path arguments are restricted to the project workspace boundary.

## Quick Validation Commands

From repository root:

```bash
bash -n install.sh
cd nova-cortex && python3 -m compileall nova
```

## Immediate Next Steps

1. Implement real backend inference path (prefer Ollama first).
2. Route normalized tool envelopes into tool execution decisions.
3. Add tests for router dispatch and output parser edge cases.
4. Start Stage 8 (audio STT/TTS modules) after stable model-response loop.

## Notes For Next Agent

- Keep router command contracts backward compatible where possible.
- Preserve failure-safe behavior: never crash on malformed model output.
- Update `progress.md` stage summaries and micro-adjustments after each change.
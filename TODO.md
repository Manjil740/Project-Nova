# Project Nova - Development Todo List

## Legend
- [*] = Done
- [-] = Not Done

---

## 🎯 Current Status
- **Phase:** Stage 7 (Real Model Integration) - Complete
- **Critical Blockers:** None
- **Last Updated:** 2026-07-13

---

## Stage 0: Urgent Must-Do First
- [*] Add `requests>=2.31.0` to `pyproject.toml`
- [*] Expand `.env` generation in `install.sh` with all config keys
- [*] Add missing `__all__` exports in `nova/__init__.py`
- [*] Smoke-test config load, IPC/router dispatch, tool-envelope parsing

## Stage 1: Initial Scaffold
- [*] Create minimal Cortex package under `nova-cortex/nova/`
- [*] Add `pyproject.toml` with `nova-cli` console entrypoint
- [*] Add `services/nova-cortex.service` placeholder
- [*] Add `.gitignore` for build artifacts

## Stage 2: Runtime Core
- [*] Add async event loop (`core/event_loop.py`)
- [*] Add Unix socket IPC server (`core/ipc_server.py`)
- [*] Add runtime state tracking (`core/state.py`)
- [*] Verify boots and responds with wake/status messages

## Stage 3: Tool Routing & System Awareness
- [*] Add tool registry + file ops (`tools/registry.py`, `tools/file_ops.py`)
- [*] Add platform/distro detection (`core/platform.py`)
- [*] Add workspace boundary enforcement
- [*] Add `status` and `system_info` IPC routes

## Stage 4: Config & Diagnostics
- [*] Add `.env` config loader (`core/config.py`)
- [*] Add prompt builder, schema parser, engine diagnostics (`llm/prompts.py`, `schema.py`, `engine.py`)
- [*] Add report generator (`core/report.py`) with `runtime_report`, `config_status`, `llm_status`
- [*] Verify compile-clean + IPC probes working

## Stage 5: Backend Bridge
- [*] Add `LLMClient` with guarded execution for Ollama & llama.cpp
- [*] Add `llm_execute_preview` + `llm_execute` IPC routes
- [*] Add missing-binary handling (returns `unavailable` instead of crashing)

## Stage 6: Output Normalization
- [*] Add `LLMOutputParser` in `llm/output.py` — extracts JSON tool envelopes or plain text
- [*] Add `llm_response_preview` IPC route
- [*] Verify parses both structured tool calls and free-form text

## Stage 7: Real Model Integration
- [*] Replace `_execute_ollama()` subprocess with `requests` HTTP POST to `/api/generate`
- [*] Handle: connection refused, model not found (404), timeout, invalid JSON
- [*] Add streaming support via SSE token accumulation (`_execute_ollama_stream`)
- [*] Add retry logic (3 attempts with exponential backoff)
- [*] Keep llama.cpp CLI fallback intact
- [*] Create `llm/pipeline.py` — orchestrates system prompt → LLM → parse tools → route → return
- [*] Add `execute_with_tools()` — full tool-augmented conversation pipeline
- [*] Add `execute_simple()` — direct model response without tool routing
- [*] Add multi-turn conversation history (last 10 turns preserved)
- [*] Add `clear_history()` method to reset conversation
- [*] Enhance `llm/output.py` parser: extract from markdown JSON code blocks
- [*] Enhance `llm/output.py` parser: support multiple tool calls in one response
- [*] Enhance `llm/output.py` parser: strip tool call JSON from text to keep only prose
- [*] Add `llm_chat` IPC command — conversational chat with tool execution
- [*] Add `llm_chat_simple` IPC command — direct model response
- [*] Add `llm_chat_clear` IPC command — reset conversation history
- [*] Update `main.py` REPL to route through `llm_chat` pipeline
- [*] Add `/clear` command to reset conversation in REPL
- [*] Update `core/event_loop.py` — creates Pipeline and wires it to router
- [*] Update `core/ipc_server.py` — accepts pre-built router
- [*] Update `nova/__init__.py` — exports Pipeline, LLMOutputParser, LLMOutput
- [*] Rewrite `install.sh` with proper user flow:
  - [*] Ask user: Ollama or other backend
  - [*] If other: provide curl/install instructions, let user install manually
  - [*] If Ollama: install Ollama binary via official script
  - [*] Let user select model from: Qwen 2.5 Coder 3B, Llama 3.2 3B, Mistral 7B, or custom
  - [*] Pull selected model via `ollama pull`
  - [*] Verify model works with API call
- [*] Add `test_ipc_connection()` in install.sh — runs 9 IPC tests after setup
- [*] Validate: `python3 -m compileall nova` — all files compile clean
- [*] Validate: `bash -n install.sh` — Syntax OK
- [*] Remove unnecessary markdown files (HANDOFF.md, Project-Nova.md, README.md)
- [*] Log all progress in `progress.md`

## Stage 8: Voice Pipeline
- [-] Create `nova/audio/stt.py` for speech-to-text
- [-] Create `nova/audio/tts.py` for text-to-speech
- [-] Connect microphone input, transcription, and spoken responses

## Stage 9: Tool Expansion
- [-] Create `nova/tools/bash_executor.py`
- [-] Create `nova/tools/web_search.py`
- [-] Add write/delete file operations

## Stage 10: Shield & Sandbox
- [-] Create `nova/shield/classifier.py` — AST parser and risk tier assignment
- [-] Create `nova/shield/sandbox.py` — bubblewrap/systemd-nspawn wrapper
- [-] Create `nova/shield/consent.py` — CLI prompts for user authorization

## Stage 11: Memory & Learning
- [-] Create `nova/memory/vector_db.py` — ChromaDB wrapper
- [-] Create `nova/memory/embeddings.py` — nomic-embed-text wrapper
- [-] Create `nova/memory/habit_tracker.py` — SQLite logging and DBSCAN clustering

## Stage 12: Packaging & Distribution
- [-] Create DEB/RPM/Arch packages
- [-] Add full systemd service behavior
- [-] Add `uninstall.sh` with clean removal
- [-] Add tests and CI pipeline


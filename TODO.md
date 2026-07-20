# Project Nova - Development Todo List

## 🎯 Current Status
- **Phase:** Phase B (ChromaDB Vector Store Integration) - ✅ Complete
- **Last Updated:** 2026-07-13

---

## ✅ Phase B: ChromaDB Vector Store Integration

### Step 1: Install Dependencies
- [*] Add `chromadb>=0.4.0` to `pyproject.toml`

### Step 2: Implement `nova/memory/vector_db.py` (ChromaDB Wrapper)
- [*] Initialize ChromaDB persistent client with storage path
- [*] Collection management (create, get, list, delete)
- [*] Add documents with embeddings + metadata
- [*] Similarity search with metadata filtering
- [*] Delete/update operations
- [*] Status rendering for IPC diagnostics

### Step 3: Implement `nova/memory/embeddings.py` (Ollama HTTP API)
- [*] POST to `http://localhost:11434/api/embeddings` with model + input
- [*] Batch embedding with configurable batch size
- [*] LRU cache for frequently used text → embedding lookups
- [*] Error handling (model unavailable, timeout, invalid response)
- [*] Status rendering for IPC diagnostics

### Step 4: Implement `nova/memory/habit_tracker.py` (SQLite)
- [*] SQLite database setup with schema
- [*] Command logging with timestamps
- [*] DBSCAN-based temporal pattern detection
- [*] Weekly analysis
- [*] Habit suggestion engine
- [*] Status rendering for IPC diagnostics

### Step 5: Wire Everything Together
- [*] Update `nova/memory/__init__.py` with proper exports + docstring
- [*] Add memory status routes to `nova/tools/registry.py`
- [*] Add `memory_status`, `memory_store`, `memory_search`, `memory_habits` IPC commands
- [*] Wire memory components in `nova/core/event_loop.py`
- [*] Add automatic memory context injection into Pipeline's system prompt
- [*] Add automatic conversation storage to memory
- [*] Update `nova/__init__.py` exports
- [*] Subscribe EventBus to habit tracker for automatic command logging

### Step 6: Validate
- [*] `python3 -m compileall nova` — zero errors
- [*] Import check: all memory classes import successfully
- [*] `scikit-learn` detected for DBSCAN clustering
- [*] Pipeline accepts memory components
- [*] Update `progress.md` with phase B completion
- [*] Update `TODO.md` with [*] markers

---

## 📊 Progress Tracking

| Step | Status |
|------|--------|
| 1. Install Dependencies | ✅ Complete |
| 2. VectorDB Implementation | ✅ Complete |
| 3. Embeddings Implementation | ✅ Complete |
| 4. HabitTracker Implementation | ✅ Complete |
| 5. Wiring & Integration | ✅ Complete |
| 6. Validation | ✅ Complete |

---

## Future Phases (After Phase B)
- **Phase C:** Memory Router Integration — deeper memory into pipeline, enhanced retrieval
- **Phase D:** Shield & Sandbox — risk classification, consent prompts, bubblewrap
- **Phase E:** Tool Expansion — bash executor, web search, write/delete files
- **Phase F:** Voice Pipeline — STT/TTS, wake word
- **Phase G:** Packaging — DEB/RPM, systemd integration, uninstaller


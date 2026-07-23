# IPC Timeout Fix - DONE

All three fixes applied:

## Fix 1: `event_loop.py` - Move `server.start()` before memory initialization ✅
- IPC socket is now created immediately before potentially slow memory init
- Memory components (vector_db, embeddings, habit_tracker) initialized after socket is live
- Router and pipeline get memory references reassigned after successful init

## Fix 2: `install.sh` - Active socket polling in `test_ipc_connection()` ✅
- Replaced `sleep 4` with active polling loop (up to 30 seconds)
- Simplified Python test code — no redundant socket retry loop
- Clearer error messages with socket timeout details

## Fix 3: `embeddings.py` - Reduce probe timeout ✅
- Embedding probe timeout reduced from 5s to 2s


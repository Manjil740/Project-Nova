# ALL FIXES APPLIED - Novo can now execute system commands

## IPC Timeout Fixes ✅
- `event_loop.py`: IPC socket created before memory init (immediate availability)
- `install.sh`: Active socket polling replaces fixed `sleep 4`
- `embeddings.py`: Probe timeout reduced from 5s to 2s

## System Access & Tool Execution Fixes ✅
- `tools/file_ops.py`: Added `write_file()` and `execute_command()` functions
- `tools/registry.py`: 
  - Added `write_file` and `execute_command` dispatch routes
  - Removed workspace boundary restriction in `_resolve()` (full system access)
- `llm/prompts.py`: 
  - Added complete tool-calling protocol with JSON format examples
  - Listed all 8 available tools with arguments
  - Instructed LLM to use tools instead of saying "I can't"


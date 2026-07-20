#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# Prefer Konsole (KDE), otherwise fall back to x-terminal-emulator.
TERMINAL_CMD=""
if command -v konsole >/dev/null 2>&1; then
  TERMINAL_CMD="konsole"
elif command -v x-terminal-emulator >/dev/null 2>&1; then
  TERMINAL_CMD="x-terminal-emulator"
elif command -v gnome-terminal >/dev/null 2>&1; then
  TERMINAL_CMD="gnome-terminal"
else
  echo "nova-open-terminal: no supported terminal found (konsole/gnome-terminal/x-terminal-emulator)." >&2
  exit 1
fi

# Prefer installed nova-cli (venv or system), otherwise run module directly with PYTHONPATH.
if command -v nova-cli >/dev/null 2>&1; then
  NOVA_CMD="nova-cli"
else
  NOVA_CMD="PYTHONPATH=${PROJECT_ROOT}/nova-cortex python3 -m nova.main"
fi

# Start terminal and run Nova CLI.
if [[ "$TERMINAL_CMD" == "konsole" ]]; then
  # Konsole arguments: --workdir and -e command
  konsole --workdir "${PROJECT_ROOT}" -e bash -lc "${NOVA_CMD}"
  exit 0
fi

if [[ "$TERMINAL_CMD" == "gnome-terminal" ]]; then
  gnome-terminal --working-directory="${PROJECT_ROOT}" -- bash -lc "${NOVA_CMD}"
  exit 0
fi

# x-terminal-emulator fallback
x-terminal-emulator -e bash -lc "${NOVA_CMD}" >/dev/null 2>&1 || x-terminal-emulator -e bash -lc "${NOVA_CMD}"

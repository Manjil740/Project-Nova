#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
UNIT_NAME="nova-cortex.service"
UNIT_PATH="/etc/systemd/system/${UNIT_NAME}"

log() {
  printf '%s\n' "$1"
}

if command -v systemctl >/dev/null 2>&1; then
  if systemctl list-unit-files | awk '{print $1}' | grep -qx "${UNIT_NAME}"; then
    log "Stopping ${UNIT_NAME}..."
    sudo systemctl stop "${UNIT_NAME}" >/dev/null 2>&1 || true
    log "Disabling ${UNIT_NAME}..."
    sudo systemctl disable "${UNIT_NAME}" >/dev/null 2>&1 || true
  fi

  log "Reloading systemd daemon..."
  sudo systemctl daemon-reload >/dev/null 2>&1 || true
fi

if [[ -f "${UNIT_PATH}" ]]; then
  log "Removing unit file: ${UNIT_PATH}"
  sudo rm -f "${UNIT_PATH}"
  if command -v systemctl >/dev/null 2>&1; then
    sudo systemctl daemon-reload >/dev/null 2>&1 || true
  fi
fi

log "Removing venv: nova-cortex/.venv (if present)"
rm -rf "${PROJECT_ROOT}/nova-cortex/.venv" >/dev/null 2>&1 || true

log "Removing runtime dir: nova-cortex/.runtime (if present)"
rm -rf "${PROJECT_ROOT}/nova-cortex/.runtime" >/dev/null 2>&1 || true

log "Removing env file: nova-cortex/.env (if present)"
rm -f "${PROJECT_ROOT}/nova-cortex/.env" >/dev/null 2>&1 || true

log "Uninstall complete."

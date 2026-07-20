#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
UNIT_NAME="nova-cortex.service"
UNIT_PATH="/etc/systemd/system/${UNIT_NAME}"
VENV_DIR="${PROJECT_ROOT}/nova-cortex/.venv"

readonly C_RESET='\033[0m'
readonly C_BOLD='\033[1m'
readonly C_DIM='\033[2m'
readonly C_RED='\033[31m'
readonly C_GREEN='\033[32m'
readonly C_YELLOW='\033[33m'
readonly C_BLUE='\033[34m'
readonly C_CYAN='\033[36m'

log()     { printf '%b%s%b\n' "$C_BOLD" "$1" "$C_RESET"; }
info()    { printf '%b  %s%b\n' "$C_BLUE" "$1" "$C_RESET"; }
success() { printf '%b  ✓ %s%b\n' "$C_GREEN" "$1" "$C_RESET"; }
warn()    { printf '%b  ! %s%b\n' "$C_YELLOW" "$1" "$C_RESET"; }
fail()    { printf '%b  ✗ %s%b\n' "$C_RED" "$1" "$C_RESET"; }

prompt_yes_no() {
  local prompt=$1
  local default=${2:-N}
  local answer=""

  while true; do
    if [[ $default == Y ]]; then
      read -r -p "$prompt [Y/n]: " answer
    else
      read -r -p "$prompt [y/N]: " answer
    fi
    answer=${answer:-$default}
    case "${answer^^}" in
      Y|YES) return 0 ;;
      N|NO)  return 1 ;;
      *)     warn "Please answer yes or no." ;;
    esac
  done
}

print_banner() {
  clear
  cat <<'EOF'
 _   _                 _       _   
| \ | | _____   _____ | | ___ | |_ 
|  \| |/ _ \ \ / / _ \| |/ _ \| __|
| |\  |  __/\ V / (_) | | (_) | |_ 
|_| \_|\___| \_/ \___/|_|\___/ \__|
EOF
  printf '%b%sNova Uninstaller%s%b\n\n' "$C_BOLD" "$C_RED" "$C_RESET" "$C_RESET"
}

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

main() {
  print_banner

  log "This will remove Project Nova components from your system."
  echo ""

  # === 1. Stop and remove systemd service ===
  log "1. Systemd Service"
  if command -v systemctl >/dev/null 2>&1; then
    if systemctl list-unit-files 2>/dev/null | awk '{print $1}' | grep -qx "${UNIT_NAME}"; then
      info "Stopping ${UNIT_NAME}..."
      sudo systemctl stop "${UNIT_NAME}" >/dev/null 2>&1 || true
      info "Disabling ${UNIT_NAME}..."
      sudo systemctl disable "${UNIT_NAME}" >/dev/null 2>&1 || true
      success "Service stopped and disabled"
    else
      info "Service not registered — skipping"
    fi
  else
    info "systemctl not available — skipping"
  fi

  if [[ -f "${UNIT_PATH}" ]]; then
    info "Removing unit file: ${UNIT_PATH}"
    sudo rm -f "${UNIT_PATH}"
    if command -v systemctl >/dev/null 2>&1; then
      sudo systemctl daemon-reload >/dev/null 2>&1 || true
    fi
    success "Unit file removed"
  else
    info "No unit file found — skipping"
  fi

  # === 2. Remove Python venv ===
  log "2. Python Virtual Environment"
  if [[ -d "${VENV_DIR}" ]]; then
    if prompt_yes_no "Remove Python virtual environment at ${VENV_DIR}?" N; then
      rm -rf "${VENV_DIR}"
      success "Venv removed"
    else
      info "Skipped"
    fi
  else
    info "No venv found — skipping"
  fi

  # === 3. Remove runtime directory ===
  log "3. Runtime Data"
  if [[ -d "${PROJECT_ROOT}/nova-cortex/.runtime" ]]; then
    rm -rf "${PROJECT_ROOT}/nova-cortex/.runtime"
    success "Runtime directory removed"
  else
    info "No runtime data found — skipping"
  fi

  # === 4. Remove .env configuration ===
  log "4. Configuration (.env)"
  if [[ -f "${PROJECT_ROOT}/nova-cortex/.env" ]]; then
    rm -f "${PROJECT_ROOT}/nova-cortex/.env"
    success ".env removed"
  else
    info "No .env found — skipping"
  fi

  # === 5. Remove Ollama (optional) ===
  log "5. Ollama Backend"
  if command -v ollama >/dev/null 2>&1; then
    echo ""
    warn "Ollama is installed on your system (installed by Nova or previously)."
    if prompt_yes_no "Remove Ollama completely? This will delete all downloaded models." N; then
      info "Stopping ollama service..."
      sudo systemctl stop ollama >/dev/null 2>&1 || true
      sudo systemctl disable ollama >/dev/null 2>&1 || true
      sudo rm -f /etc/systemd/system/ollama.service 2>/dev/null || true
      sudo systemctl daemon-reload >/dev/null 2>&1 || true

      info "Removing ollama binary..."
      sudo rm -f /usr/local/bin/ollama /usr/bin/ollama 2>/dev/null || true

      info "Removing ollama data directory..."
      sudo rm -rf /usr/share/ollama /etc/ollama 2>/dev/null || true
      rm -rf "${HOME}/.ollama" 2>/dev/null || true

      success "Ollama removed"
    else
      info "Keeping Ollama installation"
    fi
  else
    info "Ollama not installed — skipping"
  fi

  # === 6. Remove pip cache for nova ===
  log "6. PIP Cache"
  local pip_cache_dir="${HOME}/.cache/pip"
  if [[ -d "${pip_cache_dir}" ]]; then
    find "${pip_cache_dir}" -name "*nova*" -type f -delete 2>/dev/null || true
    success "PIP cache cleaned"
  else
    info "No pip cache found — skipping"
  fi

  # === Summary ===
  echo ""
  log "━━━━ Uninstall Complete ━━━━"
  success "Nova Cortex components removed"
  
  if command -v ollama >/dev/null 2>&1; then
    warn "Ollama is still installed (you chose to keep it)"
  fi
  
  echo ""
  info "To remove Nova source files manually:"
  info "  rm -rf ${PROJECT_ROOT}"
  echo ""
  info "To restart Ollama manually if needed:"
  info "  ollama serve"
  echo ""
}

main "$@"

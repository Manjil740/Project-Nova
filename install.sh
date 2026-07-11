#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
OS_RELEASE=/etc/os-release
LLM_BACKEND=""
MODEL_PRESET=""
CUSTOM_MODEL_NAME=""
DETECTED_BACKEND=""
DETECTED_MODEL=""
declare -a EXISTING_MODELS=()
PACKAGE_MANAGER=""

readonly C_RESET='\033[0m'
readonly C_BOLD='\033[1m'
readonly C_DIM='\033[2m'
readonly C_RED='\033[31m'
readonly C_GREEN='\033[32m'
readonly C_YELLOW='\033[33m'
readonly C_BLUE='\033[34m'
readonly C_CYAN='\033[36m'
readonly C_MAGENTA='\033[35m'

print_banner() {
  clear
  cat <<'EOF'
 _   _                 _       _   
| \ | | _____   _____ | | ___ | |_ 
|  \| |/ _ \ \ / / _ \| |/ _ \| __|
| |\  |  __/\ V / (_) | | (_) | |_ 
|_| \_|\___| \_/ \___/|_|\___/ \__|
EOF
  printf '%b%sWelcome to Nova by Manjil Timalsina%s%b\n' "$C_BOLD" "$C_CYAN" "$C_RESET" "$C_RESET"
  printf '%bA local, offline-first assistant setup for Linux.%b\n\n' "$C_DIM" "$C_RESET"
}

spinner() {
  local message=$1
  local duration=${2:-12}
  local frames='| / - \\ '
  local end=$((SECONDS + duration))

  printf '%b%s%b ' "$C_BLUE" "$message" "$C_RESET"
  while (( SECONDS < end )); do
    for frame in $frames; do
      printf '\r%b%s%b %s' "$C_BLUE" "$message" "$C_RESET" "$frame"
      sleep 0.1
      if (( SECONDS >= end )); then
        break
      fi
    done
  done
  printf '\r%b%s%b %s\n' "$C_GREEN" "$message" "$C_RESET" "done"
}

warn_about_capabilities() {
  cat <<EOF
${C_YELLOW}${C_BOLD}Important safety notice:${C_RESET}
${C_YELLOW}Nova is still an AI system with system access features. It can make changes, run commands, and interact with files.${C_RESET}
${C_YELLOW}Use consent carefully, review prompts, and do not treat it as fully trustworthy or infallible.${C_RESET}
EOF
  printf '\n'
}

print_section() {
  local title=$1
  printf '%b╭──────────────────────────────────────────────╮%b\n' "$C_BLUE" "$C_RESET"
  printf '%b│%b %b%-42s%b │%b\n' "$C_BLUE" "$C_RESET" "$C_BOLD" "$title" "$C_RESET" "$C_BLUE"
  printf '%b╰──────────────────────────────────────────────╯%b\n' "$C_BLUE" "$C_RESET"
}

prompt_yes_no() {
  local prompt=$1
  local default_answer=${2:-Y}
  local answer=""

  while true; do
    if [[ $default_answer == Y ]]; then
      read -r -p "$prompt [Y/n]: " answer
    else
      read -r -p "$prompt [y/N]: " answer
    fi

    answer=${answer:-$default_answer}
    case "${answer^^}" in
      Y|YES)
        return 0
        ;;
      N|NO)
        return 1
        ;;
      *)
        printf '%bPlease answer yes or no.%b\n' "$C_YELLOW" "$C_RESET"
        ;;
    esac
  done
}

prompt_menu_choice() {
  local title=$1
  shift
  local options=("$@")
  local choice=""

  print_section "$title"
  for index in "${!options[@]}"; do
    printf '%b%2d)%b %s\n' "$C_CYAN" $((index + 1)) "$C_RESET" "${options[index]}"
  done

  while true; do
    read -r -p "Select an option [1-${#options[@]}]: " choice
    if [[ $choice =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#options[@]} )); then
      printf '%s' "${options[choice - 1]}"
      return 0
    fi
    printf '%bInvalid selection. Try again.%b\n' "$C_YELLOW" "$C_RESET"
  done
}

detect_distro() {
  if [[ ! -f "$OS_RELEASE" ]]; then
    echo "Unsupported system: $OS_RELEASE not found"
    exit 1
  fi

  # shellcheck disable=SC1091
  source "$OS_RELEASE"
  DISTRO_ID=${ID:-unknown}
  case "$DISTRO_ID" in
    org.freedesktop.platform|flatpak|linux)
      # Some containerized/flatpak environments expose generic IDs. The
      # package-manager detector below is the authoritative fallback.
      DISTRO_ID=${ID_LIKE:-unknown}
      ;;
  esac
}

detect_package_manager() {
  # Use command availability over distro strings for resilience.
  if command -v apt >/dev/null 2>&1; then
    PACKAGE_MANAGER="apt"
  elif command -v pacman >/dev/null 2>&1; then
    PACKAGE_MANAGER="pacman"
  elif command -v dnf >/dev/null 2>&1; then
    PACKAGE_MANAGER="dnf"
  fi
}

detect_existing_llm_stack() {
  if command -v ollama >/dev/null 2>&1; then
    DETECTED_BACKEND="ollama"
    mapfile -t EXISTING_MODELS < <(ollama list 2>/dev/null | awk 'NR > 1 && $1 {print $1}')
    DETECTED_MODEL="${EXISTING_MODELS[0]:-}"
    return
  fi

  if command -v llama-server >/dev/null 2>&1 || command -v llama-cli >/dev/null 2>&1; then
    DETECTED_BACKEND="llama.cpp"
  fi
}

install_system_dependencies() {
  spinner "Checking distro package tools" 2
  detect_package_manager

  case "$PACKAGE_MANAGER" in
    apt)
      spinner "Updating apt package lists" 2
      sudo apt update
      spinner "Installing base dependencies" 2
      sudo apt install -y python3 python3-venv python3-pip cmake build-essential pkg-config
      ;;
    pacman)
      spinner "Updating pacman package lists" 2
      sudo pacman -Syu --noconfirm python python-pip python-virtualenv cmake base-devel pkgconf
      ;;
    dnf)
      spinner "Installing dnf package dependencies" 2
      sudo dnf install -y python3 python3-pip cmake gcc gcc-c++ make pkgconf-pkg-config
      ;;
    *)
      printf '%bNo supported package manager was detected; skipping system package installation.%b\n' "$C_YELLOW" "$C_RESET"
      printf '%bYou can install dependencies manually later if needed.%b\n' "$C_DIM" "$C_RESET"
      ;;
  esac
}

choose_llm_backend() {
  print_section "LLM backend setup"

  if [[ -n $DETECTED_BACKEND ]]; then
    printf '%bDetected existing local AI software:%b\n' "$C_GREEN" "$C_RESET"
    printf '  • Backend: %s\n' "$DETECTED_BACKEND"
    if [[ -n $DETECTED_MODEL ]]; then
      printf '  • Model:   %s\n' "$DETECTED_MODEL"
    fi
    printf '\n'

    if prompt_yes_no "Reuse the detected setup instead of installing a new one?" Y; then
      LLM_BACKEND=$DETECTED_BACKEND
      MODEL_PRESET=${DETECTED_MODEL:-$MODEL_PRESET}
      return
    fi
  fi

  local selection
  selection=$(prompt_menu_choice "Choose how Nova should connect to an LLM" \
    "Ollama (recommended for simple offline use)" \
    "llama.cpp (local GGUF / direct binary path)" \
    "Custom backend name")

  case "$selection" in
    "Ollama (recommended for simple offline use)")
      LLM_BACKEND="ollama"
      ;;
    "llama.cpp (local GGUF / direct binary path)")
      LLM_BACKEND="llama.cpp"
      ;;
    "Custom backend name")
      read -r -p "Enter backend name: " LLM_BACKEND
      ;;
  esac
}

choose_model_preset() {
  if [[ -n $MODEL_PRESET ]]; then
    printf '%bUsing detected model:%b %s\n\n' "$C_GREEN" "$C_RESET" "$MODEL_PRESET"
    if prompt_yes_no "Keep this model selection?" Y; then
      return
    fi
  fi

  print_section "Model selection"

  if [[ $LLM_BACKEND == ollama ]] && command -v ollama >/dev/null 2>&1; then
    mapfile -t EXISTING_MODELS < <(ollama list 2>/dev/null | awk 'NR > 1 && $1 {print $1}')
    if (( ${#EXISTING_MODELS[@]} > 0 )); then
      local model_selection
      model_selection=$(prompt_menu_choice "Choose an installed Ollama model or enter a new one" \
        "Use the first detected installed model (${EXISTING_MODELS[0]})" \
        "Choose another installed model" \
        "Enter a custom model name")

      case "$model_selection" in
        "Use the first detected installed model (${EXISTING_MODELS[0]})")
          MODEL_PRESET=${EXISTING_MODELS[0]}
          ;;
        "Choose another installed model")
          local installed_choice
          installed_choice=$(prompt_menu_choice "Installed Ollama models" "${EXISTING_MODELS[@]}")
          MODEL_PRESET=$installed_choice
          ;;
        "Enter a custom model name")
          read -r -p "Enter model name or identifier: " MODEL_PRESET
          ;;
      esac
      return
    fi
  fi

  local preset_selection
  preset_selection=$(prompt_menu_choice "Pick a model preset" \
    "Qwen 2.5 Coder 3B (recommended)" \
    "Generic open-source model" \
    "Custom model name")

  case "$preset_selection" in
    "Qwen 2.5 Coder 3B (recommended)")
      MODEL_PRESET="qwen2.5-coder:3b"
      ;;
    "Generic open-source model")
      MODEL_PRESET="opensource-model"
      ;;
    "Custom model name")
      read -r -p "Enter model name or identifier: " MODEL_PRESET
      ;;
  esac
}

write_configuration() {
  mkdir -p "$PROJECT_ROOT/nova-cortex/data"
  if [[ ! -f "$PROJECT_ROOT/nova-cortex/.env.example" ]]; then
    cat > "$PROJECT_ROOT/nova-cortex/.env.example" <<EOF
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5-coder:3b
LLM_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text
VECTOR_DB_PATH=./data/chroma_db
SQLITE_DB_PATH=./data/nova_memory.sqlite
SANDBOX_ENABLED=true
DEFAULT_RISK_TIER_OVERRIDE=0
AUTO_APPROVE_TIER_0=true
ENABLE_WEB_SEARCH=true
SEARCH_PROVIDER=duckduckgo
MAX_SEARCH_RESULTS=3
EOF
  fi

  cat > "$PROJECT_ROOT/nova-cortex/.env" <<EOF
LLM_PROVIDER=$LLM_BACKEND
LLM_MODEL=$MODEL_PRESET
LLM_BASE_URL=http://localhost:11434
EOF
}

main() {
  print_banner
  warn_about_capabilities
  detect_distro
  detect_existing_llm_stack
  install_system_dependencies
  choose_llm_backend
  choose_model_preset
  write_configuration

  printf '%bSetup selection saved to nova-cortex/.env%b\n' "$C_GREEN" "$C_RESET"
  printf '%bBackend:%b %s\n' "$C_CYAN" "$C_RESET" "$LLM_BACKEND"
  printf '%bModel:%b %s\n\n' "$C_CYAN" "$C_RESET" "$MODEL_PRESET"

  printf '%bThanks for choosing Project Nova.%b\n' "$C_BOLD" "$C_RESET"
  printf '%bPlease report bugs, unsafe behavior, or setup issues so the project can improve.%b\n' "$C_DIM" "$C_RESET"
}

if [[ ${NOVA_INSTALL_LIB_ONLY:-0} != 1 ]]; then
  main "$@"
fi
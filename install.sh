#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
OS_RELEASE=/etc/os-release
LLM_BACKEND=""
MODEL_PRESET=""
CUSTOM_MODEL_NAME=""
DETECTED_BACKEND=""
DETECTED_MODEL=""
DISTRO_ID=""
declare -a EXISTING_MODELS=()
PACKAGE_MANAGER=""
INSTALL_METHOD=""  # "ollama" or "other"

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

  # Print UI to stderr so only the selected value goes to stdout (for capture via $())
  print_section "$title" >&2
  for index in "${!options[@]}"; do
    printf '%b%2d)%b %s\n' "$C_CYAN" $((index + 1)) "$C_RESET" "${options[index]}" >&2
  done

  while true; do
    read -r -p "Select an option [1-${#options[@]}]: " choice >&2
    if [[ $choice =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#options[@]} )); then
      printf '%s' "${options[choice - 1]}"
      return 0
    fi
    printf '%bInvalid selection. Try again.%b\n' "$C_YELLOW" "$C_RESET" >&2
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
      DISTRO_ID=${ID_LIKE:-unknown}
      ;;
  esac
}

detect_package_manager() {
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
      sudo apt install -y python3 python3-venv python3-pip cmake build-essential pkg-config curl
      ;;
    pacman)
      spinner "Updating pacman package lists" 2
      sudo pacman -Syu --noconfirm python python-pip python-virtualenv cmake base-devel pkgconf curl
      ;;
    dnf)
      spinner "Installing dnf package dependencies" 2
      sudo dnf install -y python3 python3-pip cmake gcc gcc-c++ make pkgconf-pkg-config curl
      ;;
    *)
      printf '%bNo supported package manager was detected; skipping system package installation.%b\n' "$C_YELLOW" "$C_RESET"
      printf '%bYou can install dependencies manually later if needed.%b\n' "$C_DIM" "$C_RESET"
      ;;
  esac
}

# ------------------------------------------------------------------
# LLM BACKEND & MODEL SETUP
# ------------------------------------------------------------------

choose_install_method() {
  print_section "AI Backend Setup"

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
      INSTALL_METHOD="$DETECTED_BACKEND"
      return
    fi
  fi

  printf '%bHow would you like to set up the AI backend?%b\n' "$C_CYAN" "$C_RESET"
  printf '\n'
  if prompt_yes_no "Use Ollama (recommended — simple, automatic setup)?" Y; then
    INSTALL_METHOD="ollama"
    LLM_BACKEND="ollama"
  else
    print_section "Alternative Backend Installation"
    printf '%bYou can install any LLM server manually. Common options:%b\n' "$C_CYAN" "$C_RESET"
    printf '  • Ollama:        curl -fsSL https://ollama.com/install.sh | sh\n'
    printf '  • llama.cpp:     git clone https://github.com/ggerganov/llama.cpp && cd llama.cpp && make\n'
    printf '  • LocalAI:       curl -fsSL https://localai.io/install.sh | sh\n'
    printf '\n'
    printf '%bPlease install your preferred backend in another terminal, then return here.%b\n' "$C_YELLOW" "$C_RESET"
    printf '%bEnter the backend name (e.g. ollama, llama.cpp, localai):%b ' "$C_BOLD" "$C_RESET"
    read -r LLM_BACKEND
    INSTALL_METHOD="other"
  fi
}

install_ollama_binary() {
  if command -v ollama >/dev/null 2>&1; then
    printf '%bOllama already installed.%b\n' "$C_GREEN" "$C_RESET"
    return
  fi

  printf '%bInstalling Ollama...%b\n' "$C_BLUE" "$C_RESET"
  if curl -fsSL https://ollama.com/install.sh | sh; then
    printf '%bOllama installed successfully.%b\n' "$C_GREEN" "$C_RESET"
  else
    printf '%bOllama installation failed.%b\n' "$C_RED" "$C_RESET"
    printf '%bPlease install manually: curl -fsSL https://ollama.com/install.sh | sh%b\n' "$C_YELLOW" "$C_RESET"
    exit 1
  fi
}

choose_ollama_model() {
  print_section "Model Selection"

  # Check if any models are already installed
  local existing_models=()
  if command -v ollama >/dev/null 2>&1; then
    mapfile -t existing_models < <(ollama list 2>/dev/null | awk 'NR > 1 && $1 {print $1}')
  fi

  if (( ${#existing_models[@]} > 0 )); then
    printf '%bDetected installed models:%b\n' "$C_GREEN" "$C_RESET"
    for model in "${existing_models[@]}"; do
      printf '  • %s\n' "$model"
    done
    printf '\n'
    if prompt_yes_no "Use an existing installed model?" Y; then
      local model_choice
      model_choice=$(prompt_menu_choice "Choose a model" "${existing_models[@]}")
      MODEL_PRESET=$model_choice
      return
    fi
  fi

  local selection
  selection=$(prompt_menu_choice "Choose a model to download" \
    "Qwen 2.5 Coder 3B (recommended — fast, good for code/system tasks)" \
    "Llama 3.2 3B (general purpose, lightweight)" \
    "Mistral 7B (powerful, needs more RAM)" \
    "Enter a custom model name from Ollama library")

  case "$selection" in
    "Qwen 2.5 Coder 3B (recommended — fast, good for code/system tasks)")
      MODEL_PRESET="qwen2.5-coder:3b"
      ;;
    "Llama 3.2 3B (general purpose, lightweight)")
      MODEL_PRESET="llama3.2:3b"
      ;;
    "Mistral 7B (powerful, needs more RAM)")
      MODEL_PRESET="mistral:7b"
      ;;
    "Enter a custom model name from Ollama library")
      printf '%bEnter model name (e.g. llama3.2:1b, phi3:3.8b, deepseek-coder:6.7b):%b ' "$C_BOLD" "$C_RESET"
      read -r MODEL_PRESET
      ;;
  esac
}

pull_ollama_model() {
  local model_name="${1:-$MODEL_PRESET}"
  if [[ -z "$model_name" ]]; then
    printf '%bNo model specified; skipping pull.%b\n' "$C_YELLOW" "$C_RESET"
    return
  fi

  if ! command -v ollama >/dev/null 2>&1; then
    printf '%bOllama not found; cannot pull model.%b\n' "$C_YELLOW" "$C_RESET"
    return
  fi

  # Check if already pulled
  if ollama list 2>/dev/null | awk 'NR > 1 {print $1}' | grep -qFx "${model_name}"; then
    printf '%bModel %s already downloaded.%b\n' "$C_GREEN" "$model_name" "$C_RESET"
    return
  fi

  printf '\n%b┌──────────────────────────────────────────────────────────┐%b\n' "$C_BOLD" "$C_RESET"
  printf '%b│  Model Manifest Command                                 │%b\n' "$C_GREEN" "$C_RESET"
  printf '%b│                                                        │%b\n' "$C_GREEN" "$C_RESET"
  printf '%b│  %bollama pull %-34s%b │%b\n' "$C_GREEN" "$C_CYAN" "$model_name" "$C_GREEN" "$C_RESET"
  printf '%b│                                                        │%b\n' "$C_GREEN" "$C_RESET"
  printf '%b└──────────────────────────────────────────────────────────┘%b\n' "$C_BOLD" "$C_RESET"

  printf '%bDownloading model: %s%b\n' "$C_BLUE" "$model_name" "$C_RESET"
  printf '%bSize range: 2-8 GB depending on model quantization.%b\n' "$C_YELLOW" "$C_RESET"
  printf '%bInternet speed will determine download time (may be 5-30+ mins).%b\n' "$C_DIM" "$C_RESET"
  printf '\n'

  if prompt_yes_no "Run 'ollama pull $model_name' now?" Y; then
    printf '%bRunning: ollama pull %s%b\n' "$C_BOLD" "$model_name" "$C_RESET"
    ollama pull "$model_name"
    local pull_exit=$?
    if [[ $pull_exit -eq 0 ]]; then
      printf '\n%b✓ Model %s downloaded successfully!%b\n' "$C_GREEN" "$model_name" "$C_RESET"
    else
      printf '\n%b✗ Model pull failed (exit code %d).%b\n' "$C_RED" "$pull_exit" "$C_RESET"
      printf '%bYou can retry later with:%b ollama pull %s\n' "$C_YELLOW" "$C_RESET" "$model_name"
    fi
  else
    printf '%bSkipped. You can pull the model manually anytime with:%b\n' "$C_YELLOW" "$C_RESET"
    printf '  %bollama pull %s%b\n' "$C_CYAN" "$model_name" "$C_RESET"
  fi
}

ensure_ollama_running() {
  if ! command -v ollama >/dev/null 2>&1; then
    return 1
  fi

  # Check if ollama server is responding
  if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    return 0
  fi

  # Try to start ollama server
  printf '%bStarting Ollama server...%b\n' "$C_BLUE" "$C_RESET"
  ollama serve &
  sleep 2

  # Verify it's running
  if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    printf '%bOllama server is running.%b\n' "$C_GREEN" "$C_RESET"
    return 0
  fi

  printf '%bWarning: Could not verify Ollama server is running.%b\n' "$C_YELLOW" "$C_RESET"
  printf '%bStart it manually with: ollama serve%b\n' "$C_DIM" "$C_RESET"
  return 1
}

verify_model_works() {
  local model_name="${1:-$MODEL_PRESET}"
  if [[ -z "$model_name" ]]; then
    return 1
  fi

  if ! command -v ollama >/dev/null 2>&1; then
    return 1
  fi

  if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    printf '%bOllama server not running; skipping model verification.%b\n' "$C_YELLOW" "$C_RESET"
    return 1
  fi

  printf '%bVerifying model %s...%b\n' "$C_BLUE" "$model_name" "$C_RESET"
  local response
  response=$(curl -s -X POST http://localhost:11434/api/generate \
    -d "{\"model\": \"$model_name\", \"prompt\": \"Hello\", \"stream\": false}" 2>/dev/null)

  if python3 -c "import sys,json; d=json.loads(sys.stdin.read()); sys.exit(0 if d.get('response','').strip() else 1)" <<< "$response"; then
    printf '%bModel %s is working correctly!%b\n' "$C_GREEN" "$model_name" "$C_RESET"
    return 0
  else
    printf '%bModel verification returned unexpected response.%b\n' "$C_YELLOW" "$model_name" "$C_RESET"
    printf '  Response: %s\n' "$response"
    return 1
  fi
}

# ------------------------------------------------------------------
# DATA DIRECTORIES
# ------------------------------------------------------------------

create_data_directories() {
  spinner "Creating Nova data directories" 2
  mkdir -p "$PROJECT_ROOT/nova-cortex/data"
  mkdir -p "$PROJECT_ROOT/nova-cortex/.runtime"
  # Create user-local data storage for memory/vector DB/habits
  local nova_data_dir="${HOME}/.local/share/nova"
  mkdir -p "$nova_data_dir/chroma_db"
  mkdir -p "$nova_data_dir/logs"
  printf '%bNova data directory: %s%b\n' "$C_DIM" "$nova_data_dir" "$C_RESET"
}

# ------------------------------------------------------------------
# PYTHON ENVIRONMENT
# ------------------------------------------------------------------

ensure_venv() {
  local venv_dir="$PROJECT_ROOT/nova-cortex/.venv"
  if [[ ! -d "$venv_dir" ]]; then
    spinner "Creating Python virtual environment" 2
    python3 -m venv "$venv_dir"
  fi

  local pip_bin="$venv_dir/bin/pip"
  if [[ ! -x "$pip_bin" ]]; then
    printf '%bVenv pip not found; recreating venv.%b\n' "$C_YELLOW" "$C_RESET"
    rm -rf "$venv_dir"
    python3 -m venv "$venv_dir"
  fi

  spinner "Upgrading pip tooling" 2
  "$venv_dir/bin/pip" install --upgrade pip setuptools wheel >/dev/null 2>&1 || true
}

install_cortex_into_venv() {
  local venv_dir="$PROJECT_ROOT/nova-cortex/.venv"
  local venv_pip="$venv_dir/bin/pip"

  if [[ ! -d "$venv_dir" ]]; then
    ensure_venv
  fi

  spinner "Installing nova-cortex into venv" 2
  "$venv_pip" install -e "$PROJECT_ROOT/nova-cortex" >/dev/null || "$venv_pip" install -e "$PROJECT_ROOT/nova-cortex"
  if [[ ! -x "$venv_dir/bin/nova-cli" ]]; then
    printf '%bWarning: nova-cli not found in venv bin.%b\n' "$C_YELLOW" "$C_RESET"
  fi
}

# ------------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------------

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

  local base_url="http://localhost:11434"
  if [[ "$LLM_BACKEND" == "llama.cpp" ]]; then
    base_url="http://localhost:8080"
  fi

  cat > "$PROJECT_ROOT/nova-cortex/.env" <<EOF
LLM_PROVIDER=$LLM_BACKEND
LLM_MODEL=$MODEL_PRESET
LLM_BASE_URL=$base_url

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
}

# ------------------------------------------------------------------
# SYSTEMD SERVICE
# ------------------------------------------------------------------

install_systemd_unit() {
  local unit_name="nova-cortex.service"
  local unit_path="/etc/systemd/system/$unit_name"
  local venv_dir="$PROJECT_ROOT/nova-cortex/.venv"
  local nova_cli="$venv_dir/bin/nova-cli"
  local workdir="$PROJECT_ROOT/nova-cortex"

  if [[ ! -x "$nova_cli" ]]; then
    printf '%bnova-cli not found at %s%b\n' "$C_YELLOW" "$C_RESET" "$nova_cli"
    printf '%bFalling back to python3 -m nova.main with PYTHONPATH environment injection.%b\n' "$C_YELLOW" "$C_RESET"
    nova_cli="__python3_dash_m_nova_main__"
  fi

  spinner "Installing systemd unit" 2
  sudo mkdir -p /etc/systemd/system

  sudo tee "$unit_path" > /dev/null <<EOF
[Unit]
Description=Project Nova Cortex Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$workdir
EOF

  if [[ "$nova_cli" == "__python3_dash_m_nova_main__" ]]; then
    sudo tee -a "$unit_path" > /dev/null <<EOF
Environment=PYTHONPATH=$workdir
ExecStart=/usr/bin/python3 -m nova.main
EOF
  else
    sudo tee -a "$unit_path" > /dev/null <<EOF
ExecStart=$nova_cli
EOF
  fi

  sudo tee -a "$unit_path" > /dev/null <<EOF
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
EOF

  sudo systemctl daemon-reload
  sudo systemctl enable --now "$unit_name" >/dev/null 2>&1 || sudo systemctl restart "$unit_name"
}

# ------------------------------------------------------------------
# TEST IPC CONNECTION
# ------------------------------------------------------------------

test_ipc_connection() {
  printf '\n%b━━━━ Testing Nova Cortex IPC Connection ━━━━%b\n' "$C_BOLD" "$C_MAGENTA" "$C_RESET"

  local venv_dir="$PROJECT_ROOT/nova-cortex/.venv"
  local venv_python="$venv_dir/bin/python3"
  local sock_path="$PROJECT_ROOT/nova-cortex/.runtime/nova-cortex.sock"

  if [[ ! -x "$venv_python" ]]; then
    printf '%bPython venv not found at %s; skipping IPC test.%b\n' "$C_YELLOW" "$venv_python" "$C_RESET"
    return
  fi

  # Make sure the server is not already running on this socket
  if [[ -S "$sock_path" ]]; then
    printf '%bRemoving stale socket...%b\n' "$C_DIM" "$C_RESET"
    rm -f "$sock_path"
  fi

  # Start the server in background
  printf '%bStarting Cortex server for testing...%b\n' "$C_BLUE" "$C_RESET"
  PYTHONPATH="$PROJECT_ROOT/nova-cortex" "$venv_python" -m nova.main --server &
  local server_pid=$!
  sleep 2

  # Cleanup function
  cleanup() {
    kill "$server_pid" 2>/dev/null || true
    rm -f "$sock_path" 2>/dev/null || true
  }
  trap cleanup EXIT

  # Test functions using python
  run_test() {
    local test_name=$1
    local tool_name=$2
    local arg=$3

    printf '%b  [TEST] %s...%b ' "$C_BOLD" "$test_name" "$C_RESET"
    local result
    result=$(PYTHONPATH="$PROJECT_ROOT/nova-cortex" "$venv_python" -c "
import json, socket
sock_path = '$sock_path'
# Wait for socket
import time
for _ in range(10):
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect(str(sock_path))
        break
    except (FileNotFoundError, ConnectionRefusedError, OSError):
        time.sleep(0.2)
else:
    print('SOCKET_TIMEOUT')
    exit(1)
msg = json.dumps({'tool': '$tool_name', 'arguments': {'path': '$arg'}})
s.sendall((msg + '\n').encode('utf-8'))
data = s.recv(4096)
print(data.decode('utf-8').rstrip())
s.close()
" 2>&1)

    if echo "$result" | grep -qi "error\|unavailable\|SOCKET_TIMEOUT"; then
      printf '%bFAILED%b\n' "$C_RED" "$C_RESET"
      printf '    %s\n' "$result"
      return 1
    else
      printf '%bPASSED%b\n' "$C_GREEN" "$C_RESET"
      printf '    %s\n' "$result"
      return 0
    fi
  }

  local tests_passed=0
  local tests_failed=0

  # Test 1: Wake/ping
  if run_test "Wake/Ping" "wake" ""; then
    ((tests_passed++))
  else
    ((tests_failed++))
  fi

  # Test 2: Status
  if run_test "Status" "status" ""; then
    ((tests_passed++))
  else
    ((tests_failed++))
  fi

  # Test 3: System info
  if run_test "System Info" "system_info" ""; then
    ((tests_passed++))
  else
    ((tests_failed++))
  fi

  # Test 4: Config status
  if run_test "Config Status" "config_status" ""; then
    ((tests_passed++))
  else
    ((tests_failed++))
  fi

  # Test 5: LLM status
  if run_test "LLM Status" "llm_status" ""; then
    ((tests_passed++))
  else
    ((tests_failed++))
  fi

  # Test 6: Runtime report
  if run_test "Runtime Report" "runtime_report" ""; then
    ((tests_passed++))
  else
    ((tests_failed++))
  fi

  # Test 7: List directory
  if run_test "List Directory" "list_directory" "."; then
    ((tests_passed++))
  else
    ((tests_failed++))
  fi

  # Test 8: Read file (pyproject.toml)
  if run_test "Read File" "read_file" "pyproject.toml"; then
    ((tests_passed++))
  else
    ((tests_failed++))
  fi

  # Test 9: LLM chat (if model is available)
  if command -v ollama >/dev/null 2>&1 && curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    if run_test "LLM Chat (quick)" "llm_chat_simple" "Say hello in one word"; then
      ((tests_passed++))
    else
      ((tests_failed++))
    fi
  else
    printf '%b  [SKIP] LLM Chat test — Ollama/model not available%b\n' "$C_YELLOW" "$C_RESET"
  fi

  # Summary
  printf '\n%b━━━━ Test Results ━━━━%b\n' "$C_BOLD" "$C_MAGENTA" "$C_RESET"
  printf '%bPassed:%b %d\n' "$C_GREEN" "$C_RESET" "$tests_passed"
  if (( tests_failed > 0 )); then
    printf '%bFailed:%b %d\n' "$C_RED" "$C_RESET" "$tests_failed"
  else
    printf '%bFailed:%b 0\n' "$C_GREEN" "$C_RESET"
  fi
  printf '\n'

  # Cleanup
  cleanup
}

# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------

main() {
  print_banner
  warn_about_capabilities
  detect_distro
  detect_existing_llm_stack
  install_system_dependencies

  # LLM backend selection
  choose_install_method

  if [[ "$INSTALL_METHOD" == "ollama" ]]; then
    install_ollama_binary

    # Ensure ollama is running before model selection
    ensure_ollama_running

    # Let user choose a model
    choose_ollama_model

    # Pull the selected model
    if [[ -n "$MODEL_PRESET" ]]; then
      pull_ollama_model "$MODEL_PRESET"
    fi
  fi

  # Create data directories
  create_data_directories

  # Write configuration
  write_configuration

  # Python environment
  ensure_venv
  install_cortex_into_venv

  # Systemd service
  install_systemd_unit

  # Run IPC tests
  test_ipc_connection

  # Final summary
  printf '\n%b━━━━ Setup Complete ━━━━%b\n' "$C_BOLD" "$C_GREEN" "$C_RESET"
  printf '%bConfiguration saved to:%b nova-cortex/.env\n' "$C_CYAN" "$C_RESET"
  printf '%bBackend:%b %s\n' "$C_CYAN" "$C_RESET" "$LLM_BACKEND"
  printf '%bModel:%b %s\n' "$C_CYAN" "$C_RESET" "$MODEL_PRESET"
  printf '\n'
  printf '%bTo start chatting, run:%b\n' "$C_BOLD" "$C_RESET"
  printf '  nova-cli\n'
  printf '\n'
  printf '%bOr use the REPL directly:%b\n' "$C_BOLD" "$C_RESET"
  printf '  cd nova-cortex && .venv/bin/python3 -m nova.main\n'
  printf '\n'
  printf '%bThanks for choosing Project Nova.%b\n' "$C_BOLD" "$C_RESET"
  printf '%bPlease report bugs, unsafe behavior, or setup issues so the project can improve.%b\n' "$C_DIM" "$C_RESET"
}

if [[ ${NOVA_INSTALL_LIB_ONLY:-0} != 1 ]]; then
  main "$@"
fi

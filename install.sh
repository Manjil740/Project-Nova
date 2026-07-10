#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
OS_RELEASE=/etc/os-release
LLM_BACKEND=""
MODEL_PRESET=""
CUSTOM_MODEL_NAME=""

detect_distro() {
  if [[ ! -f "$OS_RELEASE" ]]; then
    echo "Unsupported system: $OS_RELEASE not found"
    exit 1
  fi

  # shellcheck disable=SC1091
  source "$OS_RELEASE"
  DISTRO_ID=${ID:-unknown}
}

install_system_dependencies() {
  case "$DISTRO_ID" in
    kali|ubuntu|debian)
      sudo apt update
      sudo apt install -y python3 python3-venv python3-pip cmake build-essential pkg-config
      ;;
    arch|manjaro)
      sudo pacman -Syu --noconfirm python python-pip python-virtualenv cmake base-devel pkgconf
      ;;
    fedora|rhel)
      sudo dnf install -y python3 python3-pip cmake gcc gcc-c++ make pkgconf-pkg-config
      ;;
    *)
      echo "Unsupported distro: $DISTRO_ID"
      exit 1
      ;;
  esac
}

choose_llm_backend() {
  echo "Select the LLM backend to set up:"
  select choice in "Ollama" "llama.cpp" "Custom"; do
    case "$choice" in
      Ollama)
        LLM_BACKEND="ollama"
        break
        ;;
      llama.cpp)
        LLM_BACKEND="llama.cpp"
        break
        ;;
      Custom)
        read -r -p "Enter backend name: " LLM_BACKEND
        break
        ;;
      *)
        echo "Choose 1, 2, or 3."
        ;;
    esac
  done
}

choose_model_preset() {
  echo "Select the model preset to configure:"
  select choice in "Qwen 2.5 Coder 3B" "Generic Open-Source Model" "Custom"; do
    case "$choice" in
      "Qwen 2.5 Coder 3B")
        MODEL_PRESET="qwen2.5-coder:3b"
        break
        ;;
      "Generic Open-Source Model")
        MODEL_PRESET="opensource-model"
        break
        ;;
      Custom)
        read -r -p "Enter model name or identifier: " MODEL_PRESET
        break
        ;;
      *)
        echo "Choose 1, 2, or 3."
        ;;
    esac
  done
}

write_configuration() {
  mkdir -p "$PROJECT_ROOT/nova-cortex/data"
  cat > "$PROJECT_ROOT/nova-cortex/.env" <<EOF
LLM_PROVIDER=$LLM_BACKEND
LLM_MODEL=$MODEL_PRESET
LLM_BASE_URL=http://localhost:11434
EOF
}

main() {
  detect_distro
  install_system_dependencies
  choose_llm_backend
  choose_model_preset
  write_configuration

  echo "Setup selection saved to nova-cortex/.env"
  echo "Backend: $LLM_BACKEND"
  echo "Model: $MODEL_PRESET"
}

main "$@"
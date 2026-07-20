from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from nova.core.event_loop import CortexApp


def _socket_path(project_root: Path) -> Path:
    return project_root / ".runtime" / "nova-cortex.sock"


def _ensure_server_running(project_root: Path) -> None:
    sock = _socket_path(project_root)
    if sock.exists():
        return

    env = dict(os.environ)
    cmd = [sys.executable, "-m", "nova.main", "--server"]
    proc = subprocess.Popen(
        cmd, cwd=str(project_root), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    for _ in range(100):
        if sock.exists():
            return
        time.sleep(0.05)

    try:
        proc.terminate()
    except Exception:
        pass
    raise RuntimeError("Cortex server did not start (socket not created).")


def _ipc_request(project_root: Path, message: str) -> str:
    sock = _socket_path(project_root)
    _ensure_server_running(project_root)

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(str(sock))
        s.sendall((message + "\n").encode("utf-8"))
        data = s.recv(1024 * 1024)

    return data.decode("utf-8", errors="replace").rstrip("\n")


def _print_header(project_root: Path) -> None:
    sock = _socket_path(project_root)
    print("=== Nova Cortex Terminal ===")
    print(f"Workspace: {project_root}")
    print(f"Socket:    {sock}")
    print("Type 'exit' to quit. Use '/clear' to reset conversation.")
    print()


def _repl(project_root: Path) -> None:
    _print_header(project_root)
    while True:
        try:
            user_in = input("nova> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return

        if not user_in:
            continue
        if user_in.lower() in {"exit", "quit", "q"}:
            print("bye")
            return

        # Clear conversation history
        if user_in.lower() == "/clear":
            try:
                msg = json.dumps({"tool": "llm_chat_clear"})
                _ipc_request(project_root, msg)
            except Exception:
                pass
            print("[Conversation history cleared]\n")
            continue

        # Route through the conversational chat pipeline (llm_chat).
        # Supports: tool call extraction, tool execution, plain text fallback.
        try:
            msg = json.dumps({"tool": "llm_chat", "arguments": {"path": user_in}})
            resp = _ipc_request(project_root, msg)
        except Exception as e:
            resp = f"error:ipc_failed:{e}"

        # Extract and display the response text cleanly
        if resp.startswith("response:"):
            display = resp[len("response:"):]
            # Strip any tool results suffix for cleaner display
            if " tools=[" in display:
                display = display.split(" tools=[")[0]
            print(f"Nova: {display}")
        else:
            print(resp)
        print()


def _run_server(project_root: Path) -> None:
    print("Starting Nova Cortex server (IPC listener)...")
    asyncio.run(CortexApp(project_root=project_root).run())


def main() -> None:
    parser = argparse.ArgumentParser(prog="nova-cli", add_help=True)
    parser.add_argument("--server", action="store_true", help="Run the Cortex IPC server.")
    parser.add_argument("--once", type=str, default=None, help="Run a single prompt (non-interactive).")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]

    if args.server:
        _run_server(project_root)
        return

    if args.once is not None:
        msg = json.dumps({"tool": "llm_chat", "arguments": {"path": args.once}})
        print(_ipc_request(project_root, msg))
        return

    _repl(project_root)


if __name__ == "__main__":
    main()

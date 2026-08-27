from __future__ import annotations

import subprocess
from pathlib import Path


def list_directory(target: Path) -> str:
    if not target.exists():
        return f"error:missing:{target}"

    if not target.is_dir():
        return f"error:not_directory:{target}"

    entries = sorted(child.name for child in target.iterdir())
    return "\n".join(entries) if entries else "(empty)"


def read_file(target: Path) -> str:
    if not target.exists():
        return f"error:missing:{target}"

    if not target.is_file():
        return f"error:not_file:{target}"

    return target.read_text(encoding="utf-8", errors="replace")


def write_file(target: Path, content: str) -> str:
    """Write content to a file, creating parent directories if needed."""
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"written:{target}"


def execute_command(command: str, cwd: str | None = None, timeout: int = 30) -> str:
    """Execute a shell command and return its output.

    Args:
        command: The shell command to execute.
        cwd: Working directory (defaults to home).
        timeout: Command timeout in seconds.

    Returns:
        stdout + stderr combined output.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        output = result.stdout
        if result.stderr:
            if output:
                output += "\n" + result.stderr
            else:
                output = result.stderr
        if result.returncode != 0:
            output = f"[exit code: {result.returncode}]\n{output}"
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return f"error:command timed out after {timeout}s"
    except FileNotFoundError:
        return "error:shell not found"
    except PermissionError:
        return "error:permission denied"
    except OSError as exc:
        return f"error:os_error:{exc}"

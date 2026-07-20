"""Centralized error types for Nova Cortex.

Provides typed exception classes so error handling across the codebase
is consistent and tool-specific error recovery is straightforward.
"""

from __future__ import annotations


class NovaError(Exception):
    """Base error for all Nova Cortex exceptions."""

    def __init__(self, message: str = "", code: str = "unknown_error") -> None:
        self.code = code
        super().__init__(message)

    def render(self) -> str:
        return f"nova_error:code={self.code} message={str(self)}"


class NovaConfigError(NovaError):
    """Raised when configuration loading or validation fails."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message=message, code="config_error")


class NovaMemoryError(NovaError):
    """Raised when vector DB, embeddings, or habit tracker operations fail."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message=message, code="memory_error")


class NovaToolError(NovaError):
    """Raised when tool dispatch or execution encounters a failure.

    Includes the failing tool name for targeted error recovery.
    """

    def __init__(self, message: str = "", tool: str = "unknown") -> None:
        self.tool = tool
        code = f"tool_error:{tool}"
        super().__init__(message=message, code=code)


class NovaIOError(NovaError):
    """Raised on filesystem or storage I/O failures."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message=message, code="io_error")


class NovaConnectionError(NovaError):
    """Raised when a backend service (LLM, embedding, DB) is unreachable."""

    def __init__(self, message: str = "", service: str = "unknown") -> None:
        self.service = service
        code = f"connection_error:{service}"
        super().__init__(message=message, code=code)

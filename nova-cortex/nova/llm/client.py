from __future__ import annotations

from dataclasses import dataclass
from subprocess import TimeoutExpired
from subprocess import PIPE, run

from nova.core.config import NovaConfig
from nova.llm.output import LLMOutputParser


@dataclass(slots=True)
class LLMRequest:
    """Normalized request envelope for all local backends.

    Keep request fields backend-agnostic so upstream router code does not need
    provider-specific branching.
    """

    provider: str
    model: str
    base_url: str
    prompt: str

    def render(self) -> str:
        safe_prompt = self.prompt.replace("\n", " ").strip()
        return (
            f"request:provider={self.provider} model={self.model} base_url={self.base_url} "
            f"prompt={safe_prompt}"
        )


@dataclass(slots=True)
class LLMResponse:
    """Lightweight response envelope returned to router commands.

    `available=False` is used for both missing-runtime and execution failures
    so callers can remain failure-safe without exception handling.
    """

    provider: str
    model: str
    available: bool
    output: str = ""

    def render(self) -> str:
        availability = "available" if self.available else "unavailable"
        safe_output = self.output.replace("\n", " ").strip()
        suffix = f" output={safe_output}" if safe_output else ""
        return f"response:provider={self.provider} model={self.model} state={availability}{suffix}"


@dataclass(slots=True)
class LLMClient:
    """Backend bridge for local model providers.

    This layer is intentionally small so a future agent can replace command
    execution with API clients/streaming without touching the router contract.
    """

    config: NovaConfig

    def build_request(self, prompt: str) -> LLMRequest:
        return LLMRequest(
            provider=self.config.llm_provider,
            model=self.config.llm_model,
            base_url=self.config.llm_base_url,
            prompt=prompt,
        )

    def render_preview(self, prompt: str) -> str:
        return self.build_request(prompt).render()

    def execute(self, prompt: str) -> LLMResponse:
        # This method is intentionally provider-switched in one place so future
        # backends can be added without changing router command contracts.
        request = self.build_request(prompt)

        if request.provider == "ollama":
            return self._execute_ollama(request)

        if request.provider == "llama.cpp":
            return self._execute_llama_cpp(request)

        return LLMResponse(provider=request.provider, model=request.model, available=False)

    def render_execution_preview(self, prompt: str) -> str:
        return self.execute(prompt).render()

    def render_response_preview(self, raw_text: str) -> str:
        # Parsing is kept outside execute() to let debugging and policy layers
        # inspect raw model output independently.
        parser = LLMOutputParser()
        return parser.render_preview(raw_text)

    def _execute_ollama(self, request: LLMRequest) -> LLMResponse:
        # This currently uses CLI execution for portability. Swap this with
        # native HTTP API calls in a later stage when streaming is added.
        try:
            completed = run(
                ["ollama", "run", request.model, request.prompt],
                stdout=PIPE,
                stderr=PIPE,
                text=True,
                timeout=30,
                check=False,
            )
        except FileNotFoundError:
            return LLMResponse(provider=request.provider, model=request.model, available=False, output="ollama_missing")
        except TimeoutExpired:
            return LLMResponse(provider=request.provider, model=request.model, available=False, output="ollama_timeout")

        if completed.returncode != 0:
            error_text = completed.stderr.strip() or "ollama_execution_failed"
            return LLMResponse(provider=request.provider, model=request.model, available=False, output=error_text)

        return LLMResponse(provider=request.provider, model=request.model, available=True, output=completed.stdout.strip())

    def _execute_llama_cpp(self, request: LLMRequest) -> LLMResponse:
        # Assumes llama.cpp CLI availability in PATH. Model resolution is still
        # caller-provided and should be hardened in packaging stages.
        try:
            completed = run(
                ["llama-cli", "-m", request.model, "-p", request.prompt],
                stdout=PIPE,
                stderr=PIPE,
                text=True,
                timeout=30,
                check=False,
            )
        except FileNotFoundError:
            return LLMResponse(provider=request.provider, model=request.model, available=False, output="llama_cli_missing")
        except TimeoutExpired:
            return LLMResponse(provider=request.provider, model=request.model, available=False, output="llama_cpp_timeout")

        if completed.returncode != 0:
            error_text = completed.stderr.strip() or "llama_cpp_execution_failed"
            return LLMResponse(provider=request.provider, model=request.model, available=False, output=error_text)

        return LLMResponse(provider=request.provider, model=request.model, available=True, output=completed.stdout.strip())

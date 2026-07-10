from __future__ import annotations

from dataclasses import dataclass
from subprocess import TimeoutExpired
from subprocess import PIPE, run

from nova.core.config import NovaConfig


@dataclass(slots=True)
class LLMRequest:
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
        request = self.build_request(prompt)

        if request.provider == "ollama":
            return self._execute_ollama(request)

        if request.provider == "llama.cpp":
            return self._execute_llama_cpp(request)

        return LLMResponse(provider=request.provider, model=request.model, available=False)

    def render_execution_preview(self, prompt: str) -> str:
        return self.execute(prompt).render()

    def _execute_ollama(self, request: LLMRequest) -> LLMResponse:
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

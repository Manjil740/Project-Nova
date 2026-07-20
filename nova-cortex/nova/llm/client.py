from __future__ import annotations

import json
import time
from dataclasses import dataclass
from subprocess import TimeoutExpired
from subprocess import PIPE, run
from typing import Any

import requests

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

    Uses HTTP API for Ollama (streaming supported) and CLI subprocess for
    llama.cpp as a fallback.
    """

    config: NovaConfig
    _parser: LLMOutputParser = LLMOutputParser()

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
        """Execute a prompt against the configured backend.

        Uses HTTP API for Ollama, CLI subprocess for llama.cpp fallback.
        """
        request = self.build_request(prompt)

        if request.provider == "ollama":
            return self._execute_ollama_api(request)

        if request.provider == "llama.cpp":
            return self._execute_llama_cpp(request)

        return LLMResponse(
            provider=request.provider,
            model=request.model,
            available=False,
            output="unsupported_provider",
        )

    def execute_stream(self, prompt: str) -> str:
        """Execute and return raw output, with streaming if supported.

        Returns the full response text. Raises RuntimeError on failure.
        """
        request = self.build_request(prompt)

        if request.provider == "ollama":
            return self._execute_ollama_stream(request)

        response = self.execute(prompt)
        if not response.available:
            raise RuntimeError(f"LLM unavailable: {response.output}")
        return response.output

    def render_execution_preview(self, prompt: str) -> str:
        return self.execute(prompt).render()

    def render_response_preview(self, raw_text: str) -> str:
        return self._parser.render_preview(raw_text)

    # ------------------------------------------------------------------
    # Ollama HTTP API
    # ------------------------------------------------------------------

    def _execute_ollama_api(self, request: LLMRequest, timeout: int = 60) -> LLMResponse:
        """Execute via Ollama HTTP API (/api/generate) with retry logic."""
        url = f"{request.base_url.rstrip('/')}/api/generate"

        for attempt in range(3):
            try:
                resp = requests.post(
                    url,
                    json={
                        "model": request.model,
                        "prompt": request.prompt,
                        "stream": False,
                    },
                    timeout=timeout,
                )
            except requests.exceptions.ConnectionError:
                if attempt < 2:
                    time.sleep(1.5 ** attempt)
                    continue
                return LLMResponse(
                    provider=request.provider,
                    model=request.model,
                    available=False,
                    output="ollama_connection_refused",
                )
            except requests.exceptions.Timeout:
                if attempt < 2:
                    time.sleep(1.5 ** attempt)
                    continue
                return LLMResponse(
                    provider=request.provider,
                    model=request.model,
                    available=False,
                    output="ollama_timeout",
                )
            except requests.exceptions.RequestException as exc:
                return LLMResponse(
                    provider=request.provider,
                    model=request.model,
                    available=False,
                    output=f"ollama_request_failed:{exc}",
                )

            if resp.status_code == 404:
                try:
                    err = resp.json()
                    error_type = err.get("error", "model_not_found")
                except (json.JSONDecodeError, KeyError):
                    error_type = "model_not_found"
                return LLMResponse(
                    provider=request.provider,
                    model=request.model,
                    available=False,
                    output=f"ollama_{error_type}",
                )

            if resp.status_code != 200:
                return LLMResponse(
                    provider=request.provider,
                    model=request.model,
                    available=False,
                    output=f"ollama_http_{resp.status_code}",
                )

            try:
                data = resp.json()
            except json.JSONDecodeError:
                return LLMResponse(
                    provider=request.provider,
                    model=request.model,
                    available=False,
                    output="ollama_invalid_json_response",
                )

            raw_output = data.get("response", "").strip()
            return LLMResponse(
                provider=request.provider,
                model=request.model,
                available=True,
                output=raw_output,
            )

        return LLMResponse(
            provider=request.provider,
            model=request.model,
            available=False,
            output="ollama_max_retries_exceeded",
        )

    def _execute_ollama_stream(self, request: LLMRequest, timeout: int = 120) -> str:
        """Stream response from Ollama HTTP API, accumulating tokens."""
        url = f"{request.base_url.rstrip('/')}/api/generate"

        resp = requests.post(
            url,
            json={
                "model": request.model,
                "prompt": request.prompt,
                "stream": True,
            },
            timeout=timeout,
            stream=True,
        )
        resp.raise_for_status()

        tokens: list[str] = []
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                continue
            token = chunk.get("response", "")
            if token:
                tokens.append(token)
            if chunk.get("done", False):
                break

        return "".join(tokens).strip()

    # ------------------------------------------------------------------
    # llama.cpp CLI fallback
    # ------------------------------------------------------------------

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
            return LLMResponse(
                provider=request.provider,
                model=request.model,
                available=False,
                output="llama_cli_missing",
            )
        except TimeoutExpired:
            return LLMResponse(
                provider=request.provider,
                model=request.model,
                available=False,
                output="llama_cpp_timeout",
            )

        if completed.returncode != 0:
            error_text = completed.stderr.strip() or "llama_cpp_execution_failed"
            return LLMResponse(
                provider=request.provider,
                model=request.model,
                available=False,
                output=error_text,
            )

        return LLMResponse(
            provider=request.provider,
            model=request.model,
            available=True,
            output=completed.stdout.strip(),
        )

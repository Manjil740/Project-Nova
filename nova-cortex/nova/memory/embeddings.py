"""Embedding model wrapper for text vectorization.

Phase B implementation:
- nomic-embed-text via Ollama HTTP API (POST /api/embeddings)
- Batch embedding with configurable batch size
- LRU cache for frequently used text → embedding lookups
- Error handling: connection refused, timeout, model unavailable, invalid JSON
"""

from __future__ import annotations

import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

import requests

from nova.core.errors import NovaMemoryError, NovaConnectionError

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Embeddings:
    """Embedding model client using Ollama's HTTP API.

    Connects to a local Ollama instance to generate text embeddings
    using models like nomic-embed-text. Includes LRU caching and
    batched processing for efficiency.

    Usage:
        emb = Embeddings()
        emb.initialize()
        vector = emb.embed("Hello world")
        vectors = emb.embed_batch(["Hello", "World"])
    """

    model_name: str = "nomic-embed-text"
    batch_size: int = 8
    cache_size: int = 1000

    base_url: str = "http://localhost:11434"

    _client: Any = None  # requests.Session
    _cache: OrderedDict = field(default_factory=lambda: OrderedDict())
    _initialized: bool = False
    _cache_hits: int = 0
    _cache_misses: int = 0
    _total_embedded: int = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize the HTTP session and verify Ollama connectivity.

        Tests the embedding endpoint with a lightweight probe to ensure
        the model is available before first use.

        Raises:
            NovaConnectionError: If Ollama is unreachable or model unavailable.
        """
        self._client = requests.Session()
        self._cache = OrderedDict()

        # Probe the embedding endpoint
        try:
            resp = self._client.post(
                f"{self.base_url.rstrip('/')}/api/embeddings",
                json={"model": self.model_name, "prompt": "ping"},
                timeout=2,
            )
        except requests.exceptions.ConnectionError:
            raise NovaConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                f"Is ollama running?"
            )
        except requests.exceptions.Timeout:
            raise NovaConnectionError(
                f"Ollama at {self.base_url} timed out during probe."
            )

        if resp.status_code == 404:
            raise NovaMemoryError(
                f"Model '{self.model_name}' not found in Ollama. "
                f"Run: ollama pull {self.model_name}"
            )

        if resp.status_code != 200:
            raise NovaMemoryError(
                f"Ollama returned HTTP {resp.status_code}: {resp.text[:200]}"
            )

        try:
            data = resp.json()
            if "embedding" not in data:
                raise NovaMemoryError(
                    f"Unexpected Ollama response (no 'embedding' field): {data}"
                )
        except json.JSONDecodeError:
            raise NovaMemoryError(
                f"Invalid JSON response from Ollama: {resp.text[:200]}"
            )

        self._initialized = True
        logger.info(
            "Embeddings initialized: model=%s url=%s",
            self.model_name,
            self.base_url,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_initialized(self) -> bool:
        """Return True when the embedding model is ready."""
        return self._initialized and self._client is not None

    @property
    def cache_info(self) -> dict[str, int]:
        """Return cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self.cache_size,
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "total_embedded": self._total_embedded,
        }

    # ------------------------------------------------------------------
    # Embedding API
    # ------------------------------------------------------------------

    def embed(self, text: str) -> list[float]:
        """Embed a single text string into a vector.

        Uses LRU cache: if the exact text was embedded recently,
        returns the cached vector.

        Args:
            text: Input text to embed.

        Returns:
            List of floats representing the embedding vector.

        Raises:
            NovaMemoryError: If embedding fails.
        """
        # Check cache first
        if text in self._cache:
            self._cache_hits += 1
            # Move to end (most recently used)
            self._cache.move_to_end(text)
            return self._cache[text]

        self._cache_misses += 1

        if not self.is_initialized:
            raise NovaMemoryError("Embeddings not initialized. Call initialize() first.")

        try:
            resp = self._client.post(
                f"{self.base_url.rstrip('/')}/api/embeddings",
                json={"model": self.model_name, "prompt": text},
                timeout=30,
            )
        except requests.exceptions.ConnectionError:
            raise NovaConnectionError(
                service="ollama",
                message=f"Ollama connection refused at {self.base_url}",
            )
        except requests.exceptions.Timeout:
            raise NovaConnectionError(
                service="ollama",
                message="Ollama embedding request timed out",
            )
        except requests.exceptions.RequestException as exc:
            raise NovaMemoryError(f"Embedding request failed: {exc}")

        if resp.status_code != 200:
            raise NovaMemoryError(
                f"Ollama returned HTTP {resp.status_code}: {resp.text[:200]}"
            )

        try:
            data = resp.json()
            vector = data["embedding"]
        except (json.JSONDecodeError, KeyError) as exc:
            raise NovaMemoryError(
                f"Invalid embedding response: {resp.text[:200]}"
            ) from exc

        # Update cache (LRU eviction)
        self._cache[text] = vector
        if len(self._cache) > self.cache_size:
            self._cache.popitem(last=False)  # Remove oldest

        self._total_embedded += 1
        return vector

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in batches for efficiency.

        Processes texts in batches of `batch_size`, using LRU cache
        for previously embedded texts to avoid redundant API calls.

        Args:
            texts: List of input texts to embed.

        Returns:
            List of embedding vectors, one per input text.

        Raises:
            NovaMemoryError: If any embedding in the batch fails.
        """
        results: list[list[float]] = []
        batch: list[str] = []

        for text in texts:
            # Check cache first
            if text in self._cache:
                self._cache_hits += 1
                self._cache.move_to_end(text)
                results.append(self._cache[text])
                continue

            self._cache_misses += 1
            batch.append(text)

            # Process when batch is full or at end
            if len(batch) >= self.batch_size:
                batch_vectors = self._execute_batch(batch)
                results.extend(batch_vectors)
                batch = []

        # Process remaining texts
        if batch:
            batch_vectors = self._execute_batch(batch)
            results.extend(batch_vectors)

        return results

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _execute_batch(self, texts: list[str]) -> list[list[float]]:
        """Execute a single batch embedding request.

        Falls back to sequential embedding if batch endpoint fails
        (some models may not support batching).
        """
        if not self.is_initialized:
            raise NovaMemoryError("Embeddings not initialized. Call initialize() first.")

        vectors: list[list[float]] = []

        for text in texts:
            try:
                vector = self._embed_single(text)
                vectors.append(vector)
                # Cache the result
                self._cache[text] = vector
                if len(self._cache) > self.cache_size:
                    self._cache.popitem(last=False)
                self._total_embedded += 1
            except Exception as exc:
                raise NovaMemoryError(
                    f"Failed to embed text in batch: {exc}"
                ) from exc

        return vectors

    def _embed_single(self, text: str) -> list[float]:
        """Execute a single embedding request to Ollama."""
        try:
            resp = self._client.post(
                f"{self.base_url.rstrip('/')}/api/embeddings",
                json={"model": self.model_name, "prompt": text},
                timeout=30,
            )
        except requests.exceptions.ConnectionError:
            raise NovaConnectionError(
                service="ollama",
                message=f"Ollama connection refused at {self.base_url}",
            )
        except requests.exceptions.Timeout:
            raise NovaConnectionError(
                service="ollama",
                message="Ollama embedding request timed out",
            )
        except requests.exceptions.RequestException as exc:
            raise NovaMemoryError(f"Embedding request failed: {exc}")

        if resp.status_code != 200:
            raise NovaMemoryError(
                f"Ollama returned HTTP {resp.status_code}: {resp.text[:200]}"
            )

        try:
            data = resp.json()
            return data["embedding"]
        except (json.JSONDecodeError, KeyError) as exc:
            raise NovaMemoryError(
                f"Invalid embedding response: {resp.text[:200]}"
            ) from exc

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def render_status(self) -> str:
        """Return a single-line status string for IPC diagnostics."""
        state = "ready" if self.is_initialized else "uninitialized"
        info = self.cache_info
        return (
            f"embeddings:model={self.model_name} "
            f"url={self.base_url} "
            f"batch={self.batch_size} "
            f"cache_size={info['size']}/{info['max_size']} "
            f"cache_hits={info['hits']} "
            f"cache_misses={info['misses']} "
            f"total_embedded={info['total_embedded']} "
            f"state={state}"
        )


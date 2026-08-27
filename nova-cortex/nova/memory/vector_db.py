"""Vector database wrapper for semantic memory storage.

Phase B implementation:
- ChromaDB persistent client for vector storage and similarity search
- Collection management (create, get, list, delete)
- CRUD operations with metadata filtering
- Embedding-based similarity queries with optional where filters
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from nova.core.errors import NovaMemoryError

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class VectorDB:
    """ChromaDB vector database integration for semantic memory.

    Provides persistent storage and retrieval of text embeddings with
    associated metadata. Uses ChromaDB's PersistentClient for on-disk storage.

    Usage:
        vdb = VectorDB()
        vdb.initialize()
        vdb.add_documents(["id1"], ["text1"], [[0.1]*768], [{"key": "val"}])
        results = vdb.similarity_search([[0.1]*768], n_results=5)
    """

    persist_directory: Path = Path.home() / ".local" / "share" / "nova" / "chroma_db"
    collection_name: str = "nova_memories"
    embedding_dimension: int = 768  # nomic-embed-text dimension

    _client: Any = None
    _collection: Any = None
    _initialized: bool = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize the ChromaDB persistent client and collection.

        Creates the persistence directory if it doesn't exist.
        Gets or creates the named collection on first access.

        Raises:
            NovaMemoryError: If ChromaDB initialization fails.
        """
        import chromadb
        from chromadb.config import Settings

        try:
            self.persist_directory.mkdir(parents=True, exist_ok=True)

            self._client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=False,
                ),
            )

            # Get or create the collection
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )

            self._initialized = True
            logger.info(
                "VectorDB initialized: path=%s collection=%s",
                self.persist_directory,
                self.collection_name,
            )

        except Exception as exc:
            self._initialized = False
            raise NovaMemoryError(
                f"Failed to initialize ChromaDB: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_initialized(self) -> bool:
        """Return True when the underlying ChromaDB client is ready."""
        return self._initialized and self._client is not None and self._collection is not None

    @property
    def count(self) -> int:
        """Return the number of documents in the collection."""
        if not self.is_initialized:
            return 0
        try:
            return self._collection.count()
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # CRUD Operations
    # ------------------------------------------------------------------

    def add_documents(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """Add documents with embeddings and optional metadata.

        Args:
            ids: Unique identifiers for each document.
            documents: Text content to store.
            embeddings: Pre-computed embedding vectors.
            metadatas: Optional metadata dicts for filtering.

        Raises:
            NovaMemoryError: If the add operation fails.
        """
        if not self.is_initialized:
            raise NovaMemoryError("VectorDB not initialized. Call initialize() first.")

        try:
            self._collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )
        except Exception as exc:
            raise NovaMemoryError(f"Failed to add documents: {exc}") from exc

    def similarity_search(
        self,
        query_embeddings: list[list[float]],
        n_results: int = 10,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar documents by embedding vector.

        Args:
            query_embeddings: Embedding vectors to search with.
            n_results: Maximum number of results to return.
            where: Optional metadata filter dict (e.g. {"source": "chat"}).

        Returns:
            List of dicts with keys: id, document, metadata, distance.

        Raises:
            NovaMemoryError: If the search operation fails.
        """
        if not self.is_initialized:
            raise NovaMemoryError("VectorDB not initialized. Call initialize() first.")

        try:
            results = self._collection.query(
                query_embeddings=query_embeddings,
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise NovaMemoryError(f"Failed to search documents: {exc}") from exc

        # Normalize results into a list of dicts
        output: list[dict[str, Any]] = []
        if results and results["ids"]:
            ids_list = results["ids"][0] if results["ids"] else []
            docs_list = results["documents"][0] if results.get("documents") else []
            metas_list = results["metadatas"][0] if results.get("metadatas") else []
            dists_list = results["distances"][0] if results.get("distances") else []

            for i in range(len(ids_list)):
                output.append({
                    "id": ids_list[i] if i < len(ids_list) else "",
                    "document": docs_list[i] if i < len(docs_list) else "",
                    "metadata": metas_list[i] if i < len(metas_list) else {},
                    "distance": dists_list[i] if i < len(dists_list) else 0.0,
                })

        return output

    def delete(self, ids: list[str]) -> None:
        """Delete documents by their IDs.

        Args:
            ids: List of document IDs to delete.

        Raises:
            NovaMemoryError: If the delete operation fails.
        """
        if not self.is_initialized:
            raise NovaMemoryError("VectorDB not initialized. Call initialize() first.")

        try:
            self._collection.delete(ids=ids)
        except Exception as exc:
            raise NovaMemoryError(f"Failed to delete documents: {exc}") from exc

    def update(
        self,
        ids: list[str],
        documents: list[str] | None = None,
        embeddings: list[list[float]] | None = None,
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """Update existing documents.

        Args:
            ids: Document IDs to update.
            documents: New text content (optional).
            embeddings: New embedding vectors (optional).
            metadatas: New metadata dicts (optional).

        Raises:
            NovaMemoryError: If the update operation fails.
        """
        if not self.is_initialized:
            raise NovaMemoryError("VectorDB not initialized. Call initialize() first.")

        try:
            self._collection.update(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )
        except Exception as exc:
            raise NovaMemoryError(f"Failed to update documents: {exc}") from exc

    # ------------------------------------------------------------------
    # Collection Management
    # ------------------------------------------------------------------

    def list_collections(self) -> list[str]:
        """List all collection names in the database.

        Returns:
            List of collection name strings.
        """
        if not self._client:
            return []
        try:
            collections = self._client.list_collections()
            return [c.name for c in collections]
        except Exception:
            return []

    def delete_collection(self, name: str) -> None:
        """Delete a collection by name.

        Args:
            name: Collection name to delete.
        """
        if not self._client:
            return
        try:
            self._client.delete_collection(name)
            self._collection = None
            self._initialized = False
        except Exception as exc:
            raise NovaMemoryError(f"Failed to delete collection '{name}': {exc}") from exc

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def render_status(self) -> str:
        """Return a single-line status string for IPC diagnostics."""
        state = "ready" if self.is_initialized else "uninitialized"
        doc_count = self.count if self.is_initialized else 0
        return (
            f"vector_db:path={self.persist_directory} "
            f"collection={self.collection_name} "
            f"docs={doc_count} state={state}"
        )


"""Memory and learning package for Nova Cortex.

Provides vector storage (ChromaDB), embeddings (Ollama HTTP API),
and habit tracking (SQLite + pattern detection) infrastructure.

Phase B implementation:
- VectorDB: ChromaDB persistent client for semantic memory storage
- Embeddings: Ollama API client for text-to-vector conversion
- HabitTracker: SQLite-backed command logging with DBSCAN/Heuristic pattern detection

Usage:
    vdb = VectorDB()
    vdb.initialize()
    vdb.add_documents(["id1"], ["text"], [[0.1]*768])

    emb = Embeddings()
    emb.initialize()
    vector = emb.embed("Hello world")

    tracker = HabitTracker()
    tracker.initialize()
    tracker.log_command("list_directory", "/home")
    patterns = tracker.analyze_patterns()
    suggestions = tracker.get_suggestions()
"""

from nova.memory.vector_db import VectorDB
from nova.memory.embeddings import Embeddings
from nova.memory.habit_tracker import HabitTracker, HabitPattern, HabitSuggestion

__all__ = [
    "VectorDB",
    "Embeddings",
    "HabitTracker",
    "HabitPattern",
    "HabitSuggestion",
]


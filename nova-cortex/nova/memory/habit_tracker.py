"""Habit tracking and pattern detection module.

Phase B implementation:
- SQLite database for command and interaction logging
- DBSCAN clustering for temporal pattern detection
- Weekly analysis cron job setup
- Proactive habit suggestion engine

Usage:
    tracker = HabitTracker()
    tracker.initialize()
    tracker.log_command("list_directory", "/home/user/projects", success=True)
    patterns = tracker.analyze_patterns()
    suggestions = tracker.get_suggestions()
"""

from __future__ import annotations

import logging
import sqlite3
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from nova.core.errors import NovaMemoryError

logger = logging.getLogger(__name__)

# Try to import DBSCAN; graceful fallback if sklearn not available
try:
    from sklearn.cluster import DBSCAN
    import numpy as np

    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available. HabitTracker will use heuristic-based pattern detection instead of DBSCAN.")


@dataclass(slots=True)
class HabitPattern:
    """A detected pattern in user behavior."""

    command_type: str  # e.g. "list_directory", "read_file", "llm_chat"
    frequency: float  # Average occurrences per day
    typical_hour: int  # Hour of day when most common (0-23)
    confidence: float  # 0.0 to 1.0
    sample_count: int  # Number of observations
    days_active: list[str]  # Days of week most active (e.g. ["Monday", "Wednesday"])
    description: str  # Human-readable description


@dataclass(slots=True)
class HabitSuggestion:
    """A proactive suggestion based on learned patterns."""

    suggestion_type: str  # "reminder", "insight", "tip"
    message: str
    confidence: float
    based_on: str  # Which pattern triggered this


@dataclass(slots=True)
class HabitTracker:
    """Habit tracking and pattern detection for Nova Cortex.

    Logs user commands and interactions to a local SQLite database,
    then analyzes temporal patterns to detect routines and offer
    proactive suggestions.

    Uses DBSCAN clustering when scikit-learn is available; falls back
    to heuristic-based detection for environments without numpy/sklearn.
    """

    db_path: Path = Path.home() / ".local" / "share" / "nova" / "habits.db"
    min_observations: int = 10  # Minimum data points before analysis starts

    _connection: Any = None  # sqlite3.Connection
    _cursor: Any = None
    _initialized: bool = False
    _pattern_cache: dict[str, float] = field(default_factory=dict)
    _last_analysis: float = 0.0  # Unix timestamp of last pattern analysis

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize the SQLite database and create tables if needed.

        Creates the database directory and sets up the schema for
        command logging and pattern storage.

        Raises:
            NovaMemoryError: If database initialization fails.
        """
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(str(self.db_path))
            self._connection.row_factory = sqlite3.Row
            self._cursor = self._connection.cursor()
            self._create_schema()
            self._initialized = True
            self._load_pattern_cache()
            logger.info("HabitTracker initialized: db=%s", self.db_path)
        except sqlite3.Error as exc:
            raise NovaMemoryError(f"Failed to initialize habit tracker DB: {exc}") from exc

    def _create_schema(self) -> None:
        """Create the database schema."""
        self._cursor.executescript("""
            CREATE TABLE IF NOT EXISTS command_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                command TEXT NOT NULL,
                arguments TEXT DEFAULT '',
                success INTEGER NOT NULL DEFAULT 1,
                duration_ms REAL DEFAULT 0,
                context TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command_type TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                data TEXT NOT NULL,
                confidence REAL DEFAULT 0.0,
                created_at REAL NOT NULL,
                last_observed REAL NOT NULL,
                UNIQUE(command_type, pattern_type)
            );

            CREATE TABLE IF NOT EXISTS suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                suggestion_type TEXT NOT NULL,
                message TEXT NOT NULL,
                confidence REAL DEFAULT 0.0,
                based_on TEXT DEFAULT '',
                shown INTEGER DEFAULT 0,
                created_at REAL NOT NULL,
                dismissed INTEGER DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_command_log_timestamp ON command_log(timestamp);
            CREATE INDEX IF NOT EXISTS idx_command_log_command ON command_log(command);
            CREATE INDEX IF NOT EXISTS idx_patterns_command ON patterns(command_type);
            CREATE INDEX IF NOT EXISTS idx_suggestions_shown ON suggestions(shown);
        """)
        self._connection.commit()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_initialized(self) -> bool:
        """Return True when the SQLite database connection is ready."""
        return self._initialized and self._connection is not None

    @property
    def total_commands(self) -> int:
        """Return total number of logged commands."""
        if not self.is_initialized:
            return 0
        try:
            row = self._cursor.execute("SELECT COUNT(*) FROM command_log").fetchone()
            return row[0] if row else 0
        except sqlite3.Error:
            return 0

    # ------------------------------------------------------------------
    # Command Logging
    # ------------------------------------------------------------------

    def log_command(
        self,
        command: str,
        arguments: str = "",
        success: bool = True,
        duration_ms: float = 0.0,
        context: str = "",
    ) -> None:
        """Log a user command or interaction.

        Args:
            command: The command or action name (e.g. "list_directory", "llm_chat").
            arguments: Arguments passed to the command.
            success: Whether the command completed successfully.
            duration_ms: Execution duration in milliseconds.
            context: Additional context (e.g. "user_query", "system_action").
        """
        if not self.is_initialized:
            logger.warning("HabitTracker not initialized. Skipping log.")
            return

        try:
            self._cursor.execute(
                """INSERT INTO command_log
                   (timestamp, command, arguments, success, duration_ms, context)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (time.time(), command, arguments, 1 if success else 0, duration_ms, context),
            )
            self._connection.commit()
        except sqlite3.Error as exc:
            logger.error("Failed to log command: %s", exc)

    def get_recent_commands(self, hours: int = 24) -> list[dict[str, Any]]:
        """Get commands logged in the last N hours.

        Args:
            hours: Number of hours to look back.

        Returns:
            List of command log entries as dicts.
        """
        if not self.is_initialized:
            return []

        cutoff = time.time() - (hours * 3600)
        try:
            rows = self._cursor.execute(
                """SELECT * FROM command_log WHERE timestamp >= ? ORDER BY timestamp DESC""",
                (cutoff,),
            ).fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error:
            return []

    def get_command_stats(self, days: int = 7) -> dict[str, Any]:
        """Get aggregate statistics for the last N days.

        Args:
            days: Number of days to analyze.

        Returns:
            Dict with stats: total_commands, unique_commands, top_commands,
            hourly_distribution, daily_distribution.
        """
        if not self.is_initialized:
            return {}

        cutoff = time.time() - (days * 86400)
        stats: dict[str, Any] = {
            "total_commands": 0,
            "unique_commands": 0,
            "top_commands": [],
            "hourly_distribution": defaultdict(int),
            "daily_distribution": defaultdict(int),
            "avg_duration_ms": 0.0,
            "success_rate": 0.0,
        }

        try:
            rows = self._cursor.execute(
                """SELECT * FROM command_log WHERE timestamp >= ?""",
                (cutoff,),
            ).fetchall()

            commands_count: dict[str, int] = {}
            total_duration = 0.0
            total_success = 0
            total = len(rows)

            for row in rows:
                d = dict(row)
                cmd = d["command"]
                commands_count[cmd] = commands_count.get(cmd, 0) + 1

                # Hourly
                dt = datetime.fromtimestamp(d["timestamp"], tz=timezone.utc)
                stats["hourly_distribution"][dt.hour] += 1
                stats["daily_distribution"][dt.strftime("%A")] += 1

                total_duration += d.get("duration_ms", 0)
                if d.get("success", 1):
                    total_success += 1

            stats["total_commands"] = total
            stats["unique_commands"] = len(commands_count)
            stats["top_commands"] = sorted(
                commands_count.items(), key=lambda x: x[1], reverse=True
            )[:10]
            stats["avg_duration_ms"] = total_duration / total if total > 0 else 0
            stats["success_rate"] = (total_success / total * 100) if total > 0 else 0

        except sqlite3.Error:
            pass

        return stats

    # ------------------------------------------------------------------
    # Pattern Detection (DBSCAN + Heuristic)
    # ------------------------------------------------------------------

    def analyze_patterns(self) -> list[HabitPattern]:
        """Analyze command logs to detect temporal patterns.

        Uses DBSCAN clustering when available for sophisticated
        temporal clustering, or falls back to heuristic-based detection.

        Returns:
            List of detected HabitPattern objects.
        """
        if not self.is_initialized:
            return []

        self._last_analysis = time.time()
        patterns: list[HabitPattern] = []

        try:
            if _SKLEARN_AVAILABLE:
                patterns = self._analyze_dbscan()
            else:
                patterns = self._analyze_heuristic()

            # Cache pattern confidences
            self._pattern_cache = {
                p.command_type: p.confidence for p in patterns
            }

            # Store patterns in database
            self._store_patterns(patterns)

        except Exception as exc:
            logger.error("Pattern analysis failed: %s", exc)

        return patterns

    def _analyze_dbscan(self) -> list[HabitPattern]:
        """Perform DBSCAN clustering on temporal command data."""
        patterns: list[HabitPattern] = []

        # Get commands from the last 14 days
        cutoff = time.time() - (14 * 86400)
        rows = self._cursor.execute(
            """SELECT command, timestamp, success FROM command_log
               WHERE timestamp >= ? ORDER BY timestamp""",
            (cutoff,),
        ).fetchall()

        if len(rows) < self.min_observations:
            return patterns

        # Group by command type
        command_groups: dict[str, list[float]] = defaultdict(list)
        for row in rows:
            cmd = row["command"]
            ts = row["timestamp"]
            command_groups[cmd].append(ts)

        for cmd, timestamps in command_groups.items():
            if len(timestamps) < self.min_observations // 2:
                continue

            # Convert to numpy array of hour-of-day features
            hours = np.array([
                [datetime.fromtimestamp(ts, tz=timezone.utc).hour]
                for ts in timestamps
            ])

            # DBSCAN clustering on hour of day
            clustering = DBSCAN(eps=2.0, min_samples=3).fit(hours)
            labels = clustering.labels_

            # Find the dominant cluster (most common label excluding noise -1)
            valid_labels = [l for l in labels if l >= 0]
            if not valid_labels:
                continue

            dominant_label = max(set(valid_labels), key=valid_labels.count)
            cluster_mask = labels == dominant_label
            cluster_hours = hours[cluster_mask]

            typical_hour = int(np.mean(cluster_hours))
            cluster_size = int(np.sum(cluster_mask))
            total_count = len(timestamps)

            # Calculate frequency (per day)
            time_span_days = max(
                (max(timestamps) - min(timestamps)) / 86400, 1
            )
            frequency = cluster_size / time_span_days

            # Calculate confidence based on cluster purity and size
            purity = cluster_size / total_count
            confidence = min(1.0, purity * (1 - 1 / (cluster_size + 1)))

            # Determine active days
            days_active: set[str] = set()
            for i, ts in enumerate(timestamps):
                if labels[i] == dominant_label:
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                    days_active.add(dt.strftime("%A"))

            patterns.append(HabitPattern(
                command_type=cmd,
                frequency=round(frequency, 2),
                typical_hour=typical_hour,
                confidence=round(confidence, 2),
                sample_count=cluster_size,
                days_active=sorted(days_active),
                description=self._describe_pattern(cmd, frequency, typical_hour, days_active),
            ))

        return patterns

    def _analyze_heuristic(self) -> list[HabitPattern]:
        """Heuristic-based pattern detection fallback.

        Uses simpler statistical methods when scikit-learn is not available.
        """
        patterns: list[HabitPattern] = []

        cutoff = time.time() - (14 * 86400)
        rows = self._cursor.execute(
            """SELECT command, timestamp, success FROM command_log
               WHERE timestamp >= ? ORDER BY timestamp""",
            (cutoff,),
        ).fetchall()

        if len(rows) < self.min_observations:
            return patterns

        command_groups: dict[str, list[float]] = defaultdict(list)
        for row in rows:
            command_groups[row["command"]].append(row["timestamp"])

        for cmd, timestamps in command_groups.items():
            if len(timestamps) < self.min_observations // 2:
                continue

            # Calculate hour distribution
            hour_counts: dict[int, int] = defaultdict(int)
            days_active: set[str] = set()
            for ts in timestamps:
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                hour_counts[dt.hour] += 1
                days_active.add(dt.strftime("%A"))

            # Find peak hour
            typical_hour = max(hour_counts, key=hour_counts.get)
            peak_count = hour_counts[typical_hour]
            total_count = len(timestamps)

            # Frequency per day
            time_span_days = max(
                (max(timestamps) - min(timestamps)) / 86400, 1
            )
            frequency = total_count / time_span_days

            # Confidence: how much activity is concentrated at peak hour
            concentration = peak_count / total_count
            confidence = min(1.0, concentration * (1 - 1 / (total_count + 1)))

            patterns.append(HabitPattern(
                command_type=cmd,
                frequency=round(frequency, 2),
                typical_hour=typical_hour,
                confidence=round(confidence, 2),
                sample_count=total_count,
                days_active=sorted(days_active),
                description=self._describe_pattern(cmd, frequency, typical_hour, days_active),
            ))

        return patterns

    def _describe_pattern(
        self,
        command: str,
        frequency: float,
        hour: int,
        days: set[str],
    ) -> str:
        """Generate a human-readable description of a pattern."""
        hour_label = self._hour_to_period(hour)
        freq_label = "very frequent" if frequency > 20 else \
                     "frequent" if frequency > 10 else \
                     "regular" if frequency > 3 else "occasional"

        day_str = ", ".join(sorted(days)) if days else "various days"

        return (
            f"You {freq_label}ly use '{command}' during the {hour_label} "
            f"on {day_str} ({frequency:.1f}x/day)"
        )

    @staticmethod
    def _hour_to_period(hour: int) -> str:
        """Convert hour (0-23) to time period name."""
        if 5 <= hour < 8:
            return "early morning"
        elif 8 <= hour < 12:
            return "morning"
        elif 12 <= hour < 14:
            return "lunchtime"
        elif 14 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        elif 21 <= hour < 24:
            return "night"
        else:
            return "late night"

    # ------------------------------------------------------------------
    # Pattern Storage
    # ------------------------------------------------------------------

    def _store_patterns(self, patterns: list[HabitPattern]) -> None:
        """Store detected patterns in the database."""
        now = time.time()
        for p in patterns:
            data = {
                "frequency": p.frequency,
                "typical_hour": p.typical_hour,
                "days_active": p.days_active,
                "description": p.description,
            }
            try:
                self._cursor.execute(
                    """INSERT OR REPLACE INTO patterns
                       (command_type, pattern_type, data, confidence, created_at, last_observed)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (p.command_type, "temporal", str(data), p.confidence, now, now),
                )
            except sqlite3.Error as exc:
                logger.error("Failed to store pattern: %s", exc)
        self._connection.commit()

    def _load_pattern_cache(self) -> None:
        """Load existing pattern confidences from the database."""
        try:
            rows = self._cursor.execute(
                "SELECT command_type, confidence FROM patterns"
            ).fetchall()
            self._pattern_cache = {row["command_type"]: row["confidence"] for row in rows}
        except sqlite3.Error:
            self._pattern_cache = {}

    # ------------------------------------------------------------------
    # Suggestion Engine
    # ------------------------------------------------------------------

    def get_suggestions(self, max_suggestions: int = 5) -> list[HabitSuggestion]:
        """Generate proactive suggestions based on learned patterns.

        Analyzes current patterns and generates actionable suggestions,
        including reminders, insights, and tips for better workflows.

        Args:
            max_suggestions: Maximum number of suggestions to return.

        Returns:
            List of HabitSuggestion objects.
        """
        if not self.is_initialized:
            return []

        suggestions: list[HabitSuggestion] = []

        try:
            # Get patterns
            patterns = self.analyze_patterns()
            if not patterns:
                return suggestions

            # Get recent stats
            recent = self.get_command_stats(days=3)
            total_recent = recent.get("total_commands", 0)

            # 1. Usage peak suggestion
            if patterns:
                most_frequent = max(patterns, key=lambda p: p.frequency)
                if most_frequent.confidence > 0.5 and most_frequent.frequency > 5:
                    suggestions.append(HabitSuggestion(
                        suggestion_type="insight",
                        message=(
                            f"Your peak activity is during the "
                            f"{self._hour_to_period(most_frequent.typical_hour)} "
                            f"with '{most_frequent.command_type}' being your most "
                            f"used command ({most_frequent.frequency:.1f}x/day)"
                        ),
                        confidence=most_frequent.confidence,
                        based_on=f"pattern:{most_frequent.command_type}",
                    ))

            # 2. Low usage suggestion
            if total_recent < 5:
                suggestions.append(HabitSuggestion(
                    suggestion_type="tip",
                    message="You've been less active recently. Try asking me something!",
                    confidence=0.7,
                    based_on="usage:low_activity",
                ))

            # 3. Error rate suggestion
            success_rate = recent.get("success_rate", 100)
            if success_rate < 80:
                suggestions.append(HabitSuggestion(
                    suggestion_type="reminder",
                    message=(
                        f"Command success rate is {success_rate:.0f}%. "
                        f"Some commands may need attention."
                    ),
                    confidence=min(1.0, (100 - success_rate) / 50),
                    based_on="error_rate:high",
                ))

            # 4. Time-based suggestions
            current_hour = datetime.now(timezone.utc).hour
            if 8 <= current_hour <= 10:
                # Morning suggestion
                suggestions.append(HabitSuggestion(
                    suggestion_type="reminder",
                    message="Good morning! I'm ready to help you with your tasks.",
                    confidence=1.0,
                    based_on="time:morning",
                ))
            elif 21 <= current_hour <= 23:
                suggestions.append(HabitSuggestion(
                    suggestion_type="insight",
                    message="Working late! Let me know if you need help wrapping up.",
                    confidence=0.8,
                    based_on="time:night",
                ))

            # 5. Command diversity suggestion
            unique_count = recent.get("unique_commands", 0)
            if unique_count <= 2 and total_recent > self.min_observations:
                suggestions.append(HabitSuggestion(
                    suggestion_type="tip",
                    message="Try using different commands! I can help with file operations, "
                            "system info, and more.",
                    confidence=0.6,
                    based_on="usage:low_diversity",
                ))

        except Exception as exc:
            logger.error("Failed to generate suggestions: %s", exc)

        # Store suggestions in database
        self._store_suggestions(suggestions)

        return suggestions[:max_suggestions]

    def _store_suggestions(self, suggestions: list[HabitSuggestion]) -> None:
        """Store generated suggestions in the database."""
        now = time.time()
        for s in suggestions:
            try:
                self._cursor.execute(
                    """INSERT INTO suggestions
                       (suggestion_type, message, confidence, based_on, created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (s.suggestion_type, s.message, s.confidence, s.based_on, now),
                )
            except sqlite3.Error:
                pass
        self._connection.commit()

    def get_pending_suggestions(self) -> list[dict[str, Any]]:
        """Get suggestions that haven't been shown to the user yet.

        Returns:
            List of suggestion dicts.
        """
        if not self.is_initialized:
            return []
        try:
            rows = self._cursor.execute(
                """SELECT * FROM suggestions
                   WHERE shown = 0 AND dismissed = 0
                   ORDER BY confidence DESC LIMIT 10"""
            ).fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error:
            return []

    def mark_suggestion_shown(self, suggestion_id: int) -> None:
        """Mark a suggestion as shown to the user."""
        if not self.is_initialized:
            return
        try:
            self._cursor.execute(
                "UPDATE suggestions SET shown = 1 WHERE id = ?",
                (suggestion_id,),
            )
            self._connection.commit()
        except sqlite3.Error:
            pass

    def dismiss_suggestion(self, suggestion_id: int) -> None:
        """Dismiss a suggestion permanently."""
        if not self.is_initialized:
            return
        try:
            self._cursor.execute(
                "UPDATE suggestions SET dismissed = 1 WHERE id = ?",
                (suggestion_id,),
            )
            self._connection.commit()
        except sqlite3.Error:
            pass

    # ------------------------------------------------------------------
    # Weekly Analysis
    # ------------------------------------------------------------------

    def run_weekly_analysis(self) -> dict[str, Any]:
        """Run comprehensive weekly analysis.

        Should be called periodically (e.g., once per day via cron).
        Returns a summary of findings.

        Returns:
            Dict with analysis results.
        """
        if not self.is_initialized:
            return {"error": "not_initialized"}

        analysis: dict[str, Any] = {
            "timestamp": time.time(),
            "patterns_detected": 0,
            "suggestions_generated": 0,
            "total_commands_logged": self.total_commands,
            "summary": "",
        }

        # Run pattern analysis
        patterns = self.analyze_patterns()
        analysis["patterns_detected"] = len(patterns)

        # Generate suggestions
        suggestions = self.get_suggestions(max_suggestions=10)
        analysis["suggestions_generated"] = len(suggestions)

        # Build summary
        if patterns:
            top_pattern = max(patterns, key=lambda p: p.confidence)
            analysis["summary"] = (
                f"Weekly analysis complete. Detected {len(patterns)} patterns. "
                f"Top pattern: {top_pattern.description}. "
                f"Generated {len(suggestions)} suggestions."
            )
        else:
            analysis["summary"] = (
                f"Weekly analysis complete. No strong patterns detected yet "
                f"(need at least {self.min_observations} observations). "
                f"Total commands logged: {self.total_commands}."
            )

        return analysis

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def render_status(self) -> str:
        """Return a single-line status string for IPC diagnostics."""
        state = "ready" if self.is_initialized else "uninitialized"
        patterns = len(self._pattern_cache)
        return (
            f"habit_tracker:db={self.db_path} "
            f"min_observations={self.min_observations} "
            f"patterns={patterns} "
            f"total_commands={self.total_commands} "
            f"state={state}"
        )

    def cleanup(self) -> None:
        """Close database connection and clean up resources."""
        self._initialized = False
        if self._connection:
            try:
                self._connection.close()
            except sqlite3.Error:
                pass
            self._connection = None
            self._cursor = None


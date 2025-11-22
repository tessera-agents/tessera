"""
Metrics storage for Tessera using SQLite.

Stores:
- Task assignments and execution history
- Agent performance metrics
- Cost tracking
- Session state
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from ..config.xdg import get_metrics_db_path


class MetricsStore:
    """
    SQLite-based metrics storage for Tessera.

    Tracks task assignments, agent performance, and costs.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize metrics store.

        Args:
            db_path: Path to metrics database (default: ~/.cache/tessera/metrics.db)
        """
        self.db_path = db_path or get_metrics_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Task assignments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT UNIQUE NOT NULL,
                task_description TEXT,
                task_type TEXT,
                agent_name TEXT NOT NULL,
                agent_config_snapshot JSON NOT NULL,
                assigned_at TIMESTAMP NOT NULL,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT NOT NULL,
                result_summary TEXT,
                error_message TEXT,
                llm_calls_count INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                total_cost_usd REAL DEFAULT 0.0,
                trace_id TEXT
            )
        """)

        # Agent performance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                task_id TEXT NOT NULL,
                phase TEXT,
                success BOOLEAN NOT NULL,
                duration_seconds INTEGER,
                cost_usd REAL,
                quality_score REAL,
                reassigned BOOLEAN DEFAULT FALSE,
                off_topic BOOLEAN DEFAULT FALSE,
                timestamp TIMESTAMP NOT NULL,
                FOREIGN KEY (task_id) REFERENCES task_assignments(task_id)
            )
        """)

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_task_agent ON task_assignments(agent_name)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_task_status ON task_assignments(status)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_task_assigned_at ON task_assignments(assigned_at)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_perf_agent ON agent_performance(agent_name)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_perf_timestamp ON agent_performance(timestamp)"
        )

        conn.commit()
        conn.close()

    def record_task_assignment(
        self,
        task_id: str,
        task_description: str,
        agent_name: str,
        agent_config: Dict[str, Any],
        task_type: Optional[str] = None,
    ) -> None:
        """
        Record a new task assignment.

        Args:
            task_id: Unique task identifier
            task_description: Human-readable task description
            agent_name: Name of assigned agent
            agent_config: Complete agent configuration snapshot
            task_type: Optional task type classification
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO task_assignments
            (task_id, task_description, task_type, agent_name, agent_config_snapshot,
             assigned_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                task_id,
                task_description,
                task_type,
                agent_name,
                json.dumps(agent_config),
                datetime.now().isoformat(),
                "pending",
            ),
        )

        conn.commit()
        conn.close()

    def update_task_status(
        self,
        task_id: str,
        status: str,
        result_summary: Optional[str] = None,
        error_message: Optional[str] = None,
        llm_calls_count: Optional[int] = None,
        total_tokens: Optional[int] = None,
        total_cost_usd: Optional[float] = None,
        trace_id: Optional[str] = None,
    ) -> None:
        """
        Update task status and metrics.

        Args:
            task_id: Task identifier
            status: New status (pending, in_progress, completed, failed)
            result_summary: Optional summary of results
            error_message: Optional error message if failed
            llm_calls_count: Number of LLM API calls made
            total_tokens: Total tokens used
            total_cost_usd: Total cost in USD
            trace_id: OTEL trace ID for correlation
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        updates = ["status = ?"]
        params = [status]

        if status == "in_progress" and not self._get_started_at(task_id):
            updates.append("started_at = ?")
            params.append(datetime.now().isoformat())

        if status in ("completed", "failed"):
            updates.append("completed_at = ?")
            params.append(datetime.now().isoformat())

        if result_summary is not None:
            updates.append("result_summary = ?")
            params.append(result_summary)

        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)

        if llm_calls_count is not None:
            updates.append("llm_calls_count = ?")
            params.append(llm_calls_count)

        if total_tokens is not None:
            updates.append("total_tokens = ?")
            params.append(total_tokens)

        if total_cost_usd is not None:
            updates.append("total_cost_usd = ?")
            params.append(total_cost_usd)

        if trace_id is not None:
            updates.append("trace_id = ?")
            params.append(trace_id)

        params.append(task_id)

        query = f"""
            UPDATE task_assignments
            SET {", ".join(updates)}
            WHERE task_id = ?
        """

        cursor.execute(query, params)
        conn.commit()
        conn.close()

    def _get_started_at(self, task_id: str) -> Optional[datetime]:
        """Get started_at timestamp for a task."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        result = cursor.execute(
            "SELECT started_at FROM task_assignments WHERE task_id = ?", (task_id,)
        ).fetchone()
        conn.close()
        return result[0] if result and result[0] else None

    def record_agent_performance(
        self,
        agent_name: str,
        task_id: str,
        success: bool,
        duration_seconds: Optional[int] = None,
        cost_usd: Optional[float] = None,
        phase: Optional[str] = None,
        quality_score: Optional[float] = None,
        reassigned: bool = False,
        off_topic: bool = False,
    ) -> None:
        """
        Record agent performance metrics.

        Args:
            agent_name: Agent name
            task_id: Task identifier
            success: Whether task completed successfully
            duration_seconds: Task duration
            cost_usd: Cost in USD
            phase: SDLC phase
            quality_score: Quality assessment score (0-100)
            reassigned: Whether task was reassigned from this agent
            off_topic: Whether agent went off-topic
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO agent_performance
            (agent_name, task_id, phase, success, duration_seconds, cost_usd,
             quality_score, reassigned, off_topic, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                agent_name,
                task_id,
                phase,
                success,
                duration_seconds,
                cost_usd,
                quality_score,
                reassigned,
                off_topic,
                datetime.now().isoformat(),
            ),
        )

        conn.commit()
        conn.close()

    def get_agent_stats(self, agent_name: str, days: Optional[int] = None) -> Dict[str, Any]:
        """
        Get performance statistics for an agent.

        Args:
            agent_name: Agent name
            days: Optional number of days to look back (None = all time)

        Returns:
            Dict with performance statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        date_filter = ""
        params: List[Any] = [agent_name]

        if days:
            date_filter = "AND timestamp > datetime('now', ?)"
            params.append(f"-{days} days")

        query = f"""
            SELECT
                COUNT(*) as total_tasks,
                SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_tasks,
                SUM(CASE WHEN reassigned THEN 1 ELSE 0 END) as reassigned_tasks,
                SUM(CASE WHEN off_topic THEN 1 ELSE 0 END) as off_topic_tasks,
                AVG(duration_seconds) as avg_duration_seconds,
                SUM(cost_usd) as total_cost_usd,
                AVG(quality_score) as avg_quality_score
            FROM agent_performance
            WHERE agent_name = ? {date_filter}
        """

        result = cursor.execute(query, params).fetchone()
        conn.close()

        if not result:
            return {}

        (
            total,
            successful,
            reassigned,
            off_topic,
            avg_duration,
            total_cost,
            avg_quality,
        ) = result

        return {
            "total_tasks": total or 0,
            "successful_tasks": successful or 0,
            "failed_tasks": (total or 0) - (successful or 0),
            "success_rate": (successful / total) if total else 0.0,
            "reassigned_tasks": reassigned or 0,
            "reassignment_rate": (reassigned / total) if total else 0.0,
            "off_topic_tasks": off_topic or 0,
            "off_topic_rate": (off_topic / total) if total else 0.0,
            "avg_duration_seconds": avg_duration or 0.0,
            "total_cost_usd": total_cost or 0.0,
            "avg_quality_score": avg_quality or 0.0,
        }

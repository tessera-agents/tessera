"""Tests for workflow DAG visualization."""

import tempfile
from pathlib import Path

import pytest

from tessera.visualization.dag import WorkflowDAG, export_dag_to_mermaid
from tessera.workflow.task_queue import QueuedTask, TaskStatus


@pytest.mark.unit
class TestWorkflowDAG:
    """Test workflow DAG functionality."""

    def test_dag_creation(self):
        """Test creating DAG from tasks."""
        tasks = [
            QueuedTask(task_id="t1", description="Task 1", dependencies=[]),
            QueuedTask(task_id="t2", description="Task 2", dependencies=["t1"]),
            QueuedTask(task_id="t3", description="Task 3", dependencies=["t1", "t2"]),
        ]

        dag = WorkflowDAG(tasks)

        assert len(dag.nodes) == 3
        assert len(dag.edges) == 3  # t1->t2, t1->t3, t2->t3

    def test_to_mermaid(self):
        """Test exporting to Mermaid format."""
        tasks = [
            QueuedTask(task_id="t1", description="Start", dependencies=[]),
            QueuedTask(task_id="t2", description="Middle", dependencies=["t1"]),
        ]
        tasks[0].status = TaskStatus.COMPLETED

        dag = WorkflowDAG(tasks)
        mermaid = dag.to_mermaid()

        assert "graph TD" in mermaid
        assert "t1" in mermaid
        assert "t2" in mermaid
        assert "-->" in mermaid
        assert "classDef completed" in mermaid

    def test_to_dot(self):
        """Test exporting to DOT format."""
        tasks = [
            QueuedTask(task_id="t1", description="Task 1", dependencies=[]),
            QueuedTask(task_id="t2", description="Task 2", dependencies=["t1"]),
        ]

        dag = WorkflowDAG(tasks)
        dot = dag.to_dot()

        assert "digraph workflow" in dot
        assert '"t1"' in dot
        assert '"t2"' in dot
        assert "->" in dot

    def test_get_execution_order(self):
        """Test topological sort for execution order."""
        tasks = [
            QueuedTask(task_id="t1", description="Base", dependencies=[]),
            QueuedTask(task_id="t2", description="Depends on t1", dependencies=["t1"]),
            QueuedTask(task_id="t3", description="Also depends on t1", dependencies=["t1"]),
            QueuedTask(task_id="t4", description="Depends on t2 and t3", dependencies=["t2", "t3"]),
        ]

        dag = WorkflowDAG(tasks)
        batches = dag.get_execution_order()

        # Should have 3 batches
        assert len(batches) == 3

        # First batch: t1 (no dependencies)
        assert batches[0] == ["t1"]

        # Second batch: t2 and t3 (can run in parallel)
        assert set(batches[1]) == {"t2", "t3"}

        # Third batch: t4
        assert batches[2] == ["t4"]

    def test_get_critical_path(self):
        """Test finding critical path."""
        tasks = [
            QueuedTask(task_id="t1", description="Start", dependencies=[]),
            QueuedTask(task_id="t2", description="Short", dependencies=["t1"]),
            QueuedTask(task_id="t3", description="Long chain 1", dependencies=["t1"]),
            QueuedTask(task_id="t4", description="Long chain 2", dependencies=["t3"]),
            QueuedTask(task_id="t5", description="Long chain 3", dependencies=["t4"]),
        ]

        dag = WorkflowDAG(tasks)
        critical_path = dag.get_critical_path()

        # Critical path should be longest: t1 -> t3 -> t4 -> t5
        assert len(critical_path) >= 4
        assert "t1" in critical_path

    def test_export_to_file(self):
        """Test exporting DAG to file."""
        tasks = [
            QueuedTask(task_id="t1", description="Task 1", dependencies=[]),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "dag.mmd"

            mermaid = export_dag_to_mermaid(tasks, output_file)

            assert output_file.exists()
            assert output_file.read_text() == mermaid

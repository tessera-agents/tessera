"""
Workflow DAG visualization.

Creates visualizations of task dependencies and execution flow.
"""

from pathlib import Path
from typing import Any

from ..logging_config import get_logger
from ..workflow.task_queue import QueuedTask, TaskStatus

logger = get_logger(__name__)


class WorkflowDAG:
    """
    Directed Acyclic Graph representation of workflow.

    Builds DAG from task queue and generates visualizations.
    """

    def __init__(self, tasks: list[QueuedTask]) -> None:
        """
        Initialize DAG from tasks.

        Args:
            tasks: List of tasks with dependencies
        """
        self.tasks = {task.task_id: task for task in tasks}
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[tuple[str, str]] = []

        self._build_graph()

    def _build_graph(self) -> None:
        """Build graph nodes and edges from tasks."""
        # Create nodes
        for task_id, task in self.tasks.items():
            self.nodes[task_id] = {
                "id": task_id,
                "label": task.description[:50],  # Truncate long descriptions
                "status": task.status.value,
                "agent": task.agent_name,
            }

        # Create edges from dependencies
        for task_id, task in self.tasks.items():
            for dep_id in task.dependencies:
                if dep_id in self.tasks:
                    self.edges.append((dep_id, task_id))

    def to_mermaid(self) -> str:
        """
        Export DAG to Mermaid diagram format.

        Returns:
            Mermaid diagram string
        """
        lines = ["graph TD"]

        # Add nodes with styling based on status
        for task_id, node in self.nodes.items():
            status = node["status"]

            # Node ID and label
            node_id = task_id.replace("-", "_")
            label = node["label"].replace('"', "'")

            # Style based on status
            if status == TaskStatus.COMPLETED.value:
                style = ":::completed"
            elif status == TaskStatus.FAILED.value:
                style = ":::failed"
            elif status == TaskStatus.IN_PROGRESS.value:
                style = ":::inprogress"
            else:
                style = ""

            lines.append(f'    {node_id}["{label}"]{style}')

        # Add edges
        for source, target in self.edges:
            source_id = source.replace("-", "_")
            target_id = target.replace("-", "_")
            lines.append(f"    {source_id} --> {target_id}")

        # Add styling
        lines.extend(
            [
                "",
                "    classDef completed fill:#90EE90,stroke:#228B22",
                "    classDef failed fill:#FFB6C1,stroke:#DC143C",
                "    classDef inprogress fill:#87CEEB,stroke:#4169E1",
            ]
        )

        return "\n".join(lines)

    def to_dot(self) -> str:
        """
        Export DAG to Graphviz DOT format.

        Returns:
            DOT format string
        """
        lines = ["digraph workflow {"]
        lines.append("    rankdir=TB;")
        lines.append("    node [shape=box, style=filled];")

        # Add nodes
        for task_id, node in self.nodes.items():
            status = node["status"]

            # Color based on status
            if status == TaskStatus.COMPLETED.value:
                color = "lightgreen"
            elif status == TaskStatus.FAILED.value:
                color = "lightcoral"
            elif status == TaskStatus.IN_PROGRESS.value:
                color = "lightblue"
            else:
                color = "white"

            label = node["label"].replace('"', '\\"')
            lines.append(f'    "{task_id}" [label="{label}", fillcolor={color}];')

        # Add edges
        for source, target in self.edges:
            lines.append(f'    "{source}" -> "{target}";')

        lines.append("}")

        return "\n".join(lines)

    def get_execution_order(self) -> list[list[str]]:
        """
        Get topological execution order (batches of tasks that can run in parallel).

        Returns:
            List of batches, where each batch can execute in parallel
        """
        # Calculate in-degree for each node
        in_degree = dict.fromkeys(self.tasks, 0)

        for _source, target in self.edges:
            in_degree[target] += 1

        # Topological sort with batching
        batches = []
        remaining = set(self.tasks.keys())

        while remaining:
            # Find nodes with no dependencies (in-degree == 0)
            batch = [task_id for task_id in remaining if in_degree[task_id] == 0]

            if not batch:
                # Circular dependency detected
                logger.warning("Circular dependency detected in DAG")
                break

            batches.append(batch)

            # Remove batch from remaining and update in-degrees
            for task_id in batch:
                remaining.remove(task_id)

                # Reduce in-degree for dependent tasks
                for source, target in self.edges:
                    if source == task_id:
                        in_degree[target] -= 1

        return batches

    def get_critical_path(self) -> list[str]:
        """
        Get critical path (longest path through DAG).

        Returns:
            List of task IDs on critical path
        """
        # Simple implementation: find path with most nodes
        # More sophisticated could use actual durations

        def dfs(node: str, visited: set[str]) -> list[str]:
            visited = visited | {node}

            # Find all children
            children = [target for source, target in self.edges if source == node]

            if not children:
                return [node]

            # Find longest path through children
            longest = []
            for child in children:
                if child not in visited:  # Avoid cycles
                    path = dfs(child, visited)
                    if len(path) > len(longest):
                        longest = path

            return [node, *longest]

        # Find root nodes (no incoming edges)
        roots = [task_id for task_id in self.tasks if not any(target == task_id for _, target in self.edges)]

        # Find longest path from any root
        critical_path = []
        for root in roots:
            path = dfs(root, set())
            if len(path) > len(critical_path):
                critical_path = path

        return critical_path


def create_dag_visualization(tasks: list[QueuedTask]) -> WorkflowDAG:
    """
    Create DAG visualization from task list.

    Args:
        tasks: List of tasks

    Returns:
        WorkflowDAG instance
    """
    return WorkflowDAG(tasks)


def export_dag_to_mermaid(tasks: list[QueuedTask], output_file: Path | None = None) -> str:
    """
    Export task DAG to Mermaid format.

    Args:
        tasks: List of tasks
        output_file: Optional file to write diagram to

    Returns:
        Mermaid diagram string
    """
    dag = create_dag_visualization(tasks)
    mermaid = dag.to_mermaid()

    if output_file:
        output_file.write_text(mermaid)
        logger.info(f"Exported DAG to {output_file}")

    return mermaid


def export_dag_to_dot(tasks: list[QueuedTask], output_file: Path | None = None) -> str:
    """
    Export task DAG to Graphviz DOT format.

    Args:
        tasks: List of tasks
        output_file: Optional file to write diagram to

    Returns:
        DOT format string
    """
    dag = create_dag_visualization(tasks)
    dot = dag.to_dot()

    if output_file:
        output_file.write_text(dot)
        logger.info(f"Exported DAG to {output_file}")

    return dot

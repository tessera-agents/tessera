"""
Supervisor agent implementation.
"""

import json
from datetime import UTC, datetime
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from .config import SUPERVISOR_PROMPT, FrameworkConfig
from .llm import create_llm
from .models import AgentResponse, SubTask, Task, TaskStatus


class SupervisorAgent:
    """
    Supervisor agent that orchestrates multi-agent tasks.

    The supervisor decomposes complex objectives into subtasks,
    assigns them to agents, monitors progress, and ensures quality.
    """

    def __init__(
        self,
        llm: BaseChatModel | None = None,
        config: FrameworkConfig | None = None,
        system_prompt: str = SUPERVISOR_PROMPT,
    ) -> None:
        """
        Initialize the supervisor agent.

        Args:
            llm: Language model to use (creates default if None)
            config: Framework configuration
            system_prompt: Custom system prompt (uses default if not provided)
        """
        self.config = config or FrameworkConfig.from_env()
        self.llm = llm or create_llm(self.config.llm)
        self.system_prompt = system_prompt
        self.tasks: dict[str, Task] = {}

    def decompose_task(self, objective: str, callbacks: list | None = None) -> Task:
        """
        Decompose a complex objective into subtasks.

        Args:
            objective: The high-level objective to decompose

        Returns:
            Task object with subtasks
        """
        prompt = f"""
Objective: {objective}

Decompose this objective into discrete, actionable subtasks.
For each subtask, provide:
1. A clear description
2. Acceptance criteria (list of requirements)
3. Dependencies on other subtasks (if any)

Respond in JSON format:
{{
    "goal": "one-sentence restatement of the objective",
    "subtasks": [
        {{
            "task_id": "unique_id",
            "description": "what needs to be done",
            "acceptance_criteria": ["criterion 1", "criterion 2"],
            "dependencies": ["task_id_if_any"]
        }}
    ]
}}
"""

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=prompt),
        ]

        # Invoke with callbacks if provided
        if callbacks:
            response = self.llm.invoke(messages, config={"callbacks": callbacks})
        else:
            response = self.llm.invoke(messages)

        result = self._parse_json_response(self._extract_string_content(response.content))

        task = Task(
            task_id=f"task_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
            goal=result.get("goal", objective),
            subtasks=[
                SubTask(
                    task_id=st["task_id"],
                    description=st["description"],
                    acceptance_criteria=st.get("acceptance_criteria", []),
                    dependencies=st.get("dependencies", []),
                )
                for st in result.get("subtasks", [])
            ],
        )

        self.tasks[task.task_id] = task
        return task

    def assign_subtask(self, task_id: str, subtask_id: str, agent_name: str) -> None:
        """
        Assign a subtask to an agent.

        Args:
            task_id: Parent task ID
            subtask_id: Subtask ID to assign
            agent_name: Name of the agent to assign to
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        task = self.tasks[task_id]
        for subtask in task.subtasks:
            if subtask.task_id == subtask_id:
                subtask.assigned_to = agent_name
                subtask.status = TaskStatus.PENDING
                task.last_updated = datetime.now(UTC)
                break

    def update_subtask_status(
        self,
        task_id: str,
        subtask_id: str,
        status: TaskStatus,
        result: str | None = None,
    ) -> None:
        """
        Update the status of a subtask.

        Args:
            task_id: Parent task ID
            subtask_id: Subtask ID to update
            status: New status
            result: Optional result/output from the subtask
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        task = self.tasks[task_id]
        for subtask in task.subtasks:
            if subtask.task_id == subtask_id:
                subtask.status = status
                if result:
                    subtask.result = result
                task.last_updated = datetime.now(UTC)
                break

    def review_agent_output(
        self,
        task_id: str,
        subtask_id: str,
        agent_response: AgentResponse,
    ) -> dict[str, Any]:
        """
        Review an agent's output for a subtask.

        Args:
            task_id: Parent task ID
            subtask_id: Subtask ID
            agent_response: The agent's response to review

        Returns:
            Review result with feedback and approval status
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        task = self.tasks[task_id]
        subtask = next((st for st in task.subtasks if st.task_id == subtask_id), None)

        if not subtask:
            raise ValueError(f"Subtask {subtask_id} not found in task {task_id}")

        prompt = f"""
Review this agent output for the assigned subtask:

SUBTASK: {subtask.description}

ACCEPTANCE CRITERIA:
{chr(10).join(f"- {criterion}" for criterion in subtask.acceptance_criteria)}

AGENT OUTPUT:
{agent_response.content}

Evaluate:
1. Does the output meet all acceptance criteria?
2. Is the output on-task or has the agent deviated?
3. What is the quality level (high/medium/low)?
4. Any issues or required revisions?

Respond in JSON format:
{{
    "approved": true/false,
    "quality": "high/medium/low",
    "feedback": "constructive feedback",
    "missing_criteria": ["list of unmet criteria"],
    "redirect_needed": true/false,
    "redirect_prompt": "specific guidance if redirect needed"
}}
"""

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=prompt),
        ]

        response = self.llm.invoke(messages)
        return self._parse_json_response(self._extract_string_content(response.content))

    def get_task_status(self, task_id: str) -> dict[str, Any]:
        """
        Get the current status of a task in JSON format.

        Args:
            task_id: Task ID

        Returns:
            Task status as a dictionary
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        task = self.tasks[task_id]
        return {
            "task_id": task.task_id,
            "goal": task.goal,
            "created_at": task.created_at.isoformat(),
            "last_updated": task.last_updated.isoformat(),
            "subtasks": [
                {
                    "task_id": st.task_id,
                    "description": st.description,
                    "assigned_to": st.assigned_to,
                    "status": st.status.value,
                    "acceptance_criteria": st.acceptance_criteria,
                    "dependencies": st.dependencies,
                    "result": st.result,
                }
                for st in task.subtasks
            ],
        }

    def request_interviewer_evaluation(
        self,
        task_description: str,
        candidates: list[str],
    ) -> dict[str, Any]:
        """
        Request the Interviewer agent to evaluate candidates.

        Args:
            task_description: Description of the task requiring evaluation
            candidates: List of candidate agent names

        Returns:
            Interview request details
        """
        return {
            "action": "interview_request",
            "task_description": task_description,
            "candidates": candidates,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def _extract_string_content(self, content: str | list[str | dict[str, Any]]) -> str:
        """Extract string content from LLM response."""
        if isinstance(content, str):
            return content
        # For list content, join text parts and ignore dict parts
        text_parts = [item for item in content if isinstance(item, str)]
        return "".join(text_parts) if text_parts else ""

    def _parse_json_response(self, content: str) -> dict[str, Any]:
        """Parse JSON from LLM response, handling markdown code blocks."""
        content = content.strip()

        # Remove markdown code blocks if present
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            # If parsing fails, try to extract JSON object
            import re

            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"Failed to parse JSON response: {e}") from e

    def synthesize_results(self, task_id: str) -> str:
        """
        Synthesize all subtask results into a final output.

        Args:
            task_id: Task ID

        Returns:
            Synthesized final output
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        task = self.tasks[task_id]
        completed_subtasks = [st for st in task.subtasks if st.status == TaskStatus.COMPLETED]

        if not completed_subtasks:
            return "No completed subtasks to synthesize."

        prompt = f"""
Goal: {task.goal}

Completed Subtasks and Results:
{chr(10).join(f"- {st.description}: {st.result}" for st in completed_subtasks)}

Synthesize these results into a coherent final output that fulfills the original goal.
Provide a clear, complete response that integrates all the subtask results.
"""

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=prompt),
        ]

        response = self.llm.invoke(messages)
        return self._extract_string_content(response.content)

"""
LangGraph-based Supervisor Agent implementation.

This module provides a LangGraph StateGraph version of the SupervisorAgent
with built-in state persistence, checkpointing, and human-in-the-loop support.
"""

from datetime import datetime, timezone
from typing import Literal, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from .config import SUPERVISOR_PROMPT, FrameworkConfig
from .graph_base import get_checkpointer
from .llm import create_llm
from .models import SubTask, Task, TaskStatus
from .supervisor import SupervisorAgent  # For JSON parsing utility


class SupervisorState(TypedDict):
    """State schema for SupervisorGraph."""

    # Input
    objective: str
    thread_id: str | None

    # Task decomposition
    task_id: str | None
    task: dict | None  # Serialized Task

    # Subtask execution
    current_subtask_id: str | None
    current_subtask: dict | None  # Serialized SubTask
    agent_name: str | None
    agent_response: dict | None  # Serialized AgentResponse

    # Review
    review_result: dict | None

    # Final output
    completed_subtasks: list[dict]
    final_output: str | None

    # Control flow
    next_action: Literal["assign", "execute", "review", "synthesize", "end"] | None


class SupervisorGraph:
    """
    LangGraph-based supervisor agent with state persistence.

    Provides the same functionality as SupervisorAgent but with:
    - SQLite checkpointing for crash recovery
    - Human-in-the-loop support via interrupt()
    - Streaming support
    - Better observability

    Example:
        >>> from tessera.supervisor_graph import SupervisorGraph
        >>> from tessera.graph_base import get_thread_config
        >>>
        >>> supervisor = SupervisorGraph()
        >>> config = get_thread_config("project-123")
        >>>
        >>> # Decompose task
        >>> result = supervisor.invoke({
        >>>     "objective": "Build a website",
        >>>     "next_action": "decompose"
        >>> }, config=config)
        >>>
        >>> # Resume from checkpoint
        >>> result = supervisor.invoke(None, config=config)
    """

    def __init__(
        self,
        llm: BaseChatModel | None = None,
        config: FrameworkConfig | None = None,
        system_prompt: str = SUPERVISOR_PROMPT,
    ) -> None:
        """
        Initialize the supervisor graph.

        Args:
            llm: Language model to use (creates default if None)
            config: Framework configuration
            system_prompt: Custom system prompt
        """
        self.config = config or FrameworkConfig.from_env()
        self.llm = llm or create_llm(self.config.llm)
        self.system_prompt = system_prompt

        # Build the graph
        self.app = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph StateGraph."""
        # Create graph
        workflow = StateGraph(SupervisorState)

        # Add nodes
        workflow.add_node("decompose", self._decompose_node)
        workflow.add_node("assign", self._assign_node)
        workflow.add_node("execute", self._execute_node)
        workflow.add_node("review", self._review_node)
        workflow.add_node("synthesize", self._synthesize_node)

        # Set entry point
        workflow.set_entry_point("decompose")

        # Add edges with routing
        workflow.add_conditional_edges(
            "decompose",
            self._route_after_decompose,
            {
                "assign": "assign",
                "end": END,
            },
        )

        workflow.add_conditional_edges(
            "assign",
            self._route_after_assign,
            {
                "execute": "execute",
                "synthesize": "synthesize",
                "end": END,
            },
        )

        workflow.add_conditional_edges(
            "execute",
            self._route_after_execute,
            {
                "review": "review",
                "end": END,
            },
        )

        workflow.add_conditional_edges(
            "review",
            self._route_after_review,
            {
                "assign": "assign",
                "execute": "execute",
                "synthesize": "synthesize",
                "end": END,
            },
        )

        workflow.add_edge("synthesize", END)

        # Compile with checkpointer
        checkpointer = get_checkpointer()
        return workflow.compile(checkpointer=checkpointer)

    def _decompose_node(self, state: SupervisorState) -> SupervisorState:
        """Decompose objective into subtasks."""
        objective = state["objective"]

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

        response = self.llm.invoke(messages)
        result = SupervisorAgent._parse_json_response(None, response.content)

        # Create task with microseconds for uniqueness
        task_id = f"task_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
        task = Task(
            task_id=task_id,
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

        return {
            **state,
            "task_id": task_id,
            "task": task.model_dump(),
            "completed_subtasks": [],
            "next_action": "assign",
        }

    def _assign_node(self, state: SupervisorState) -> SupervisorState:
        """Assign next available subtask."""
        task_dict = state["task"]
        if not task_dict:
            return {**state, "next_action": "end"}

        # Find next unassigned subtask
        for subtask_dict in task_dict["subtasks"]:
            if subtask_dict.get("status") == TaskStatus.PENDING.value:
                # Check dependencies
                dependencies = subtask_dict.get("dependencies", [])
                completed = [st["task_id"] for st in state.get("completed_subtasks", [])]

                if all(dep in completed for dep in dependencies):
                    # Assign this subtask
                    subtask_dict["status"] = TaskStatus.IN_PROGRESS.value
                    subtask_dict["assigned_to"] = "default_agent"

                    return {
                        **state,
                        "task": task_dict,  # Return updated task dict
                        "current_subtask_id": subtask_dict["task_id"],
                        "current_subtask": subtask_dict,
                        "agent_name": "default_agent",
                        "next_action": "execute",
                    }

        # No more subtasks to assign - synthesize
        return {**state, "next_action": "synthesize"}

    def _execute_node(self, state: SupervisorState) -> SupervisorState:
        """Execute the current subtask (simulated)."""
        subtask = state["current_subtask"]
        if not subtask:
            return {**state, "next_action": "end"}

        # In a real implementation, this would invoke the actual agent
        # For now, simulate execution
        result = f"Completed: {subtask['description']}"

        agent_response = {
            "agent_name": state["agent_name"],
            "content": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return {
            **state,
            "agent_response": agent_response,
            "next_action": "review",
        }

    def _review_node(self, state: SupervisorState) -> SupervisorState:
        """Review agent output."""
        subtask = state["current_subtask"]
        agent_response = state["agent_response"]

        if not subtask or not agent_response:
            return {**state, "next_action": "end"}

        prompt = f"""
Review this agent output for the assigned subtask:

SUBTASK: {subtask["description"]}

ACCEPTANCE CRITERIA:
{chr(10).join(f"- {criterion}" for criterion in subtask.get("acceptance_criteria", []))}

AGENT OUTPUT:
{agent_response["content"]}

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
        review = SupervisorAgent._parse_json_response(None, response.content)

        # Update subtask status
        if review.get("approved", False):
            subtask["status"] = TaskStatus.COMPLETED.value
            subtask["result"] = agent_response["content"]

            # Add to completed list
            completed = state.get("completed_subtasks", [])
            completed.append(subtask)

            # Update task subtasks
            task_dict = state["task"]
            for st in task_dict["subtasks"]:
                if st["task_id"] == subtask["task_id"]:
                    st.update(subtask)
                    break

            return {
                **state,
                "review_result": review,
                "completed_subtasks": completed,
                "task": task_dict,
                "next_action": "assign",
            }
        # Need revision
        return {
            **state,
            "review_result": review,
            "next_action": "execute",
        }

    def _synthesize_node(self, state: SupervisorState) -> SupervisorState:
        """Synthesize all subtask results."""
        task_dict = state["task"]
        completed = state.get("completed_subtasks", [])

        if not completed:
            return {
                **state,
                "final_output": "No completed subtasks to synthesize.",
                "next_action": "end",
            }

        prompt = f"""
Goal: {task_dict["goal"]}

Completed Subtasks and Results:
{chr(10).join(f"- {st['description']}: {st.get('result', 'N/A')}" for st in completed)}

Synthesize these results into a coherent final output that fulfills the original goal.
Provide a clear, complete response that integrates all the subtask results.
"""

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=prompt),
        ]

        response = self.llm.invoke(messages)

        return {
            **state,
            "final_output": response.content,
            "next_action": "end",
        }

    def _route_after_decompose(self, state: SupervisorState) -> Literal["assign", "end"]:
        """Route after decomposition."""
        task = state.get("task")
        if task and task.get("subtasks"):
            return "assign"
        return "end"

    def _route_after_assign(
        self, state: SupervisorState
    ) -> Literal["execute", "synthesize", "end"]:
        """Route after assignment."""
        next_action = state.get("next_action", "end")
        if next_action == "execute":
            return "execute"
        if next_action == "synthesize":
            return "synthesize"
        return "end"

    def _route_after_execute(self, state: SupervisorState) -> Literal["review", "end"]:
        """Route after execution."""
        if state.get("agent_response"):
            return "review"
        return "end"

    def _route_after_review(
        self, state: SupervisorState
    ) -> Literal["assign", "execute", "synthesize", "end"]:
        """Route after review."""
        next_action = state.get("next_action", "end")
        if next_action in ["assign", "execute", "synthesize"]:
            return next_action
        return "end"

    def invoke(self, input_data: dict | None, config: dict | None = None) -> dict:
        """
        Invoke the supervisor graph.

        Args:
            input_data: Input state (or None to resume from checkpoint)
            config: Configuration including thread_id for checkpointing

        Returns:
            Final state after execution

        Example:
            >>> supervisor = SupervisorGraph()
            >>> config = get_thread_config("project-123")
            >>> result = supervisor.invoke({
            >>>     "objective": "Build a website"
            >>> }, config=config)
        """
        return self.app.invoke(input_data, config=config)

    def stream(self, input_data: dict, config: dict | None = None) -> object:
        """
        Stream supervisor graph execution.

        Args:
            input_data: Input state
            config: Configuration including thread_id

        Yields:
            State updates as they occur

        Example:
            >>> supervisor = SupervisorGraph()
            >>> for state in supervisor.stream({"objective": "..."}):
            >>>     print(state)
        """
        return self.app.stream(input_data, config=config)

    def get_state(self, config: dict) -> dict:
        """
        Get current state from checkpoint.

        Args:
            config: Configuration with thread_id

        Returns:
            Current state
        """
        return self.app.get_state(config)

    def update_state(self, config: dict, values: dict) -> dict:
        """
        Update state at checkpoint.

        Args:
            config: Configuration with thread_id
            values: Values to update

        Returns:
            Updated state
        """
        return self.app.update_state(config, values)

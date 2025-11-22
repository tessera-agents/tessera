"""
Agent pool management for multi-agent execution.
"""

from dataclasses import dataclass

from ..config.schema import AgentDefinition


@dataclass
class AgentInstance:
    """Runtime agent instance."""

    name: str
    agent: any  # SupervisorAgent, InterviewerAgent, etc.
    config: AgentDefinition
    current_task: str | None = None  # Currently assigned task ID
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_cost: float = 0.0


class AgentPool:
    """
    Manages pool of agent instances.

    Responsibilities:
    - Load agents from configuration
    - Match tasks to agents based on capabilities
    - Track agent availability and performance
    - Select best agent for each task
    """

    def __init__(self, agent_configs: list[AgentDefinition]) -> None:
        """
        Initialize agent pool.

        Args:
            agent_configs: List of agent configurations
        """
        self.agents: dict[str, AgentInstance] = {}
        self._load_agents(agent_configs)

    def _load_agents(self, configs: list[AgentDefinition]) -> None:
        """
        Load agents from configurations.

        For v0.2, we'll create placeholder agents. v0.3 will instantiate real agents.

        Args:
            configs: Agent configuration list
        """
        for config in configs:
            # For v0.2, store config only
            # v0.3 will actually instantiate the agent classes
            self.agents[config.name] = AgentInstance(
                name=config.name,
                agent=None,  # Will instantiate in v0.3
                config=config,
            )

    def get_agent(self, name: str) -> AgentInstance | None:
        """
        Get agent by name.

        Args:
            name: Agent name

        Returns:
            AgentInstance or None
        """
        return self.agents.get(name)

    def get_available_agents(self) -> list[AgentInstance]:
        """
        Get agents that are not currently assigned to a task.

        Returns:
            List of available agents
        """
        return [agent for agent in self.agents.values() if agent.current_task is None]

    def assign_task_to_agent(self, task_id: str, agent_name: str) -> AgentInstance | None:
        """
        Assign task to specific agent.

        Args:
            task_id: Task identifier
            agent_name: Agent name

        Returns:
            AgentInstance if assignment successful, None otherwise
        """
        agent = self.agents.get(agent_name)
        if agent and agent.current_task is None:
            agent.current_task = task_id
            return agent
        return None

    def find_best_agent(
        self, capabilities_needed: list[str], phase: str | None = None
    ) -> str | None:
        """
        Find best agent for task based on capabilities and phase affinity.

        Args:
            capabilities_needed: List of required capabilities
            phase: Optional current workflow phase

        Returns:
            Agent name or None if no match found
        """
        scored_agents = []

        for agent in self.get_available_agents():
            score = 0

            # Match capabilities
            matching_capabilities = set(capabilities_needed) & set(agent.config.capabilities)
            score += len(matching_capabilities) * 10

            # Match phase affinity
            if phase and phase in agent.config.phase_affinity:
                score += 5

            # Performance bonus (success rate)
            if agent.tasks_completed + agent.tasks_failed > 0:
                success_rate = agent.tasks_completed / (agent.tasks_completed + agent.tasks_failed)
                score += success_rate * 3

            if score > 0:
                scored_agents.append((score, agent.name))

        if scored_agents:
            # Sort by score (highest first)
            scored_agents.sort(reverse=True)
            return scored_agents[0][1]

        # Fallback: return first available agent
        available = self.get_available_agents()
        return available[0].name if available else None

    def mark_task_complete(self, agent_name: str, success: bool = True) -> None:
        """
        Mark agent's current task as complete.

        Args:
            agent_name: Agent name
            success: Whether task succeeded
        """
        agent = self.agents.get(agent_name)
        if agent:
            agent.current_task = None
            if success:
                agent.tasks_completed += 1
            else:
                agent.tasks_failed += 1

    def get_pool_status(self) -> dict:
        """
        Get pool status summary.

        Returns:
            Dict with pool statistics
        """
        return {
            "total_agents": len(self.agents),
            "available_agents": len(self.get_available_agents()),
            "busy_agents": sum(1 for a in self.agents.values() if a.current_task),
            "total_tasks_completed": sum(a.tasks_completed for a in self.agents.values()),
            "total_tasks_failed": sum(a.tasks_failed for a in self.agents.values()),
        }

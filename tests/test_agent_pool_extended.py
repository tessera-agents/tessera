"""Extended tests for agent pool functionality."""

from unittest.mock import Mock

import pytest

from tessera.config.schema import AgentDefinition
from tessera.workflow.agent_pool import AgentInstance, AgentPool


@pytest.mark.unit
class TestAgentPoolExtended:
    """Extended agent pool tests for coverage."""

    def test_agent_instance_creation(self):
        """Test creating agent instances."""
        config = AgentDefinition(
            name="test-agent",
            model="gpt-4",
            capabilities=["python"],
        )
        mock_agent = Mock()

        instance = AgentInstance(
            name="test-agent",
            agent=mock_agent,
            config=config,
        )

        assert instance.name == "test-agent"
        assert instance.agent == mock_agent
        assert instance.config == config
        assert instance.current_task is None
        assert instance.tasks_completed == 0
        assert instance.tasks_failed == 0

    def test_get_available_agents(self):
        """Test getting available agents."""
        configs = [
            AgentDefinition(name="agent1", model="gpt-4", capabilities=["python"]),
            AgentDefinition(name="agent2", model="gpt-4", capabilities=["testing"]),
        ]

        pool = AgentPool(configs)

        available = pool.get_available_agents()

        # All agents available initially
        assert len(available) == 2
        assert any(a.name == "agent1" for a in available)
        assert any(a.name == "agent2" for a in available)

    def test_assign_task(self):
        """Test assigning task to agent."""
        configs = [AgentDefinition(name="agent1", model="gpt-4", capabilities=["python"])]

        pool = AgentPool(configs)
        result = pool.assign_task_to_agent("task123", "agent1")

        assert result is not None
        assert result.current_task == "task123"

        # Agent should not be available
        available = pool.get_available_agents()
        assert all(a.name != "agent1" for a in available)

    def test_mark_task_complete_success(self):
        """Test marking task complete successfully."""
        configs = [AgentDefinition(name="agent1", model="gpt-4", capabilities=["python"])]

        pool = AgentPool(configs)
        pool.assign_task_to_agent("task123", "agent1")
        pool.mark_task_complete("agent1", success=True)

        agent = pool.agents["agent1"]
        assert agent.current_task is None  # Released
        assert agent.tasks_completed == 1
        assert agent.tasks_failed == 0

    def test_mark_task_complete_failure(self):
        """Test marking task failed."""
        configs = [AgentDefinition(name="agent1", model="gpt-4", capabilities=["python"])]

        pool = AgentPool(configs)
        pool.assign_task_to_agent("task123", "agent1")
        pool.mark_task_complete("agent1", success=False)

        agent = pool.agents["agent1"]
        assert agent.current_task is None
        assert agent.tasks_completed == 0
        assert agent.tasks_failed == 1

    def test_get_pool_status(self):
        """Test getting pool status summary."""
        configs = [
            AgentDefinition(name="agent1", model="gpt-4", capabilities=["python"]),
            AgentDefinition(name="agent2", model="gpt-4", capabilities=["testing"]),
        ]

        pool = AgentPool(configs)

        # Assign one task
        pool.assign_task_to_agent("task1", "agent1")

        status = pool.get_pool_status()

        assert status["total_agents"] == 2
        assert status["available_agents"] == 1
        assert status["busy_agents"] == 1

    def test_find_best_agent(self):
        """Test finding best agent for capabilities."""
        configs = [
            AgentDefinition(name="python-expert", model="gpt-4", capabilities=["python", "testing"]),
            AgentDefinition(name="docs-writer", model="gpt-4", capabilities=["documentation"]),
        ]

        pool = AgentPool(configs)

        # Find agent for python task
        best = pool.find_best_agent(["python"], phase="implementation")

        assert best == "python-expert"

    def test_find_best_agent_with_performance(self):
        """Test agent selection considers performance."""
        configs = [
            AgentDefinition(name="agent1", model="gpt-4", capabilities=["python"]),
            AgentDefinition(name="agent2", model="gpt-4", capabilities=["python"]),
        ]

        pool = AgentPool(configs)

        # Give agent1 better track record
        pool.assign_task_to_agent("task1", "agent1")
        pool.mark_task_complete("agent1", success=True)

        # agent1 should be preferred due to success history
        best = pool.find_best_agent(["python"])

        assert best == "agent1"

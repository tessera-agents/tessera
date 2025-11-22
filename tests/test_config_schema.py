"""
Tests for configuration schema.
"""

import pytest
from pydantic import ValidationError

from tessera.config.schema import (
    AgentDefinition,
    AgentDefaultsConfig,
    ToolsGlobalConfig,
    CostLimitConfig,
    WorkflowPhase,
)


@pytest.mark.unit
class TestAgentDefinition:
    """Test agent definition model."""

    def test_minimal_agent(self):
        """Test minimal agent definition."""
        agent = AgentDefinition(
            name="test-agent",
            model="gpt-4",
            provider="openai"
        )

        assert agent.name == "test-agent"
        assert agent.model == "gpt-4"
        assert agent.provider == "openai"
        assert agent.capabilities == []

    def test_agent_with_capabilities(self):
        """Test agent with capabilities."""
        agent = AgentDefinition(
            name="python-expert",
            model="gpt-4",
            provider="openai",
            capabilities=["python", "testing"],
            phase_affinity=["implementation"]
        )

        assert "python" in agent.capabilities
        assert "implementation" in agent.phase_affinity

    def test_agent_temperature_validation(self):
        """Test temperature is validated."""
        # Valid temperature
        agent = AgentDefinition(
            name="agent",
            model="gpt-4",
            provider="openai",
            temperature=0.7
        )
        assert agent.temperature == 0.7

        # Invalid temperature should raise
        with pytest.raises(ValidationError):
            AgentDefinition(
                name="agent",
                model="gpt-4",
                provider="openai",
                temperature=3.0  # > 2.0
            )


@pytest.mark.unit
class TestAgentDefaults:
    """Test agent defaults configuration."""

    def test_default_values(self):
        """Test default agent configuration values."""
        defaults = AgentDefaultsConfig()

        assert defaults.temperature == 0.7
        assert defaults.timeout == 90
        assert defaults.max_retries == 3
        assert defaults.context_size == 8192


@pytest.mark.unit
class TestToolsGlobalConfig:
    """Test tools global configuration."""

    def test_tools_config_defaults(self):
        """Test default tools configuration."""
        config = ToolsGlobalConfig()

        assert config.strategy == "risk-based"
        assert config.max_risk_level == "high"
        assert config.allow == []
        assert config.deny == []


@pytest.mark.unit
class TestCostLimitConfig:
    """Test cost limit configuration."""

    def test_cost_limits(self):
        """Test cost limit configuration."""
        config = CostLimitConfig(
            daily_usd=10.0,
            max_usd=5.0,
            enforcement="hard"
        )

        assert config.daily_usd == 10.0
        assert config.max_usd == 5.0
        assert config.enforcement == "hard"

    def test_soft_enforcement_default(self):
        """Test soft enforcement is default."""
        config = CostLimitConfig()

        assert config.enforcement == "soft"


@pytest.mark.unit
class TestWorkflowPhase:
    """Test workflow phase configuration."""

    def test_minimal_phase(self):
        """Test minimal phase definition."""
        phase = WorkflowPhase(name="test-phase")

        assert phase.name == "test-phase"
        assert phase.required is True
        assert phase.typical_tasks == []
        assert phase.sub_phases == []

    def test_phase_with_dependencies(self):
        """Test phase with dependencies."""
        phase = WorkflowPhase(
            name="execution",
            depends_on=["architecture", "research"]
        )

        assert "architecture" in phase.depends_on
        assert "research" in phase.depends_on

    def test_phase_complexity_filtering(self):
        """Test phase complexity requirements."""
        simple_phase = WorkflowPhase(
            name="simple-only",
            required_for_complexity=["simple"]
        )

        complex_phase = WorkflowPhase(
            name="complex-only",
            required_for_complexity=["complex"]
        )

        assert "simple" in simple_phase.required_for_complexity
        assert "complex" not in simple_phase.required_for_complexity

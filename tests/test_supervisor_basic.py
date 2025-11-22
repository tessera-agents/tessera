"""
Basic tests for supervisor agent (avoiding complex LLM mocking).
"""

import pytest
from unittest.mock import Mock, MagicMock
from langchain_core.messages import AIMessage

from tessera.supervisor import SupervisorAgent
from tessera.legacy_config import LLMConfig, FrameworkConfig
from tessera.models import Task, SubTask


@pytest.mark.unit
class TestSupervisorBasic:
    """Basic supervisor tests."""

    def test_supervisor_initialization(self):
        """Test supervisor can be initialized."""
        mock_llm = Mock()
        mock_llm.invoke = Mock(return_value=AIMessage(content='{"result": "test"}'))

        supervisor = SupervisorAgent(llm=mock_llm)

        assert supervisor.llm == mock_llm
        assert supervisor.tasks == {}

    def test_supervisor_with_custom_prompt(self):
        """Test supervisor with custom system prompt."""
        mock_llm = Mock()
        custom_prompt = "You are a custom supervisor"

        supervisor = SupervisorAgent(llm=mock_llm, system_prompt=custom_prompt)

        assert supervisor.system_prompt == custom_prompt

    def test_supervisor_stores_config(self):
        """Test supervisor stores framework config."""
        mock_llm = Mock()
        config = FrameworkConfig(
            llm=LLMConfig(provider="openai", models=["gpt-4"], api_key="test")
        )

        supervisor = SupervisorAgent(llm=mock_llm, config=config)

        assert supervisor.config == config
        assert supervisor.config.llm.provider == "openai"

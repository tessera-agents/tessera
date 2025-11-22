"""Unit tests for PanelGraph (LangGraph version)."""

import pytest

from tessera.graph_base import clear_checkpoint_db, get_thread_config
from tessera.panel_graph import PanelGraph


@pytest.mark.unit
class TestPanelGraph:
    """Test PanelGraph functionality."""

    def setup_method(self):
        """Clean up checkpoints before each test."""
        clear_checkpoint_db()

    def teardown_method(self):
        """Clean up checkpoints after each test."""
        clear_checkpoint_db()

    def test_panel_graph_initialization(self, test_config):
        """Test panel graph initialization."""
        panel = PanelGraph(config=test_config)

        assert panel.config == test_config
        assert panel.app is not None

    def test_panel_evaluation_via_graph(self, test_config):
        """Test full panel evaluation through LangGraph."""
        panel = PanelGraph(config=test_config)

        config = get_thread_config("test-panel")
        result = panel.invoke(
            {
                "task_description": "Build a caching system",
                "candidates": ["candidate_a", "candidate_b"],
            },
            config=config,
        )

        assert result["panelists"] is not None
        assert len(result["panelists"]) >= 3
        assert result["ballots"] is not None
        assert result["winner"] is not None
        assert result["decision"] is not None

    def test_graph_state_persistence(self, test_config):
        """Test that state is persisted to checkpoint."""
        panel = PanelGraph(config=test_config)

        thread_id = "test-persist"
        config = get_thread_config(thread_id)

        # Run panel evaluation
        result = panel.invoke(
            {
                "task_description": "Build system",
                "candidates": ["a", "b"],
            },
            config=config,
        )

        assert result["winner"] is not None

        # Get state from checkpoint
        state = panel.get_state(config)
        assert state.values["winner"] is not None

    def test_panel_graph_streaming(self, test_config):
        """Test streaming graph execution."""
        panel = PanelGraph(config=test_config)

        config = get_thread_config("test-stream")

        states = list(
            panel.stream(
                {
                    "task_description": "Build system",
                    "candidates": ["a", "b"],
                },
                config=config,
            )
        )

        # Should have multiple state updates
        assert len(states) > 0

        # Extract all states
        all_states = []
        for state_update in states:
            for state_data in state_update.values():
                if isinstance(state_data, dict):
                    all_states.append(state_data)

        assert any("panelists" in s for s in all_states)

    def test_setup_panel_node_creates_panelists(self, test_config):
        """Test setup panel node creates proper panelist structure."""
        panel = PanelGraph(config=test_config)

        state = {
            "task_description": "Build a system",
            "candidates": ["a", "b"],
            "thread_id": None,
            "num_panelists": None,
            "panelists": None,
            "question_bank": None,
            "qa_transcript": None,
            "ballots": None,
            "vote_counts": None,
            "winner": None,
            "tie_detected": None,
            "tie_breaker_result": None,
            "final_ranking": None,
            "decision": None,
            "next_action": None,
        }

        result = panel._setup_panel_node(state)

        assert result["panelists"] is not None
        assert len(result["panelists"]) >= 3
        assert result["num_panelists"] % 2 == 1  # Should be odd
        assert result["next_action"] == "qa"

    def test_generate_questions_node_creates_questions(self, test_config):
        """Test generate questions node."""
        panel = PanelGraph(config=test_config)

        state = {
            "task_description": "Build a caching system",
            "candidates": ["a", "b"],
            "thread_id": None,
            "num_panelists": 3,
            "panelists": [{"name": "tech"}, {"name": "creative"}, {"name": "risk"}],
            "question_bank": None,
            "qa_transcript": None,
            "ballots": None,
            "vote_counts": None,
            "winner": None,
            "tie_detected": None,
            "tie_breaker_result": None,
            "final_ranking": None,
            "decision": None,
            "next_action": None,
        }

        result = panel._generate_questions_node(state)

        assert result["question_bank"] is not None
        assert len(result["question_bank"]) > 0
        assert result["next_action"] == "vote"

    def test_conduct_voting_node_generates_ballots(self, test_config):
        """Test conduct voting node generates ballots."""
        panel = PanelGraph(config=test_config)

        state = {
            "task_description": "Build system",
            "candidates": ["candidate_a", "candidate_b"],
            "thread_id": None,
            "num_panelists": 3,
            "panelists": [
                {"name": "tech", "prompt": "test"},
                {"name": "creative", "prompt": "test"},
                {"name": "risk", "prompt": "test"},
            ],
            "question_bank": [{"id": "Q1", "text": "Test?"}],
            "qa_transcript": None,
            "ballots": None,
            "vote_counts": None,
            "winner": None,
            "tie_detected": None,
            "tie_breaker_result": None,
            "final_ranking": None,
            "decision": None,
            "next_action": None,
        }

        result = panel._conduct_voting_node(state)

        assert result["ballots"] is not None
        assert len(result["ballots"]) == 3  # One per panelist
        assert result["vote_counts"] is not None
        assert result["next_action"] == "tiebreak"

    def test_check_tie_node_detects_winner(self, test_config):
        """Test check tie node finds winner."""
        panel = PanelGraph(config=test_config)

        state = {
            "task_description": "Build system",
            "candidates": ["a", "b"],
            "thread_id": None,
            "num_panelists": 3,
            "panelists": [{"name": "p1"}, {"name": "p2"}, {"name": "p3"}],
            "question_bank": [],
            "qa_transcript": None,
            "ballots": [],
            "vote_counts": {"a": 2, "b": 1},
            "winner": None,
            "tie_detected": None,
            "tie_breaker_result": None,
            "final_ranking": None,
            "decision": None,
            "next_action": None,
        }

        result = panel._check_tie_node(state)

        assert result["winner"] == "a"
        assert result["tie_detected"] is False
        assert result["next_action"] == "finalize"

    def test_check_tie_node_handles_tie(self, test_config):
        """Test check tie node handles tie situation."""
        panel = PanelGraph(config=test_config)

        state = {
            "task_description": "Build system",
            "candidates": ["a", "b"],
            "thread_id": None,
            "num_panelists": 2,
            "panelists": [{"name": "p1"}, {"name": "p2"}],
            "question_bank": [],
            "qa_transcript": None,
            "ballots": [],
            "vote_counts": {"a": 1, "b": 1},  # Tie
            "winner": None,
            "tie_detected": None,
            "tie_breaker_result": None,
            "final_ranking": None,
            "decision": None,
            "next_action": None,
        }

        result = panel._check_tie_node(state)

        assert result["winner"] is not None  # Should pick one
        assert result["tie_detected"] is True
        assert result["tie_breaker_result"] is not None

    def test_finalize_node_creates_ranking(self, test_config):
        """Test finalize node creates final ranking."""
        panel = PanelGraph(config=test_config)

        state = {
            "task_description": "Build system",
            "candidates": ["a", "b", "c"],
            "thread_id": None,
            "num_panelists": 5,
            "panelists": [],
            "question_bank": [],
            "qa_transcript": None,
            "ballots": [],
            "vote_counts": {"a": 3, "b": 1, "c": 1},
            "winner": "a",
            "tie_detected": False,
            "tie_breaker_result": None,
            "final_ranking": None,
            "decision": None,
            "next_action": None,
        }

        result = panel._finalize_node(state)

        assert result["final_ranking"] is not None
        assert len(result["final_ranking"]) == 3
        assert result["final_ranking"][0][0] == "a"  # First place
        assert result["decision"] is not None
        assert "a" in result["decision"]

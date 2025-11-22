"""Integration tests for end-to-end workflows."""

import pytest
from tessera import SupervisorAgent, InterviewerAgent, PanelSystem
from tessera.models import AgentResponse, TaskStatus


@pytest.mark.integration
class TestSupervisorInterviewerIntegration:
    """Test integration between Supervisor and Interviewer."""

    def test_supervisor_requests_interviewer_evaluation(
        self,
        mock_llm_with_response,
        test_config,
        sample_task_decomposition,
        sample_questions,
        sample_score_response,
        sample_recommendation_response,
        sample_comparison_response,
    ):
        """Test full workflow of supervisor requesting interviewer evaluation."""
        # Create supervisor
        supervisor_llm = mock_llm_with_response(sample_task_decomposition)
        supervisor = SupervisorAgent(llm=supervisor_llm, config=test_config)

        # Decompose task
        task = supervisor.decompose_task("Build a complex system")
        assert len(task.subtasks) > 0

        # Request interviewer evaluation
        interview_request = supervisor.request_interviewer_evaluation(
            task_description=task.subtasks[0].description,
            candidates=["agent_1", "agent_2"],
        )

        assert interview_request["action"] == "interview_request"
        assert len(interview_request["candidates"]) == 2

        # Create interviewer and evaluate
        interviewer_llm = mock_llm_with_response(sample_score_response)
        interviewer = InterviewerAgent(llm=interviewer_llm, config=test_config)

        # Design questions
        questions_llm = mock_llm_with_response(
            '{"questions": ' + str(sample_questions).replace("'", '"') + '}'
        )
        interviewer.llm = questions_llm
        questions = interviewer.design_interview(
            interview_request["task_description"]
        )

        assert len(questions) > 0


@pytest.mark.integration
class TestEndToEndTaskWorkflow:
    """Test complete task workflow."""

    def test_complete_task_lifecycle(
        self,
        mock_llm_with_response,
        test_config,
        sample_task_decomposition,
        sample_review_response,
    ):
        """Test complete lifecycle: decompose, assign, execute, review, complete."""
        # Initialize supervisor
        decomp_llm = mock_llm_with_response(sample_task_decomposition)
        supervisor = SupervisorAgent(llm=decomp_llm, config=test_config)

        # Step 1: Decompose task
        task = supervisor.decompose_task("Build a web scraping system")
        assert len(task.subtasks) == 2

        # Step 2: Assign subtasks
        for subtask in task.subtasks:
            supervisor.assign_subtask(
                task.task_id,
                subtask.task_id,
                f"agent_{subtask.task_id}",
            )
            assert subtask.assigned_to == f"agent_{subtask.task_id}"

        # Step 3: Simulate agent execution
        first_subtask = task.subtasks[0]
        response = AgentResponse(
            agent_name=first_subtask.assigned_to,
            task_id=first_subtask.task_id,
            content="Implemented scraper architecture",
        )

        # Step 4: Review output
        review_llm = mock_llm_with_response(sample_review_response)
        supervisor.llm = review_llm

        review = supervisor.review_agent_output(
            task.task_id,
            first_subtask.task_id,
            response,
        )

        assert review["approved"] is True

        # Step 5: Mark as completed
        supervisor.update_subtask_status(
            task.task_id,
            first_subtask.task_id,
            TaskStatus.COMPLETED,
            response.content,
        )

        # Step 6: Check status
        status = supervisor.get_task_status(task.task_id)
        assert status["subtasks"][0]["status"] == "completed"


@pytest.mark.integration
class TestInterviewerPanelIntegration:
    """Test integration between Interviewer and Panel systems."""

    def test_panel_uses_interviewer_for_tie_breaking(
        self,
        mock_llm_with_response,
        test_config,
    ):
        """Test that panel system uses interviewer for tie-breaking."""
        panel = PanelSystem(config=test_config)

        # Verify interviewer is initialized
        assert panel.interviewer is not None
        assert isinstance(panel.interviewer, InterviewerAgent)

        # Create panel
        panel.create_default_panel(num_panelists=3)

        # The interviewer should be available for tie-breaking
        assert panel.interviewer.llm is not None


@pytest.mark.integration
class TestMultiCandidateEvaluation:
    """Test evaluating multiple candidates through the full pipeline."""

    def test_evaluate_multiple_candidates_with_interviewer(
        self,
        mock_llm_with_response,
        test_config,
        sample_score_response,
        sample_recommendation_response,
        sample_comparison_response,
    ):
        """Test evaluating multiple candidates and selecting the best."""
        interviewer_llm = mock_llm_with_response(sample_score_response)
        interviewer = InterviewerAgent(llm=interviewer_llm, config=test_config)

        # Design questions
        questions_response = """
        {
            "questions": [
                {"question_id": "Q1", "text": "Question 1", "type": "sample", "evaluation_focus": "technical"}
            ]
        }
        """
        questions_llm = mock_llm_with_response(questions_response)
        interviewer.llm = questions_llm

        questions = interviewer.design_interview("Test task", num_questions=1)

        # Create candidate LLMs
        candidate_llms = {
            "CandidateA": mock_llm_with_response("Answer A"),
            "CandidateB": mock_llm_with_response("Answer B"),
            "CandidateC": mock_llm_with_response("Answer C"),
        }

        # Interview all candidates
        results = []
        for name, llm in candidate_llms.items():
            # Mock scoring
            score_llm = mock_llm_with_response(sample_score_response)
            interviewer.llm = score_llm

            # Mock recommendation
            rec_llm = mock_llm_with_response(sample_recommendation_response)

            original_generate = interviewer._generate_recommendation
            def mock_generate(*args, **kwargs):
                interviewer.llm = rec_llm
                result = original_generate(*args, **kwargs)
                interviewer.llm = score_llm
                return result

            interviewer._generate_recommendation = mock_generate

            result = interviewer.conduct_interview(
                candidate_name=name,
                candidate_llm=llm,
                questions=questions,
                task_description="Test task",
            )
            results.append(result)

            # Restore
            interviewer._generate_recommendation = original_generate

        # Compare candidates
        comparison_llm = mock_llm_with_response(sample_comparison_response)
        interviewer.llm = comparison_llm

        comparison = interviewer.compare_candidates(results)

        assert len(comparison["rankings"]) == 3
        assert "selected_candidate" in comparison
        assert comparison["selected_candidate"] in candidate_llms.keys()


@pytest.mark.integration
class TestConfigurationIntegration:
    """Test that configuration flows through all components."""

    def test_config_propagates_to_all_agents(self, test_config):
        """Test that config is properly used by all agents."""
        # Supervisor
        supervisor = SupervisorAgent(config=test_config)
        assert supervisor.config == test_config
        assert supervisor.config.max_iterations == 10

        # Interviewer
        interviewer = InterviewerAgent(config=test_config)
        assert interviewer.config == test_config
        assert interviewer.scoring_weights is not None

        # Panel
        panel = PanelSystem(config=test_config)
        assert panel.config == test_config
        assert panel.interviewer.config == test_config


@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Test error handling across components."""

    def test_supervisor_handles_invalid_operations(self, test_config):
        """Test that supervisor properly handles invalid operations."""
        supervisor = SupervisorAgent(config=test_config)

        # Invalid task ID
        with pytest.raises(ValueError):
            supervisor.get_task_status("nonexistent_task")

        with pytest.raises(ValueError):
            supervisor.assign_subtask("nonexistent_task", "subtask_1", "agent_1")

    def test_interviewer_handles_empty_results(self, test_config):
        """Test that interviewer handles edge cases."""
        interviewer = InterviewerAgent(config=test_config)

        # Empty candidate list
        comparison = interviewer.compare_candidates([])
        assert "error" in comparison


@pytest.mark.integration
@pytest.mark.slow
class TestFullSystemIntegration:
    """Test complete system integration."""

    def test_complete_system_workflow(
        self,
        mock_llm_with_response,
        test_config,
        sample_task_decomposition,
        sample_review_response,
        sample_ballot_response,
    ):
        """Test a complete workflow using all components."""
        # Step 1: Supervisor decomposes task
        supervisor = SupervisorAgent(
            llm=mock_llm_with_response(sample_task_decomposition),
            config=test_config,
        )

        task = supervisor.decompose_task("Build a complex distributed system")
        assert len(task.subtasks) > 0

        # Step 2: For a critical subtask, use panel to select best agent
        panel = PanelSystem(config=test_config)
        panel.create_default_panel(num_panelists=3)

        # Mock panelists
        for panelist in panel.panelists:
            panelist.llm = mock_llm_with_response(sample_ballot_response)

        # Mock interviewer for questions
        questions_response = """
        {
            "questions": [{
                "question_id": "Q1",
                "text": "How would you approach this?",
                "type": "sample",
                "evaluation_focus": "technical"
            }]
        }
        """
        panel.interviewer.llm = mock_llm_with_response(questions_response)

        # Evaluate candidate agents
        candidate_llms = {
            "AgentA": mock_llm_with_response("Approach A"),
            "AgentB": mock_llm_with_response("Approach B"),
        }

        panel_result = panel.conduct_panel_interview(
            task_description=task.subtasks[0].description,
            candidates=list(candidate_llms.keys()),
            candidate_llms=candidate_llms,
        )

        assert panel_result.decision in candidate_llms.keys()

        # Step 3: Assign selected agent to subtask
        selected_agent = panel_result.decision
        supervisor.assign_subtask(
            task.task_id,
            task.subtasks[0].task_id,
            selected_agent,
        )

        assert task.subtasks[0].assigned_to == selected_agent

        # Step 4: Simulate execution and review
        response = AgentResponse(
            agent_name=selected_agent,
            task_id=task.subtasks[0].task_id,
            content="Completed the implementation",
        )

        supervisor.llm = mock_llm_with_response(sample_review_response)
        review = supervisor.review_agent_output(
            task.task_id,
            task.subtasks[0].task_id,
            response,
        )

        assert review["approved"] is True

        # Step 5: Mark complete
        supervisor.update_subtask_status(
            task.task_id,
            task.subtasks[0].task_id,
            TaskStatus.COMPLETED,
            response.content,
        )

        # Verify final state
        status = supervisor.get_task_status(task.task_id)
        assert status["subtasks"][0]["status"] == "completed"
        assert status["subtasks"][0]["assigned_to"] == selected_agent

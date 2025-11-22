"""Extended model tests."""
import pytest
from tessera.models import Task, SubTask

@pytest.mark.unit
class TestModelsExtended:
    def test_task_metadata(self):
        task = Task(task_id="t1", goal="g", subtasks=[], metadata={"key": "val"})
        assert task.metadata["key"] == "val"
    
    def test_subtask_acceptance_criteria(self):
        sub = SubTask(task_id="s1", description="d", acceptance_criteria=["c1", "c2"])
        assert len(sub.acceptance_criteria) == 2

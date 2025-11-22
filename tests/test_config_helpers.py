"""Config helper tests."""

import pytest

from tessera.config.subphase_models import SubPhaseChecklist, SubPhaseDeliverable


@pytest.mark.unit
class TestSubPhaseModels:
    def test_deliverable_creation(self):
        sp = SubPhaseDeliverable(name="docs", outputs=["*.md"])
        assert sp.type == "deliverable"
        assert sp.required is True

    def test_checklist_creation(self):
        sp = SubPhaseChecklist(name="validate", questions=["Q1"])
        assert sp.type == "checklist"
        assert len(sp.questions) == 1

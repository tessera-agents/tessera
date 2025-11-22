"""Tests for workflow template system."""

import tempfile
from pathlib import Path

import pytest

from tessera.config.schema import WorkflowPhase
from tessera.workflow.templates import (
    WorkflowTemplate,
    WorkflowTemplateStorage,
    create_builtin_templates,
    install_builtin_templates,
)


@pytest.mark.unit
class TestWorkflowTemplate:
    """Test workflow template functionality."""

    def test_template_creation(self):
        """Test creating workflow template."""
        phases = [WorkflowPhase(name="implementation", description="Code implementation")]

        template = WorkflowTemplate(
            name="test-template",
            description="Test template",
            complexity="medium",
            phases=phases,
        )

        assert template.name == "test-template"
        assert template.description == "Test template"
        assert template.complexity == "medium"
        assert len(template.phases) == 1

    def test_template_to_dict(self):
        """Test converting template to dict."""
        phases = [WorkflowPhase(name="test", description="Test phase")]

        template = WorkflowTemplate(
            name="test",
            description="Test",
            complexity="simple",
            phases=phases,
            suggested_agents=[{"name": "agent1", "model": "gpt-4"}],
            metadata={"category": "test"},
        )

        data = template.to_dict()

        assert data["name"] == "test"
        assert data["description"] == "Test"
        assert len(data["phases"]) == 1
        assert len(data["suggested_agents"]) == 1
        assert data["metadata"]["category"] == "test"

    def test_template_from_dict(self):
        """Test creating template from dict."""
        data = {
            "name": "from-dict",
            "description": "Created from dict",
            "complexity": "complex",
            "phases": [
                {
                    "name": "implementation",
                    "description": "Code",
                    "typical_tasks": [],
                    "required": True,
                    "agents": [],
                    "sub_phases": [],
                    "required_for_complexity": ["complex"],
                },
            ],
            "suggested_agents": [],
            "metadata": {},
        }

        template = WorkflowTemplate.from_dict(data)

        assert template.name == "from-dict"
        assert template.description == "Created from dict"
        assert template.complexity == "complex"
        assert len(template.phases) == 1


@pytest.mark.unit
class TestWorkflowTemplateStorage:
    """Test workflow template storage."""

    def test_storage_initialization(self):
        """Test storage initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "workflows"
            storage = WorkflowTemplateStorage(storage_dir)

            assert storage.storage_dir == storage_dir
            assert storage.storage_dir.exists()

    def test_save_and_load_template(self):
        """Test saving and loading templates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = WorkflowTemplateStorage(Path(tmpdir))

            # Create template
            template = WorkflowTemplate(
                name="save-test",
                description="Test saving",
                complexity="medium",
                phases=[WorkflowPhase(name="test")],
            )

            # Save
            file_path = storage.save(template)
            assert file_path.exists()

            # Load
            loaded = storage.load("save-test")

            assert loaded is not None
            assert loaded.name == "save-test"
            assert loaded.description == "Test saving"
            assert loaded.complexity == "medium"

    def test_load_nonexistent_template(self):
        """Test loading template that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = WorkflowTemplateStorage(Path(tmpdir))

            loaded = storage.load("nonexistent")

            assert loaded is None

    def test_list_templates(self):
        """Test listing all templates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = WorkflowTemplateStorage(Path(tmpdir))

            # Save multiple templates
            for name in ["template1", "template2", "template3"]:
                template = WorkflowTemplate(
                    name=name, description="Test", complexity="simple", phases=[]
                )
                storage.save(template)

            templates = storage.list_templates()

            assert len(templates) == 3
            assert "template1" in templates
            assert "template2" in templates
            assert "template3" in templates

    def test_delete_template(self):
        """Test deleting template."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = WorkflowTemplateStorage(Path(tmpdir))

            # Save template
            template = WorkflowTemplate(
                name="to-delete", description="Test", complexity="simple", phases=[]
            )
            storage.save(template)

            # Delete
            result = storage.delete("to-delete")

            assert result is True
            assert storage.load("to-delete") is None

    def test_delete_nonexistent(self):
        """Test deleting nonexistent template."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = WorkflowTemplateStorage(Path(tmpdir))

            result = storage.delete("nonexistent")

            assert result is False

    def test_get_template_info(self):
        """Test getting template info."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = WorkflowTemplateStorage(Path(tmpdir))

            template = WorkflowTemplate(
                name="info-test",
                description="Info test",
                complexity="medium",
                phases=[WorkflowPhase(name="p1"), WorkflowPhase(name="p2")],
                suggested_agents=[{"name": "a1"}, {"name": "a2"}, {"name": "a3"}],
            )
            storage.save(template)

            info = storage.get_template_info("info-test")

            assert info is not None
            assert info["name"] == "info-test"
            assert info["description"] == "Info test"
            assert info["complexity"] == "medium"
            assert info["phase_count"] == 2
            assert info["agent_count"] == 3


@pytest.mark.unit
class TestBuiltinTemplates:
    """Test built-in template creation."""

    def test_create_builtin_templates(self):
        """Test creating built-in templates."""
        templates = create_builtin_templates()

        assert len(templates) >= 2  # At least fastapi and cli
        assert any(t.name == "fastapi-service" for t in templates)
        assert any(t.name == "python-cli" for t in templates)

    def test_install_builtin_templates(self):
        """Test installing built-in templates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from unittest.mock import patch

            with patch("tessera.workflow.templates.WorkflowTemplateStorage") as mock_storage_class:
                mock_storage = mock_storage_class.return_value
                mock_storage.save.return_value = Path(tmpdir) / "test.yaml"

                count = install_builtin_templates()

                assert count >= 2
                assert mock_storage.save.call_count >= 2

    def test_fastapi_template_structure(self):
        """Test FastAPI template has expected structure."""
        templates = create_builtin_templates()

        fastapi = next((t for t in templates if t.name == "fastapi-service"), None)

        assert fastapi is not None
        assert len(fastapi.phases) >= 2  # At least design and implementation
        assert len(fastapi.suggested_agents) >= 2
        assert "fastapi" in fastapi.metadata.get("tags", [])

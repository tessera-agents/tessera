"""
Workflow template system for reusable project patterns.

Allows saving and loading workflow configurations as templates.
"""

from pathlib import Path
from typing import Any

import yaml

from ..config.schema import WorkflowPhase
from ..config.xdg import get_tessera_config_dir
from ..logging_config import get_logger

logger = get_logger(__name__)


class WorkflowTemplate:
    """
    Workflow template definition.

    Templates define reusable workflow patterns for common project types.
    """

    def __init__(  # noqa: PLR0913
        self,
        name: str,
        description: str,
        complexity: str,
        phases: list[WorkflowPhase],
        suggested_agents: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize workflow template.

        Args:
            name: Template name (e.g., "fastapi-service")
            description: Template description
            complexity: Default complexity (simple, medium, complex)
            phases: Workflow phases
            suggested_agents: Recommended agent configurations
            metadata: Additional template metadata
        """
        self.name = name
        self.description = description
        self.complexity = complexity
        self.phases = phases
        self.suggested_agents = suggested_agents or []
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """
        Convert template to dictionary.

        Returns:
            Dict representation
        """
        return {
            "name": self.name,
            "description": self.description,
            "complexity": self.complexity,
            "phases": [
                {
                    "name": p.name,
                    "description": p.description,
                    "typical_tasks": p.typical_tasks,
                    "required": p.required,
                    "agents": p.agents,
                    "sub_phases": p.sub_phases,
                    "required_for_complexity": p.required_for_complexity,
                }
                for p in self.phases
            ],
            "suggested_agents": self.suggested_agents,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowTemplate":
        """
        Create template from dictionary.

        Args:
            data: Dict representation

        Returns:
            WorkflowTemplate instance
        """
        phases = [WorkflowPhase(**phase_data) for phase_data in data.get("phases", [])]

        return cls(
            name=data["name"],
            description=data["description"],
            complexity=data.get("complexity", "medium"),
            phases=phases,
            suggested_agents=data.get("suggested_agents"),
            metadata=data.get("metadata"),
        )


class WorkflowTemplateStorage:
    """
    Storage for workflow templates.

    Templates stored in ~/.config/tessera/workflows/
    """

    def __init__(self, storage_dir: Path | None = None) -> None:
        """
        Initialize template storage.

        Args:
            storage_dir: Storage directory (defaults to XDG config/workflows)
        """
        if storage_dir is None:
            storage_dir = get_tessera_config_dir() / "workflows"

        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"WorkflowTemplateStorage: {self.storage_dir}")

    def save(self, template: WorkflowTemplate) -> Path:
        """
        Save workflow template.

        Args:
            template: Template to save

        Returns:
            Path to saved template file
        """
        file_path = self.storage_dir / f"{template.name}.yaml"

        template_data = template.to_dict()

        with file_path.open("w") as f:
            yaml.dump(template_data, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Saved workflow template: {template.name}")

        return file_path

    def load(self, name: str) -> WorkflowTemplate | None:
        """
        Load workflow template by name.

        Args:
            name: Template name

        Returns:
            WorkflowTemplate or None if not found
        """
        file_path = self.storage_dir / f"{name}.yaml"

        if not file_path.exists():
            logger.warning(f"Template not found: {name}")
            return None

        try:
            with file_path.open() as f:
                data = yaml.safe_load(f)

            template = WorkflowTemplate.from_dict(data)
            logger.info(f"Loaded workflow template: {name}")

            return template

        except (OSError, ValueError):
            logger.exception(f"Failed to load template {name}")
            return None

    def list_templates(self) -> list[str]:
        """
        List all available templates.

        Returns:
            List of template names
        """
        if not self.storage_dir.exists():
            return []

        templates = [file_path.stem for file_path in self.storage_dir.glob("*.yaml")]

        return sorted(templates)

    def delete(self, name: str) -> bool:
        """
        Delete a template.

        Args:
            name: Template name

        Returns:
            True if deleted
        """
        file_path = self.storage_dir / f"{name}.yaml"

        if not file_path.exists():
            return False

        try:
            file_path.unlink()
            logger.info(f"Deleted template: {name}")
            return True

        except OSError:
            logger.exception(f"Failed to delete template {name}")
            return False

    def get_template_info(self, name: str) -> dict[str, Any] | None:
        """
        Get template metadata without full load.

        Args:
            name: Template name

        Returns:
            Template info dict or None
        """
        template = self.load(name)

        if template is None:
            return None

        return {
            "name": template.name,
            "description": template.description,
            "complexity": template.complexity,
            "phase_count": len(template.phases),
            "agent_count": len(template.suggested_agents),
        }


def create_builtin_templates() -> list[WorkflowTemplate]:
    """
    Create built-in workflow templates.

    Returns:
        List of built-in templates
    """
    templates = []

    # FastAPI Service Template
    fastapi_template = WorkflowTemplate(
        name="fastapi-service",
        description="FastAPI REST API service with authentication",
        complexity="medium",
        phases=[
            WorkflowPhase(
                name="design",
                description="API design and data models",
                typical_tasks=["Design endpoints", "Define models", "Plan auth"],
                required=True,
                agents=["architect"],
                sub_phases=[
                    {
                        "name": "api_spec",
                        "type": "deliverable",
                        "outputs": ["api-spec.yaml", "models.py"],
                    },
                ],
                required_for_complexity=["medium", "complex"],
            ),
            WorkflowPhase(
                name="implementation",
                description="Implement API endpoints and business logic",
                typical_tasks=["Create endpoints", "Implement auth", "Add validation"],
                required=True,
                agents=["python-expert"],
                sub_phases=[
                    {
                        "name": "code",
                        "type": "deliverable",
                        "outputs": ["src/**/*.py", "requirements.txt"],
                    },
                ],
                required_for_complexity=["simple", "medium", "complex"],
            ),
            WorkflowPhase(
                name="testing",
                description="Write tests and verify coverage",
                typical_tasks=["Unit tests", "Integration tests", "Coverage check"],
                required=True,
                agents=["test-engineer"],
                sub_phases=[
                    {
                        "name": "tests",
                        "type": "deliverable",
                        "outputs": ["tests/**/*.py", "pytest.ini"],
                    },
                    {
                        "name": "coverage_check",
                        "type": "checklist",
                        "questions": ["Coverage >= 80%?", "All endpoints tested?"],
                    },
                ],
                required_for_complexity=["medium", "complex"],
            ),
        ],
        suggested_agents=[
            {
                "name": "architect",
                "model": "gpt-4",
                "capabilities": ["design", "architecture"],
            },
            {
                "name": "python-expert",
                "model": "gpt-4",
                "capabilities": ["python", "fastapi", "backend"],
            },
            {
                "name": "test-engineer",
                "model": "gpt-4",
                "capabilities": ["testing", "pytest"],
            },
        ],
        metadata={
            "category": "web-service",
            "tags": ["python", "fastapi", "rest-api", "authentication"],
        },
    )
    templates.append(fastapi_template)

    # Python CLI Tool Template
    cli_template = WorkflowTemplate(
        name="python-cli",
        description="Python CLI application with argparse/click",
        complexity="simple",
        phases=[
            WorkflowPhase(
                name="implementation",
                description="Implement CLI commands and logic",
                typical_tasks=["Create CLI structure", "Add commands", "Handle args"],
                required=True,
                agents=["python-expert"],
                sub_phases=[
                    {
                        "name": "cli_code",
                        "type": "deliverable",
                        "outputs": ["src/**/*.py", "setup.py"],
                    },
                ],
                required_for_complexity=["simple", "medium", "complex"],
            ),
            WorkflowPhase(
                name="testing",
                description="Test CLI commands",
                typical_tasks=["Command tests", "Arg parsing tests"],
                required=False,
                agents=["test-engineer"],
                sub_phases=[
                    {
                        "name": "tests",
                        "type": "deliverable",
                        "outputs": ["tests/**/*.py"],
                    },
                ],
                required_for_complexity=["medium", "complex"],
            ),
        ],
        suggested_agents=[
            {
                "name": "python-expert",
                "model": "gpt-4",
                "capabilities": ["python", "cli"],
            },
        ],
        metadata={
            "category": "cli-tool",
            "tags": ["python", "cli", "argparse"],
        },
    )
    templates.append(cli_template)

    return templates


def install_builtin_templates() -> int:
    """
    Install built-in templates to user config.

    Returns:
        Number of templates installed
    """
    storage = WorkflowTemplateStorage()
    templates = create_builtin_templates()

    installed = 0
    for template in templates:
        try:
            storage.save(template)
            installed += 1
        except OSError:
            logger.exception(f"Failed to install template {template.name}")

    logger.info(f"Installed {installed} built-in templates")

    return installed

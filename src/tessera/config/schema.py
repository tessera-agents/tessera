"""
Unified configuration schema for Tessera.

All configuration is defined in a single config.yaml file with multiple sections.
"""

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from .xdg import get_tessera_config_dir
from .yaml_source import XDGYamlSettingsSource

# ==============================================================================
# NESTED CONFIG MODELS (use BaseModel, not BaseSettings)
# ==============================================================================


class TesseraGeneralConfig(BaseModel):
    """General Tessera settings."""

    version: str = "1.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    debug: bool = False
    interactive_mode: bool = True
    default_complexity: Literal["simple", "medium", "complex"] = "medium"


class ObservabilityLocalConfig(BaseModel):
    """Local OTEL export configuration."""

    enabled: bool = True
    traces_file: str = "~/.cache/tessera/otel/traces.jsonl"
    metrics_file: str = "~/.cache/tessera/otel/metrics.jsonl"
    max_file_size_mb: int = 100
    max_files: int = 10


class ObservabilityBackendConfig(BaseModel):
    """Cloud observability backend configuration."""

    name: str
    enabled: bool = False
    endpoint: str
    api_key: str = ""


class ObservabilityConfig(BaseModel):
    """Observability configuration."""

    local: ObservabilityLocalConfig = Field(default_factory=ObservabilityLocalConfig)
    backends: list[ObservabilityBackendConfig] = Field(default_factory=list)


class AgentDefaultsConfig(BaseModel):
    """Default values for all agents."""

    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    timeout: int = Field(default=90, gt=0)
    max_retries: int = Field(default=3, ge=0)
    context_size: int = Field(default=8192, gt=0)


class AgentToolsConfig(BaseModel):
    """Tool access configuration for an agent."""

    strategy: Literal["allowlist", "blocklist", "category", "risk-based"] | None = None
    max_risk_level: Literal["safe", "low", "medium", "high", "critical"] | None = None
    allow: list[str] = Field(default_factory=list)
    deny: list[str] = Field(default_factory=list)
    allow_categories: list[str] = Field(default_factory=list)
    deny_categories: list[str] = Field(default_factory=list)


class AgentDefinition(BaseModel):
    """Individual agent configuration."""

    name: str
    role: str | None = None  # orchestrator, worker
    model: str
    provider: str = "openai"
    system_prompt: str | None = None  # Inline prompt
    system_prompt_file: str | None = None  # Path to markdown file
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    context_size: int | None = Field(default=None, gt=0)
    api_url: str | None = None
    api_key: str | None = None
    timeout: int | None = Field(default=None, gt=0)
    max_retries: int | None = Field(default=None, ge=0)
    capabilities: list[str] = Field(default_factory=list)
    phase_affinity: list[str] = Field(default_factory=list)  # Which SDLC phases
    tools: AgentToolsConfig | None = None


class AgentsConfig(BaseModel):
    """Agents configuration section."""

    defaults: AgentDefaultsConfig = Field(default_factory=AgentDefaultsConfig)
    definitions: list[AgentDefinition] = Field(default_factory=list)


class ToolsGlobalConfig(BaseModel):
    """Global tool access control."""

    strategy: Literal["allowlist", "blocklist", "category", "risk-based"] = "risk-based"
    max_risk_level: Literal["safe", "low", "medium", "high", "critical"] = "high"
    allow: list[str] = Field(default_factory=list)
    deny: list[str] = Field(default_factory=list)


class ToolApprovalConfig(BaseModel):
    """Tool approval configuration."""

    approval_required: Any = False  # Can be bool or list of operations


class ToolBuiltinConfig(BaseModel):
    """Built-in tool configuration."""

    enabled: bool = True
    approval_required: Any = Field(default=False)  # Can be bool or list
    safe_paths: list[str] = Field(default_factory=list)


class PluginDefinition(BaseModel):
    """Python plugin tool definition."""

    name: str
    file: str
    enabled: bool = True
    risk_level: Literal["safe", "low", "medium", "high", "critical"] = "medium"
    approval_required: Any = False  # Can be bool or list
    config: dict[str, Any] = Field(default_factory=dict)


class MCPServerConfig(BaseModel):
    """MCP server configuration."""

    name: str
    enabled: bool = True
    type: Literal["stdio", "sse"] = "stdio"
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    url: str | None = None  # For SSE type
    env: dict[str, str] = Field(default_factory=dict)
    api_key: str | None = None
    risk_level: Literal["safe", "low", "medium", "high", "critical"] = "medium"


class ToolsPluginsConfig(BaseModel):
    """Plugin tools configuration."""

    discovery: list[str] = Field(default_factory=list)
    definitions: list[PluginDefinition] = Field(default_factory=list)


class ToolsConfig(BaseModel):
    """Tools configuration section."""

    global_config: ToolsGlobalConfig = Field(default_factory=ToolsGlobalConfig, alias="global")
    builtin: dict[str, ToolBuiltinConfig] = Field(default_factory=dict)
    plugins: ToolsPluginsConfig = Field(default_factory=ToolsPluginsConfig)
    mcp: list[MCPServerConfig] = Field(default_factory=list)


class CommunicationChannelConfig(BaseModel):
    """Communication channel configuration."""

    name: str
    type: Literal["slack", "discord", "email"] = "slack"
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


class CommunicationRoutingRule(BaseModel):
    """Communication routing rule."""

    risk_level: str | None = None
    agent: str | None = None
    tool: str | None = None
    channel: str


class CommunicationsConfig(BaseModel):
    """Communications configuration section."""

    default: str = ""
    channels: list[CommunicationChannelConfig] = Field(default_factory=list)
    routing: list[CommunicationRoutingRule] = Field(default_factory=list)


class CostLimitConfig(BaseModel):
    """Cost limit configuration."""

    daily_usd: float | None = None
    monthly_usd: float | None = None
    default_usd: float | None = None
    max_usd: float | None = None
    task_limit_usd: float | None = None
    enforcement: Literal["soft", "hard"] = "soft"


class CostManualPricing(BaseModel):
    """Manual pricing override."""

    model: str
    provider: str
    prompt_price_per_1k: float
    completion_price_per_1k: float


class CostConfig(BaseModel):
    """Cost management configuration section."""

    limits: dict[str, CostLimitConfig] = Field(default_factory=dict)
    pricing_auto_update: bool = Field(default=True, alias="pricing.auto_update")
    pricing_cache_duration_hours: int = Field(default=24, alias="pricing.cache_duration_hours")
    pricing_manual_overrides: list[CostManualPricing] = Field(default_factory=list, alias="pricing.manual_overrides")


class ProjectGenerationPhase(BaseModel):
    """SDLC phase definition."""

    name: str
    agents: list[str]
    required: bool = True
    parallel: bool = False
    approval_required: bool = False
    deliverables: list[str] = Field(default_factory=list)
    min_coverage: int | None = None
    tools: list[str] = Field(default_factory=list)


class ProjectGenerationInterviewConfig(BaseModel):
    """Interview configuration for project generation."""

    enabled: bool = True
    min_questions: int = 3
    max_questions: int = 10
    adaptive: bool = True


class ProjectGenerationPlanningConfig(BaseModel):
    """Planning configuration."""

    breakdown_strategy: Literal["hierarchical", "flat", "adaptive"] = "hierarchical"
    max_task_depth: int = 3
    min_subtasks: int = 2
    max_subtasks: int = 15


class ProjectGenerationOutputConfig(BaseModel):
    """Output configuration."""

    project_root: str = "./generated_project"
    create_git_repo: bool = True
    initial_commit: bool = True
    structure: list[str] = Field(default_factory=lambda: ["src/", "tests/", "docs/", "README.md"])


class ProjectGenerationConfig(BaseModel):
    """Project generation configuration section."""

    interview: ProjectGenerationInterviewConfig = Field(default_factory=ProjectGenerationInterviewConfig)
    planning: ProjectGenerationPlanningConfig = Field(default_factory=ProjectGenerationPlanningConfig)
    phases: list[ProjectGenerationPhase] = Field(default_factory=list)
    output: ProjectGenerationOutputConfig = Field(default_factory=ProjectGenerationOutputConfig)


# ==============================================================================
# WORKFLOW PHASE MODELS (NEW)
# ==============================================================================


class WorkflowPhase(BaseModel):
    """
    Workflow phase definition.

    A phase provides context for supervisor's task creation and defines
    standard procedures (sub-phases) applied to all tasks in that phase.
    """

    name: str
    description: str = ""
    required: bool = True
    required_for_complexity: list[Literal["simple", "medium", "complex"]] = Field(
        default_factory=lambda: ["simple", "medium", "complex"]
    )

    # Hints for supervisor about what tasks to create
    typical_tasks: list[str] = Field(default_factory=list)

    # Agents commonly used in this phase
    agents: list[str] = Field(default_factory=list)

    # Sub-phases: SOPs applied to ALL tasks in this phase
    sub_phases: list[dict[str, Any]] = Field(default_factory=list)

    # Dependencies on other phases
    depends_on: list[str] = Field(default_factory=list)


class IterationConfig(BaseModel):
    """Iteration and loop control configuration."""

    max_iterations: int = 5
    quality_improvement_threshold: float = 0.1
    loop_detection_enabled: bool = True
    same_error_threshold: int = 3


class QualityMonitoringConfig(BaseModel):
    """Quality monitoring configuration."""

    enabled: bool = True
    check_after_each_task: bool = True
    metrics: list[str] = Field(
        default_factory=lambda: [
            "tests_passing",
            "coverage_percentage",
            "code_quality_score",
        ]
    )


class WorkflowConfig(BaseModel):
    """Workflow configuration with phases and sub-phases."""

    # Project-level phases
    phases: list[WorkflowPhase] = Field(default_factory=list)

    # Iteration control
    iteration: IterationConfig = Field(default_factory=IterationConfig)

    # Quality monitoring
    monitoring: QualityMonitoringConfig = Field(default_factory=QualityMonitoringConfig)


# ==============================================================================
# MAIN SETTINGS CLASS
# ==============================================================================


class TesseraSettings(BaseSettings):
    """
    Unified Tessera configuration.

    All configuration loaded from a single config.yaml file with multiple sections.

    Configuration precedence (highest to lowest):
    1. Explicit init arguments
    2. Environment variables (TESSERA_*)
    3. .env file
    4. YAML config files (project > user > system)
    5. Field defaults
    """

    model_config = SettingsConfigDict(
        env_prefix="TESSERA_",
        env_nested_delimiter="__",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra fields in YAML
    )

    # Configuration sections
    tessera: TesseraGeneralConfig = Field(default_factory=TesseraGeneralConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    communications: CommunicationsConfig = Field(default_factory=CommunicationsConfig)
    cost: CostConfig = Field(default_factory=CostConfig)

    # Workflow with phases and sub-phases (NEW)
    workflow: WorkflowConfig = Field(default_factory=WorkflowConfig)

    # Legacy project generation config (backward compatibility)
    project_generation: ProjectGenerationConfig = Field(default_factory=ProjectGenerationConfig)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """
        Customize settings sources to include YAML config files.

        Precedence order (highest to lowest):
        1. init_settings - Explicit arguments
        2. env_settings - Environment variables
        3. dotenv_settings - .env file
        4. XDGYamlSettingsSource - YAML config files
        5. file_secret_settings - Secrets directory
        """
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            XDGYamlSettingsSource(settings_cls, app_name="tessera"),
            file_secret_settings,
        )

    @property
    def config_dir(self) -> Path:
        """Get configuration directory path."""
        return get_tessera_config_dir()

    def get_agent(self, name: str) -> AgentDefinition | None:
        """
        Get agent definition by name.

        Args:
            name: Agent name

        Returns:
            AgentDefinition if found, None otherwise
        """
        for agent in self.agents.definitions:
            if agent.name == name:
                return agent
        return None

    def get_communication_channel(self, name: str) -> CommunicationChannelConfig | None:
        """
        Get communication channel by name.

        Args:
            name: Channel name

        Returns:
            CommunicationChannelConfig if found, None otherwise
        """
        for channel in self.communications.channels:
            if channel.name == name:
                return channel
        return None

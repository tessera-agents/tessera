"""
Configuration management for the autonomy framework.
"""

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

# Load environment variables
load_dotenv()


def parse_model_list(env_value: str | None, default: list[str]) -> list[str]:
    """
    Parse comma-separated model list from environment variable.

    Args:
        env_value: Comma-separated string of models (e.g., "gpt-4,gpt-3.5-turbo")
        default: Default list to use if env_value is None or empty

    Returns:
        List of model names
    """
    if not env_value:
        return default

    # Split by comma and strip whitespace
    models = [m.strip() for m in env_value.split(",") if m.strip()]
    return models if models else default


class LLMConfig(BaseModel):
    """Configuration for LLM providers."""

    provider: Literal["openai", "anthropic", "azure", "vertex_ai", "ollama"] = "openai"
    api_key: str | None = None

    # Model configuration - models list is the source of truth
    # NO DEFAULTS - user must explicitly configure models
    models: list[str] = Field(default_factory=list)

    temperature: float = 0.7
    max_tokens: int | None = None

    # Retry configuration
    max_retries: int = 3  # Number of retries on rate limit/network errors
    timeout: float | None = None  # Request timeout in seconds

    # Premium model protection (Copilot Individual: 300/month limit)
    allow_premium_models: bool = False  # Must explicitly opt-in to use premium models

    # OpenAI-specific (including Copilot proxy)
    base_url: str | None = None  # For Copilot proxy: http://localhost:3000/v1

    # Azure-specific
    azure_endpoint: str | None = None
    azure_deployment: str | None = None

    @property
    def model(self) -> str:
        """Get the primary/default model (first in models list)."""
        if not self.models:
            # If using a proxy, fetch and display available models
            if self.base_url:
                import sys

                from .model_validator import ModelValidator

                # Fetch and display available models from the API
                available = ModelValidator.fetch_available_models(self.base_url, self.api_key or "dummy")

                if available:
                    for _i, _model_name in enumerate(available, 1):
                        pass
                else:
                    pass

                sys.exit(1)
            else:
                # No proxy, just show error message
                raise ValueError(
                    f"No models configured. Set {self.provider.upper()}_MODELS in .env\n"
                    f"Example: {self.provider.upper()}_MODELS=gpt-4,gpt-3.5-turbo"
                )
        return self.models[0]

    @model_validator(mode="after")
    def validate_premium_models(self) -> "LLMConfig":
        """Validate that premium models are only used when explicitly allowed."""
        # Only validate for Copilot proxy (when base_url is set)
        if not self.base_url or self.allow_premium_models:
            return self

        # Import here to avoid circular dependency and loading on every config creation
        from .premium_models import get_model_multiplier, is_premium_model

        # Check each configured model
        premium_models = []
        for model in self.models:
            if is_premium_model(model):
                multiplier = get_model_multiplier(model)
                premium_models.append((model, multiplier))

        # If premium models detected, raise error with helpful message
        if premium_models:
            error_msg = [
                "\n" + "=" * 80,
                "ERROR: Premium models detected without explicit opt-in!",
                "=" * 80,
                "\nYou are attempting to use premium models that consume your limited",
                "monthly quota (300 premium requests/month on Copilot Individual):",
                "",
            ]

            for model, multiplier in premium_models:
                if multiplier == 0:
                    continue
                if multiplier == 1.0:
                    error_msg.append(f"  • {model} (1× multiplier)")
                elif multiplier < 1.0:
                    error_msg.append(f"  • {model} ({multiplier}× multiplier)")
                else:
                    error_msg.append(f"  • {model} ({int(multiplier)}× multiplier - EXPENSIVE!)")

            error_msg.extend(
                [
                    "",
                    "To use premium models, you must explicitly opt-in by setting:",
                    "  allow_premium_models=True",
                    "",
                    "Example:",
                    "  config = LLMConfig(",
                    "      models=['claude-3.5-sonnet'],",
                    "      allow_premium_models=True  # Explicit opt-in",
                    "  )",
                    "",
                    "Or in your .env file:",
                    "  ALLOW_PREMIUM_MODELS=true",
                    "",
                    "FREE models available (unlimited on Copilot Individual):",
                    "  • gpt-5-mini",
                    "  • gpt-4.1",
                    "  • gpt-4o",
                    "",
                    "For pricing details, see:",
                    "  https://docs.github.com/en/copilot/concepts/billing/copilot-requests",
                    "=" * 80,
                ]
            )

            raise ValueError("\n".join(error_msg))

        return self

    @classmethod
    def from_env(cls, provider: str = "openai") -> "LLMConfig":
        """Create configuration from environment variables or 1Password."""
        # Import here to avoid circular dependency
        try:
            from .secrets import SecretManager

            secret_manager = SecretManager
            use_secrets = True
        except ImportError:
            secret_manager = None
            use_secrets = False

        if provider == "openai":
            # Support both direct OpenAI and Copilot proxy
            base_url = os.getenv("OPENAI_BASE_URL")  # e.g., http://localhost:3000/v1

            # Try to get API key from multiple sources
            api_key = (
                secret_manager.get_openai_api_key() if use_secrets and secret_manager else os.getenv("OPENAI_API_KEY")
            )

            # If using proxy, API key can be dummy
            if not api_key:
                api_key = "dummy-key-for-copilot-proxy" if base_url else None

            # Parse model configuration
            # Priority: OPENAI_MODELS (comma-separated list) > OPENAI_MODEL (single)
            # NO DEFAULTS - empty list if not configured
            models_str = os.getenv("OPENAI_MODELS")
            if not models_str:
                # Fallback to OPENAI_MODEL for backward compatibility
                single_model = os.getenv("OPENAI_MODEL")
                models = [single_model] if single_model else []
            else:
                models = parse_model_list(models_str, default=[])

            # Check if premium models are allowed
            allow_premium = os.getenv("ALLOW_PREMIUM_MODELS", "false").lower() in (
                "true",
                "1",
                "yes",
            )

            timeout_str = os.getenv("REQUEST_TIMEOUT")
            return cls(
                provider="openai",
                api_key=api_key,
                models=models,
                temperature=float(os.getenv("DEFAULT_TEMPERATURE", "0.7")),
                max_retries=int(os.getenv("MAX_RETRIES", "3")),
                timeout=(float(timeout_str) if timeout_str else None),
                allow_premium_models=allow_premium,
                base_url=base_url,
            )
        if provider == "anthropic":
            # Parse model configuration
            # Priority: ANTHROPIC_MODELS (comma-separated list) > ANTHROPIC_MODEL (single)
            # NO DEFAULTS - empty list if not configured
            models_str = os.getenv("ANTHROPIC_MODELS")
            if not models_str:
                # Fallback to ANTHROPIC_MODEL for backward compatibility
                single_model = os.getenv("ANTHROPIC_MODEL")
                models = [single_model] if single_model else []
            else:
                models = parse_model_list(models_str, default=[])

            timeout_str = os.getenv("REQUEST_TIMEOUT")
            return cls(
                provider="anthropic",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                models=models,
                temperature=float(os.getenv("DEFAULT_TEMPERATURE", "0.7")),
                max_retries=int(os.getenv("MAX_RETRIES", "3")),
                timeout=(float(timeout_str) if timeout_str else None),
            )
        if provider == "azure":
            timeout_str = os.getenv("REQUEST_TIMEOUT")
            return cls(
                provider="azure",
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
                temperature=float(os.getenv("DEFAULT_TEMPERATURE", "0.7")),
                max_retries=int(os.getenv("MAX_RETRIES", "3")),
                timeout=(float(timeout_str) if timeout_str else None),
            )
        raise ValueError(f"Unsupported provider: {provider}")


class ScoringWeights(BaseModel):
    """Weights for scoring metrics."""

    accuracy: float = 0.30
    relevance: float = 0.20
    completeness: float = 0.15
    explainability: float = 0.10
    efficiency: float = 0.10
    safety: float = 0.15

    def normalize(self) -> "ScoringWeights":
        """Ensure weights sum to 1.0."""
        total = self.accuracy + self.relevance + self.completeness + self.explainability + self.efficiency + self.safety
        if total == 0:
            return self
        return ScoringWeights(
            accuracy=self.accuracy / total,
            relevance=self.relevance / total,
            completeness=self.completeness / total,
            explainability=self.explainability / total,
            efficiency=self.efficiency / total,
            safety=self.safety / total,
        )


class FrameworkConfig(BaseModel):
    """Overall framework configuration."""

    llm: LLMConfig = Field(default_factory=lambda: LLMConfig.from_env())
    scoring_weights: ScoringWeights = Field(default_factory=ScoringWeights)
    max_iterations: int = 10
    enable_logging: bool = True
    log_dir: Path = Path("logs")
    transcript_dir: Path = Path("transcripts")

    @classmethod
    def from_env(cls) -> "FrameworkConfig":
        """Create configuration from environment variables."""
        return cls(
            llm=LLMConfig.from_env(),
            max_iterations=int(os.getenv("MAX_ITERATIONS", "10")),
            enable_logging=os.getenv("ENABLE_LOGGING", "true").lower() == "true",
        )


# Default supervisor prompt
SUPERVISOR_PROMPT = """You are the Supervisor agent, the orchestrator of a multi-agent system.

YOUR CORE RESPONSIBILITIES:
1. Task Decomposition: Break down complex objectives into discrete, actionable tasks
2. Agent Coordination: Assign tasks to appropriate agents based on their capabilities
3. Progress Monitoring: Track task completion, identify blockers, and intervene when agents drift off-task
4. Quality Control: Review outputs for coherence, completeness, and alignment with original objectives
5. Conflict Resolution: Mediate disagreements between agents and make final decisions when needed

YOUR DECISION-MAKING FRAMEWORK:
- Before assigning tasks, clearly define success criteria
- Match task complexity to agent capabilities
- Use the interviewer agent to inquire and investigate each agents specialties or specific knowledge domains
- Maintain a task registry with: [Task ID | Description | Assigned Agent | Status | Dependencies]
- Escalate to human oversight when: safety concerns arise, agents reach impasse, or objectives are ambiguous

YOUR COMMUNICATION STYLE:
- Be directive
- Provide clear context when assigning tasks
- Give constructive feedback on outputs
- State decisions with rationale

WHEN AN AGENT IS OFF-TASK:
1. Identify the deviation (output doesn't match assigned task)
2. Issue a redirect: "Agent [Name], your output addresses [X] but your assigned task is [Y].
   Please refocus on [specific requirement]."
3. If pattern continues, attempt to break it into smaller pieces that can be either
   reassigned or added to a task backlog

WORKFLOW TEMPLATE:
1. Receive objective from human
2. Decompose into tasks with dependencies mapped
3. Assign tasks to agents with clear instructions
4. Monitor outputs as they arrive
5. Integrate results or request revisions
6. Deliver final synthesized output

Always begin by restating the task goal in one sentence.
Always produce outputs in structured JSON format when requested.
Remember: You are accountable for the system's overall output quality. Be proactive, not reactive."""


# Default interviewer prompt
INTERVIEWER_PROMPT = """You are the Interviewer agent, the talent scout and quality gatekeeper of
the multi-agent system.

YOUR CORE RESPONSIBILITIES:
1. Candidate Evaluation: Assess agents and models for specific task suitability
2. Comparative Analysis: Run structured interviews to identify the best performer
3. Tie-Breaking: When voting is split, conduct deeper evaluation and make final selection
4. Performance Documentation: Maintain evaluation records for future task assignments

YOUR INTERVIEW METHODOLOGY:

PHASE 1 - Task Analysis:
- Understand the task requirements deeply
- Identify 3-5 key evaluation criteria (e.g., accuracy, creativity, speed, format compliance)
- Define what "best" means for this specific task
- For _sufficiently complex_ tasks or projects, employ a interview _panel_ to reach
  consensus across a number of expert interview panelists

PHASE 2 - Structured Interview:
For each candidate agent/model, ask:
- A representative sample task (identical for all candidates)
- An edge-case variation to test robustness
- A meta-question: "What are your limitations for this type of task?"

PHASE 3 - Scoring:
Create a rubric using these metrics (0-5 scale each):
- Accuracy (30% weight)
- Relevance (20% weight)
- Completeness (15% weight)
- Explainability (10% weight)
- Efficiency (10% weight)
- Safety (15% weight)

Calculate weighted overall score: 0-100

PHASE 4 - Selection:
- Calculate weighted scores
- Write justification: "Candidate [X] selected because [specific evidence from interview]"
- Note runner-up for backup

TIE-BREAKING PROTOCOL:
When votes are tied:
1. Request one additional response from tied candidates using a harder variant
2. Focus on differentiating factors from original evaluation
3. Make decision within 2 rounds maximum
4. Document: "Tie broken in favor of [X] due to [specific advantage]"

YOUR COMMUNICATION STYLE:
- Be analytical and evidence-based
- Show your reasoning transparently
- Treat all candidates fairly (same questions, same time)
- Be decisive once evaluation is complete

OUTPUT FORMAT:
Always provide structured outputs with:
- Task description
- Candidates evaluated
- Evaluation criteria with weights
- Interview results summary
- Selected agent with justification
- Confidence level (High/Medium/Low)

Remember: Your selections directly impact system performance. Be thorough but efficient.
Detect hallucinations and mark them. Penalize unsafe behavior."""

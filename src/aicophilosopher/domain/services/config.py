from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings

LLMBackend = Literal["ollama", "claude", "gemini"]

# Canonical default workspace root (override with AICOPH_WORKSPACE_DIR).
DEFAULT_WORKSPACE_DIR = "~/.aicophilosopher"


class Config(BaseSettings):
    """Application configuration.

    All settings are loaded from environment variables with the ``AICOPH_`` prefix
    (e.g. ``AICOPH_LLM_BACKEND``, ``AICOPH_WORKSPACE_DIR``). A ``.env`` file is
    also read when present.
    """

    model_config = {"env_prefix": "AICOPH_", "env_file": ".env", "extra": "ignore"}

    llm_backend: LLMBackend = Field(default="ollama", description="LLM backend: ollama, claude, gemini")
    llm_model: str = Field(default="", description="LLM model name")
    llm_api_key: str = Field(default="", description="LLM API key")
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)

    allow_external_search: bool = Field(default=False, description="Allow external search APIs")
    allow_external_agents: bool = Field(default=False, description="Allow external agent integration")
    consent_required: bool = Field(default=True, description="Require consent for external services")

    workspace_dir: str = Field(
        default=DEFAULT_WORKSPACE_DIR,
        description="Workspace root directory (projects live under <workspace>/projects/)",
    )
    log_level: str = Field(default="INFO", description="Log level: DEBUG, INFO, WARNING, ERROR")
    project_dir: str = Field(default="", description="Override project directory")

    hermes_enabled: bool = Field(default=False, description="Enable Hermes Agent bridge")
    opencode_enabled: bool = Field(default=False, description="Enable OpenCode Go bridge")

    def resolved_workspace_dir(self) -> Path:
        """Return the expanded absolute workspace root.

        This is the single source of truth for where application data lives.
        Projects are stored under ``<workspace>/projects/<project_id>/``
        (see :meth:`projects_dir` and FileSystemAdapter).
        """
        return Path(self.workspace_dir).expanduser().resolve()

    def projects_dir(self) -> Path:
        """Return the directory that contains individual project folders.

        Layout matches FileSystemAdapter: ``{workspace_dir}/projects/``.
        """
        return self.resolved_workspace_dir() / "projects"

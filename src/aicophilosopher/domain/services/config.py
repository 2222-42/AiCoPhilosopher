from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings

LLMBackend = Literal["ollama", "claude", "gemini"]


class Config(BaseSettings):
    model_config = {"env_prefix": "AICOPH_", "env_file": ".env", "extra": "ignore"}

    llm_backend: LLMBackend = Field(default="ollama", description="LLM backend: ollama, claude, gemini")
    llm_model: str = Field(default="", description="LLM model name")
    llm_api_key: str = Field(default="", description="LLM API key")
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)

    allow_external_search: bool = Field(default=False, description="Allow external search APIs")
    allow_external_agents: bool = Field(default=False, description="Allow external agent integration")
    consent_required: bool = Field(default=True, description="Require consent for external services")

    workspace_dir: str = Field(default="~/.aicophilosopher", description="Workspace root directory")
    log_level: str = Field(default="INFO", description="Log level: DEBUG, INFO, WARNING, ERROR")
    project_dir: str = Field(default="", description="Override project directory")

    hermes_enabled: bool = Field(default=False, description="Enable Hermes Agent bridge")
    opencode_enabled: bool = Field(default=False, description="Enable OpenCode Go bridge")

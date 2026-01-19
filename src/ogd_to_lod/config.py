"""Configuration management with environment variable support."""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv


@dataclass
class GitHubConfig:
    """GitHub configuration."""

    repo: str
    token: str


@dataclass
class AzureOpenAIConfig:
    """Azure OpenAI configuration."""

    endpoint: str
    api_key: str
    deployment: str
    api_version: str = "2024-02-15-preview"


@dataclass
class SPARQLConfig:
    """SPARQL endpoint configuration."""

    endpoint: str | None = None


@dataclass
class RMLConfig:
    """RML generation configuration."""

    base_uri: str = ""


@dataclass
class Config:
    """Main application configuration."""

    github: GitHubConfig
    azure: AzureOpenAIConfig
    sparql: SPARQLConfig = field(default_factory=SPARQLConfig)
    rml: RMLConfig = field(default_factory=RMLConfig)


def _substitute_env_vars(value: str) -> str:
    """Substitute ${VAR} or $VAR patterns with environment variables.

    Args:
        value: String potentially containing environment variable references.

    Returns:
        String with environment variables substituted.

    Raises:
        ValueError: If a referenced environment variable is not set.
    """
    pattern = r"\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)"

    def replacer(match: re.Match) -> str:
        var_name = match.group(1) or match.group(2)
        env_value = os.environ.get(var_name)
        if env_value is None:
            raise ValueError(f"Environment variable '{var_name}' is not set")
        return env_value

    return re.sub(pattern, replacer, value)


def _process_config_values(obj: dict | list | str) -> dict | list | str:
    """Recursively process config values, substituting environment variables.

    Args:
        obj: Configuration object (dict, list, or string).

    Returns:
        Processed configuration with environment variables substituted.
    """
    if isinstance(obj, dict):
        return {k: _process_config_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_process_config_values(item) for item in obj]
    elif isinstance(obj, str):
        return _substitute_env_vars(obj)
    return obj


def load_config(config_path: str | Path) -> Config:
    """Load configuration from YAML file with environment variable substitution.

    Args:
        config_path: Path to the configuration YAML file.

    Returns:
        Loaded and validated configuration.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        ValueError: If required configuration values are missing or invalid.
    """
    # Load environment variables from .env file if present
    load_dotenv()

    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path) as f:
        raw_config = yaml.safe_load(f)

    if raw_config is None:
        raise ValueError("Configuration file is empty")

    # Substitute environment variables
    config_data = _process_config_values(raw_config)

    # Validate and construct config objects
    try:
        github_data = config_data.get("github", {})
        github = GitHubConfig(
            repo=github_data.get("repo", ""),
            token=github_data.get("token", ""),
        )
        if not github.repo:
            raise ValueError("github.repo is required")
        if not github.token:
            raise ValueError("github.token is required")

        azure_data = config_data.get("azure", {})
        azure = AzureOpenAIConfig(
            endpoint=azure_data.get("endpoint", ""),
            api_key=azure_data.get("api_key", ""),
            deployment=azure_data.get("deployment", ""),
            api_version=azure_data.get("api_version", "2024-02-15-preview"),
        )
        if not azure.endpoint:
            raise ValueError("azure.endpoint is required")
        if not azure.api_key:
            raise ValueError("azure.api_key is required")
        if not azure.deployment:
            raise ValueError("azure.deployment is required")

        sparql_data = config_data.get("sparql", {})
        sparql = SPARQLConfig(
            endpoint=sparql_data.get("endpoint"),
        )

        rml_data = config_data.get("rml", {})
        rml = RMLConfig(
            base_uri=rml_data.get("base_uri", ""),
        )

        return Config(
            github=github,
            azure=azure,
            sparql=sparql,
            rml=rml,
        )

    except KeyError as e:
        raise ValueError(f"Missing required configuration key: {e}")

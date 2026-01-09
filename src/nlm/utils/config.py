"""Configuration management for NLM CLI."""

import os
from pathlib import Path
from typing import Any

from platformdirs import user_config_dir, user_data_dir
from pydantic import BaseModel, Field


class OutputConfig(BaseModel):
    """Output formatting configuration."""

    format: str = Field(default="table", description="Default output format: table, json, compact")
    color: bool = Field(default=True, description="Enable colored output")
    short_ids: bool = Field(default=True, description="Show abbreviated IDs by default")


class AuthConfig(BaseModel):
    """Authentication configuration."""

    browser: str = Field(default="auto", description="Browser for auth: auto, chrome, firefox, safari, edge, brave")
    default_profile: str = Field(default="default", description="Default profile name")


class Config(BaseModel):
    """Main configuration model."""

    output: OutputConfig = Field(default_factory=OutputConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)


def get_config_dir() -> Path:
    """Get the configuration directory path."""
    # Check for environment override
    if env_path := os.environ.get("NLM_CONFIG_PATH"):
        return Path(env_path)
    # Use platformdirs for cross-platform support
    return Path(user_config_dir("nlm", ensure_exists=True))


def get_data_dir() -> Path:
    """Get the data directory path (for profiles/credentials)."""
    if env_path := os.environ.get("NLM_PROFILE_PATH"):
        return Path(env_path)
    return Path(user_data_dir("nlm", ensure_exists=True))


def get_profiles_dir() -> Path:
    """Get the profiles directory path."""
    return get_data_dir() / "profiles"


def get_profile_dir(profile_name: str = "default") -> Path:
    """Get directory for a specific profile."""
    return get_profiles_dir() / profile_name


def get_config_file() -> Path:
    """Get the config file path."""
    return get_config_dir() / "config.toml"


def load_config() -> Config:
    """Load configuration from file and environment."""
    config_file = get_config_file()
    config_data: dict[str, Any] = {}
    
    # Load from file if exists
    if config_file.exists():
        try:
            import tomllib
            with open(config_file, "rb") as f:
                config_data = tomllib.load(f)
        except Exception:
            pass  # Use defaults on error
    
    # Apply environment overrides
    if output_format := os.environ.get("NLM_OUTPUT_FORMAT"):
        config_data.setdefault("output", {})["format"] = output_format
    
    if os.environ.get("NLM_NO_COLOR"):
        config_data.setdefault("output", {})["color"] = False
    
    if browser := os.environ.get("NLM_BROWSER"):
        config_data.setdefault("auth", {})["browser"] = browser
    
    if profile := os.environ.get("NLM_PROFILE"):
        config_data.setdefault("auth", {})["default_profile"] = profile
    
    return Config(**config_data)


def save_config(config: Config) -> None:
    """Save configuration to file."""
    config_file = get_config_file()
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to TOML format
    toml_content = _config_to_toml(config)
    config_file.write_text(toml_content)


def _config_to_toml(config: Config) -> str:
    """Convert config model to TOML string."""
    lines = []
    
    lines.append("[output]")
    lines.append(f'format = "{config.output.format}"')
    lines.append(f'color = {"true" if config.output.color else "false"}')
    lines.append(f'short_ids = {"true" if config.output.short_ids else "false"}')
    lines.append("")
    
    lines.append("[auth]")
    lines.append(f'browser = "{config.auth.browser}"')
    lines.append(f'default_profile = "{config.auth.default_profile}"')
    lines.append("")
    
    return "\n".join(lines)


# Global config instance (lazy loaded)
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reset_config() -> None:
    """Reset the global configuration (for testing)."""
    global _config
    _config = None

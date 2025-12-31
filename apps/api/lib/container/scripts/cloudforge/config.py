# apps/api/sandbox-modules/cloudforge/config.py
"""
Configuration management for CloudForge sandbox operations.
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


@dataclass
class Config:
    """CloudForge configuration loaded from environment variables."""
    
    # Cloudflare
    cloudflare_api_token: str = field(default_factory=lambda: os.environ.get("CLOUDFLARE_API_TOKEN", ""))
    cloudflare_account_id: str = field(default_factory=lambda: os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""))
    
    # GitHub
    github_token: str = field(default_factory=lambda: os.environ.get("GITHUB_TOKEN", ""))
    github_org: str = field(default_factory=lambda: os.environ.get("GITHUB_ORG", ""))
    
    # Starter Kit
    starter_kit_repo: str = "jmbish04/core-react-starter-kit"
    starter_kit_branch: str = "main"
    
    # Workspace
    workspace_dir: Path = field(default_factory=lambda: Path("/workspace"))
    temp_dir: Path = field(default_factory=lambda: Path("/tmp/cloudforge"))
    log_dir: Path = field(default_factory=lambda: Path("/var/log/cloudforge"))
    
    # Build settings
    node_version: str = "20"
    pnpm_version: str = "9"
    
    # Timeouts (seconds)
    git_timeout: int = 120
    npm_timeout: int = 300
    build_timeout: int = 600
    deploy_timeout: int = 300
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self.workspace_dir = Path(self.workspace_dir)
        self.temp_dir = Path(self.temp_dir)
        self.log_dir = Path(self.log_dir)
        
        # Create directories if they don't exist
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def validate(self) -> list[str]:
        """Validate required configuration values."""
        errors = []
        
        if not self.cloudflare_api_token:
            errors.append("CLOUDFLARE_API_TOKEN is required")
        if not self.cloudflare_account_id:
            errors.append("CLOUDFLARE_ACCOUNT_ID is required")
        if not self.github_token:
            errors.append("GITHUB_TOKEN is required")
        if not self.github_org:
            errors.append("GITHUB_ORG is required")
            
        return errors
    
    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        return cls()


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config

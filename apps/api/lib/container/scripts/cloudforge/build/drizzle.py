# apps/api/sandbox-modules/cloudforge/build/drizzle.py
"""
Drizzle ORM operations.
"""

from pathlib import Path
from typing import Optional
import structlog

from cloudforge.config import get_config
from cloudforge.utils.shell import Shell

logger = structlog.get_logger(__name__)


class DrizzleRunner:
    """Runs Drizzle Kit commands."""
    
    def __init__(self):
        """Initialize Drizzle runner."""
        self.config = get_config()
        self.shell = Shell()
    
    def generate(
        self,
        cwd: Path,
        config_path: Optional[str] = None,
    ) -> str:
        """
        Generate SQL migrations from schema.
        
        Returns:
            Command output
        """
        logger.info("Generating Drizzle migrations", cwd=str(cwd))
        
        cmd = ["drizzle-kit", "generate"]
        if config_path:
            cmd.extend(["--config", config_path])
        
        result = self.shell.run(
            cmd,
            cwd=cwd,
            capture_output=True,
        )
        
        return result.stdout
    
    def migrate(
        self,
        cwd: Path,
        config_path: Optional[str] = None,
    ) -> str:
        """
        Run migrations.
        
        Returns:
            Command output
        """
        logger.info("Running Drizzle migrations", cwd=str(cwd))
        
        cmd = ["drizzle-kit", "migrate"]
        if config_path:
            cmd.extend(["--config", config_path])
        
        result = self.shell.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            env={
                "CLOUDFLARE_API_TOKEN": self.config.cloudflare_api_token,
                "CLOUDFLARE_ACCOUNT_ID": self.config.cloudflare_account_id,
            },
        )
        
        return result.stdout
    
    def push(
        self,
        cwd: Path,
        config_path: Optional[str] = None,
    ) -> str:
        """
        Push schema changes directly (no migration files).
        
        Returns:
            Command output
        """
        logger.info("Pushing Drizzle schema", cwd=str(cwd))
        
        cmd = ["drizzle-kit", "push"]
        if config_path:
            cmd.extend(["--config", config_path])
        
        result = self.shell.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            env={
                "CLOUDFLARE_API_TOKEN": self.config.cloudflare_api_token,
                "CLOUDFLARE_ACCOUNT_ID": self.config.cloudflare_account_id,
            },
        )
        
        return result.stdout
    
    def studio(
        self,
        cwd: Path,
        port: int = 4983,
    ) -> None:
        """Start Drizzle Studio (non-blocking)."""
        logger.info("Starting Drizzle Studio", cwd=str(cwd), port=port)
        
        self.shell.run_background(
            ["drizzle-kit", "studio", "--port", str(port)],
            cwd=cwd,
        )

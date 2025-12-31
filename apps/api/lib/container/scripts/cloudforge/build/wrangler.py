# apps/api/sandbox-modules/cloudforge/build/wrangler.py
"""
Wrangler CLI operations.
"""

from pathlib import Path
from typing import Optional, Dict, Any
import json
import structlog

from cloudforge.config import get_config
from cloudforge.utils.shell import Shell

logger = structlog.get_logger(__name__)


class WranglerRunner:
    """Runs wrangler CLI commands."""
    
    def __init__(self):
        """Initialize Wrangler runner."""
        self.config = get_config()
        self.shell = Shell()
    
    def deploy(
        self,
        cwd: Path,
        env: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Deploy a worker.
        
        Returns:
            Deployment info with 'url', 'version_id'
        """
        logger.info("Deploying worker", cwd=str(cwd), env=env)
        
        cmd = ["wrangler", "deploy", "--json"]
        if env:
            cmd.extend(["--env", env])
        
        result = self.shell.run(
            cmd,
            cwd=cwd,
            timeout=self.config.deploy_timeout,
            capture_output=True,
            env={
                "CLOUDFLARE_API_TOKEN": self.config.cloudflare_api_token,
                "CLOUDFLARE_ACCOUNT_ID": self.config.cloudflare_account_id,
            },
        )
        
        try:
            deployment = json.loads(result.stdout)
            logger.info("Worker deployed", url=deployment.get("url"))
            return deployment
        except json.JSONDecodeError:
            logger.error("Failed to parse deployment output", output=result.stdout)
            return {"output": result.stdout}
    
    def dev(
        self,
        cwd: Path,
        port: int = 8787,
    ) -> None:
        """Start local development server (non-blocking)."""
        logger.info("Starting dev server", cwd=str(cwd), port=port)
        
        self.shell.run_background(
            ["wrangler", "dev", "--port", str(port)],
            cwd=cwd,
        )
    
    def tail(
        self,
        cwd: Path,
        script_name: Optional[str] = None,
    ) -> str:
        """Get worker logs."""
        cmd = ["wrangler", "tail", "--format", "json"]
        if script_name:
            cmd.append(script_name)
        
        result = self.shell.run(
            cmd,
            cwd=cwd,
            timeout=30,
            capture_output=True,
        )
        
        return result.stdout
    
    def whoami(self) -> Dict[str, Any]:
        """Get current authentication info."""
        result = self.shell.run(
            ["wrangler", "whoami"],
            capture_output=True,
            env={
                "CLOUDFLARE_API_TOKEN": self.config.cloudflare_api_token,
            },
        )
        
        return {"output": result.stdout}

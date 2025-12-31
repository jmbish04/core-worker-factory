# apps/api/sandbox-modules/cloudforge/build/npm.py
"""
NPM/PNPM build operations.
"""

from pathlib import Path
from typing import Optional, List
import structlog

from cloudforge.config import get_config
from cloudforge.utils.shell import Shell

logger = structlog.get_logger(__name__)


class NPMRunner:
    """Runs npm/pnpm commands."""
    
    def __init__(self, use_pnpm: bool = True):
        """Initialize NPM runner."""
        self.config = get_config()
        self.shell = Shell()
        self.package_manager = "pnpm" if use_pnpm else "npm"
    
    def install(
        self,
        cwd: Path,
        frozen_lockfile: bool = False,
    ) -> None:
        """Install dependencies."""
        logger.info("Installing dependencies", cwd=str(cwd), pm=self.package_manager)
        
        cmd = [self.package_manager, "install"]
        if frozen_lockfile and self.package_manager == "pnpm":
            cmd.append("--frozen-lockfile")
        
        self.shell.run(cmd, cwd=cwd, timeout=self.config.npm_timeout)
    
    def run_script(
        self,
        cwd: Path,
        script: str,
        args: Optional[List[str]] = None,
    ) -> str:
        """
        Run an npm script.
        
        Returns:
            Command output
        """
        logger.info("Running script", script=script, cwd=str(cwd))
        
        cmd = [self.package_manager, "run", script]
        if args:
            cmd.extend(args)
        
        result = self.shell.run(
            cmd,
            cwd=cwd,
            timeout=self.config.build_timeout,
            capture_output=True,
        )
        
        return result.stdout
    
    def build(self, cwd: Path) -> str:
        """Run the build script."""
        return self.run_script(cwd, "build")
    
    def typecheck(self, cwd: Path) -> str:
        """Run TypeScript type checking."""
        return self.run_script(cwd, "typecheck")
    
    def lint(self, cwd: Path) -> str:
        """Run linting."""
        return self.run_script(cwd, "lint")
    
    def test(self, cwd: Path) -> str:
        """Run tests."""
        return self.run_script(cwd, "test")
    
    def add_dependency(
        self,
        cwd: Path,
        package: str,
        dev: bool = False,
    ) -> None:
        """Add a dependency."""
        logger.info("Adding dependency", package=package, dev=dev)
        
        cmd = [self.package_manager, "add", package]
        if dev:
            cmd.append("-D")
        
        self.shell.run(cmd, cwd=cwd, timeout=self.config.npm_timeout)

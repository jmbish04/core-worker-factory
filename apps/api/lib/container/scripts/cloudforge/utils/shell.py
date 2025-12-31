# apps/api/sandbox-modules/cloudforge/utils/shell.py
"""
Shell command execution utilities.
"""

import subprocess
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ShellResult:
    """Result of a shell command execution."""
    returncode: int
    stdout: str
    stderr: str
    
    @property
    def success(self) -> bool:
        return self.returncode == 0


class ShellError(Exception):
    """Raised when a shell command fails."""
    
    def __init__(self, message: str, result: ShellResult):
        super().__init__(message)
        self.result = result


class Shell:
    """Executes shell commands safely."""
    
    def __init__(self, default_timeout: int = 60):
        """Initialize shell executor."""
        self.default_timeout = default_timeout
    
    def run(
        self,
        cmd: List[str],
        cwd: Optional[Path] = None,
        timeout: Optional[int] = None,
        capture_output: bool = False,
        env: Optional[Dict[str, str]] = None,
        check: bool = True,
    ) -> ShellResult:
        """
        Run a shell command.
        
        Args:
            cmd: Command and arguments
            cwd: Working directory
            timeout: Command timeout in seconds
            capture_output: Whether to capture stdout/stderr
            env: Additional environment variables
            check: Whether to raise on non-zero exit
            
        Returns:
            ShellResult with returncode, stdout, stderr
            
        Raises:
            ShellError: If check=True and command fails
        """
        timeout = timeout or self.default_timeout
        
        # Merge environment
        full_env = os.environ.copy()
        if env:
            full_env.update(env)
        
        logger.debug("Running command", cmd=cmd, cwd=str(cwd) if cwd else None)
        
        try:
            process = subprocess.run(
                cmd,
                cwd=cwd,
                timeout=timeout,
                capture_output=True,
                text=True,
                env=full_env,
            )
            
            result = ShellResult(
                returncode=process.returncode,
                stdout=process.stdout,
                stderr=process.stderr,
            )
            
            if check and not result.success:
                raise ShellError(
                    f"Command failed with exit code {result.returncode}: {' '.join(cmd)}",
                    result,
                )
            
            return result
            
        except subprocess.TimeoutExpired as e:
            raise ShellError(
                f"Command timed out after {timeout}s: {' '.join(cmd)}",
                ShellResult(returncode=-1, stdout="", stderr=str(e)),
            )
    
    def run_background(
        self,
        cmd: List[str],
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> subprocess.Popen:
        """
        Run a command in the background.
        
        Returns:
            Popen process object
        """
        full_env = os.environ.copy()
        if env:
            full_env.update(env)
        
        logger.debug("Running background command", cmd=cmd)
        
        return subprocess.Popen(
            cmd,
            cwd=cwd,
            env=full_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    
    def which(self, program: str) -> Optional[str]:
        """Find a program in PATH."""
        result = self.run(
            ["which", program],
            check=False,
            capture_output=True,
        )
        
        if result.success:
            return result.stdout.strip()
        return None

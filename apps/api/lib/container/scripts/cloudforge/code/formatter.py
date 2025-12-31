# apps/api/sandbox-modules/cloudforge/code/formatter.py
"""
Code formatting utilities.
"""

from pathlib import Path
from typing import Optional
import structlog

from cloudforge.utils.shell import Shell

logger = structlog.get_logger(__name__)


class CodeFormatter:
    """Utilities for formatting code."""
    
    def __init__(self):
        """Initialize code formatter."""
        self.shell = Shell()
    
    def format_prettier(
        self,
        path: Path,
        write: bool = True,
    ) -> str:
        """
        Format file(s) with Prettier.
        
        Args:
            path: File or directory to format
            write: Whether to write changes
            
        Returns:
            Prettier output
        """
        cmd = ["prettier"]
        if write:
            cmd.append("--write")
        cmd.append(str(path))
        
        result = self.shell.run(cmd, capture_output=True, check=False)
        return result.stdout
    
    def format_eslint(
        self,
        path: Path,
        fix: bool = True,
    ) -> str:
        """
        Format/lint file(s) with ESLint.
        
        Args:
            path: File or directory to lint
            fix: Whether to fix auto-fixable issues
            
        Returns:
            ESLint output
        """
        cmd = ["eslint"]
        if fix:
            cmd.append("--fix")
        cmd.append(str(path))
        
        result = self.shell.run(cmd, capture_output=True, check=False)
        return result.stdout
    
    def format_project(
        self,
        project_path: Path,
        write: bool = True,
    ) -> None:
        """Format entire project with available formatters."""
        logger.info("Formatting project", path=str(project_path))
        
        # Try Prettier first
        try:
            self.format_prettier(project_path / "src", write=write)
        except Exception as e:
            logger.warning("Prettier formatting failed", error=str(e))
        
        # Then ESLint
        try:
            self.format_eslint(project_path / "src", fix=write)
        except Exception as e:
            logger.warning("ESLint formatting failed", error=str(e))

# apps/api/sandbox-modules/cloudforge/code/generator.py
"""
Code generation utilities.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import structlog

from cloudforge.utils.files import FileManager

logger = structlog.get_logger(__name__)


@dataclass
class GeneratedFile:
    """Represents a generated code file."""
    path: str
    content: str
    language: str = "typescript"
    overwrite: bool = True


@dataclass
class CodeChangeSet:
    """A set of code changes to apply."""
    files: List[GeneratedFile]
    commit_message: str
    description: str = ""


class CodeGenerator:
    """Utilities for generating and applying code."""
    
    def __init__(self, workspace_dir: Optional[Path] = None):
        """Initialize code generator."""
        self.workspace_dir = workspace_dir or Path("/workspace")
        self.file_manager = FileManager(self.workspace_dir)
    
    def apply_changes(
        self,
        repo_path: Path,
        changes: CodeChangeSet,
    ) -> List[str]:
        """
        Apply a set of code changes to a repository.
        
        Returns:
            List of file paths that were changed
        """
        changed_files = []
        
        for file in changes.files:
            full_path = repo_path / file.path
            
            # Check if file exists and overwrite is False
            if full_path.exists() and not file.overwrite:
                logger.info("Skipping existing file", path=file.path)
                continue
            
            logger.info("Writing file", path=file.path, size=len(file.content))
            self.file_manager.write(full_path, file.content)
            changed_files.append(file.path)
        
        return changed_files
    
    def create_file(
        self,
        path: str,
        content: str,
        language: str = "typescript",
    ) -> GeneratedFile:
        """Create a GeneratedFile object."""
        return GeneratedFile(
            path=path,
            content=content,
            language=language,
        )
    
    def create_changeset(
        self,
        files: List[GeneratedFile],
        commit_message: str,
        description: str = "",
    ) -> CodeChangeSet:
        """Create a CodeChangeSet object."""
        return CodeChangeSet(
            files=files,
            commit_message=commit_message,
            description=description,
        )
    
    @staticmethod
    def indent(content: str, spaces: int = 2) -> str:
        """Indent all lines in content."""
        indent_str = " " * spaces
        lines = content.split("\n")
        return "\n".join(indent_str + line if line.strip() else line for line in lines)
    
    @staticmethod
    def wrap_in_function(
        name: str,
        content: str,
        params: str = "",
        return_type: str = "void",
        async_fn: bool = False,
    ) -> str:
        """Wrap content in a function declaration."""
        async_prefix = "async " if async_fn else ""
        return f"""{async_prefix}function {name}({params}): {return_type} {{
{CodeGenerator.indent(content)}
}}"""
    
    @staticmethod
    def create_import(
        module: str,
        imports: List[str],
        type_only: bool = False,
    ) -> str:
        """Create an import statement."""
        type_prefix = "type " if type_only else ""
        imports_str = ", ".join(imports)
        return f"import {type_prefix}{{ {imports_str} }} from '{module}';"

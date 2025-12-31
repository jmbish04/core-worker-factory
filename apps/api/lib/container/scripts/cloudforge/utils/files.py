# apps/api/sandbox-modules/cloudforge/utils/files.py
"""
File management utilities.
"""

import os
import shutil
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
import structlog

logger = structlog.get_logger(__name__)


class FileManager:
    """Manages file operations."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize file manager."""
        self.base_dir = base_dir or Path("/workspace")
    
    def read(self, path: Union[str, Path]) -> str:
        """Read a file as text."""
        full_path = self._resolve_path(path)
        logger.debug("Reading file", path=str(full_path))
        return full_path.read_text()
    
    def read_json(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Read a JSON file."""
        content = self.read(path)
        return json.loads(content)
    
    def write(self, path: Union[str, Path], content: str) -> None:
        """Write text to a file."""
        full_path = self._resolve_path(path)
        logger.debug("Writing file", path=str(full_path), size=len(content))
        
        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
    
    def write_json(
        self,
        path: Union[str, Path],
        data: Dict[str, Any],
        indent: int = 2,
    ) -> None:
        """Write data as JSON to a file."""
        content = json.dumps(data, indent=indent)
        self.write(path, content)
    
    def append(self, path: Union[str, Path], content: str) -> None:
        """Append text to a file."""
        full_path = self._resolve_path(path)
        logger.debug("Appending to file", path=str(full_path), size=len(content))
        
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "a") as f:
            f.write(content)
    
    def delete(self, path: Union[str, Path]) -> None:
        """Delete a file."""
        full_path = self._resolve_path(path)
        logger.debug("Deleting file", path=str(full_path))
        
        if full_path.exists():
            full_path.unlink()
    
    def delete_dir(self, path: Union[str, Path]) -> None:
        """Delete a directory and all contents."""
        full_path = self._resolve_path(path)
        logger.debug("Deleting directory", path=str(full_path))
        
        if full_path.exists():
            shutil.rmtree(full_path)
    
    def copy(
        self,
        src: Union[str, Path],
        dest: Union[str, Path],
    ) -> None:
        """Copy a file."""
        src_path = self._resolve_path(src)
        dest_path = self._resolve_path(dest)
        
        logger.debug("Copying file", src=str(src_path), dest=str(dest_path))
        
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dest_path)
    
    def copy_dir(
        self,
        src: Union[str, Path],
        dest: Union[str, Path],
    ) -> None:
        """Copy a directory."""
        src_path = self._resolve_path(src)
        dest_path = self._resolve_path(dest)
        
        logger.debug("Copying directory", src=str(src_path), dest=str(dest_path))
        
        shutil.copytree(src_path, dest_path)
    
    def move(
        self,
        src: Union[str, Path],
        dest: Union[str, Path],
    ) -> None:
        """Move a file or directory."""
        src_path = self._resolve_path(src)
        dest_path = self._resolve_path(dest)
        
        logger.debug("Moving", src=str(src_path), dest=str(dest_path))
        
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(src_path, dest_path)
    
    def exists(self, path: Union[str, Path]) -> bool:
        """Check if a path exists."""
        return self._resolve_path(path).exists()
    
    def is_file(self, path: Union[str, Path]) -> bool:
        """Check if path is a file."""
        return self._resolve_path(path).is_file()
    
    def is_dir(self, path: Union[str, Path]) -> bool:
        """Check if path is a directory."""
        return self._resolve_path(path).is_dir()
    
    def list_dir(
        self,
        path: Union[str, Path],
        pattern: str = "*",
        recursive: bool = False,
    ) -> List[Path]:
        """List directory contents."""
        full_path = self._resolve_path(path)
        
        if recursive:
            return list(full_path.rglob(pattern))
        return list(full_path.glob(pattern))
    
    def mkdir(self, path: Union[str, Path], parents: bool = True) -> None:
        """Create a directory."""
        full_path = self._resolve_path(path)
        logger.debug("Creating directory", path=str(full_path))
        full_path.mkdir(parents=parents, exist_ok=True)
    
    def _resolve_path(self, path: Union[str, Path]) -> Path:
        """Resolve a path relative to base_dir if not absolute."""
        path = Path(path)
        if path.is_absolute():
            return path
        return self.base_dir / path

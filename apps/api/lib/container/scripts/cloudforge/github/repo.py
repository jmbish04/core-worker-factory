# apps/api/sandbox-modules/cloudforge/github/repo.py
"""
Repository management operations.
"""

import subprocess
import shutil
from pathlib import Path
from typing import Optional, List
import structlog

from cloudforge.config import get_config
from cloudforge.github.client import GitHubClient
from cloudforge.utils.shell import Shell

logger = structlog.get_logger(__name__)


class RepoManager:
    """Manages repository operations for worker builds."""
    
    def __init__(self, github_client: Optional[GitHubClient] = None):
        """Initialize repo manager."""
        self.config = get_config()
        self.github = github_client or GitHubClient()
        self.shell = Shell()
    
    def clone_repo(
        self,
        repo_url: str,
        target_dir: Path,
        branch: str = "main",
        depth: int = 1,
    ) -> Path:
        """Clone a repository to the target directory."""
        logger.info("Cloning repository", url=repo_url, target=str(target_dir), branch=branch)
        
        # Ensure target parent exists
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        
        # Remove target if it exists
        if target_dir.exists():
            shutil.rmtree(target_dir)
        
        # Clone with authentication
        auth_url = self._add_auth_to_url(repo_url)
        
        cmd = [
            "git", "clone",
            "--branch", branch,
            "--depth", str(depth),
            "--single-branch",
            auth_url,
            str(target_dir)
        ]
        
        self.shell.run(cmd, timeout=self.config.git_timeout)
        
        return target_dir
    
    def create_worker_repo(
        self,
        worker_name: str,
        description: str = "",
    ) -> tuple[str, Path]:
        """
        Create a new worker repository by forking the starter kit.
        
        Returns:
            Tuple of (repo_url, local_path)
        """
        logger.info("Creating worker repository", worker_name=worker_name)
        
        # Check if repo already exists
        if self.github.repo_exists(worker_name):
            logger.warning("Repository already exists, using existing", repo=worker_name)
            repo = self.github.get_repo(worker_name)
        else:
            # Fork starter kit
            repo = self.github.fork_repo(
                source_repo=self.config.starter_kit_repo,
                new_name=worker_name,
            )
            
            # Update description
            if description:
                repo.edit(description=description)
        
        # Clone locally
        repo_url = repo.clone_url
        local_path = self.config.workspace_dir / worker_name
        
        self.clone_repo(repo_url, local_path)
        
        # Update remote to use authenticated URL
        self._setup_remote(local_path, repo_url)
        
        return repo_url, local_path
    
    def commit_and_push(
        self,
        repo_path: Path,
        message: str,
        branch: str = "main",
        files: Optional[List[str]] = None,
    ) -> str:
        """
        Commit changes and push to remote.
        
        Args:
            repo_path: Path to the repository
            message: Commit message
            branch: Branch to push to
            files: Specific files to add (None = all)
            
        Returns:
            Commit SHA
        """
        logger.info("Committing and pushing", path=str(repo_path), message=message[:50])
        
        # Stage files
        if files:
            for f in files:
                self.shell.run(["git", "add", f], cwd=repo_path)
        else:
            self.shell.run(["git", "add", "-A"], cwd=repo_path)
        
        # Check if there are changes to commit
        result = self.shell.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
        )
        
        if not result.stdout.strip():
            logger.info("No changes to commit")
            # Get current commit SHA
            result = self.shell.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path,
                capture_output=True,
            )
            return result.stdout.strip()
        
        # Commit
        self.shell.run(
            ["git", "commit", "-m", message],
            cwd=repo_path,
        )
        
        # Push
        self.shell.run(
            ["git", "push", "origin", branch],
            cwd=repo_path,
            timeout=self.config.git_timeout,
        )
        
        # Get commit SHA
        result = self.shell.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
        )
        
        return result.stdout.strip()
    
    def create_branch(
        self,
        repo_path: Path,
        branch_name: str,
        base_branch: str = "main",
    ) -> None:
        """Create and checkout a new branch."""
        logger.info("Creating branch", branch=branch_name, base=base_branch)
        
        # Fetch latest
        self.shell.run(["git", "fetch", "origin"], cwd=repo_path)
        
        # Create and checkout branch
        self.shell.run(
            ["git", "checkout", "-b", branch_name, f"origin/{base_branch}"],
            cwd=repo_path,
        )
    
    def _add_auth_to_url(self, url: str) -> str:
        """Add authentication token to Git URL."""
        if url.startswith("https://"):
            # Insert token after https://
            return url.replace(
                "https://",
                f"https://x-access-token:{self.config.github_token}@"
            )
        return url
    
    def _setup_remote(self, repo_path: Path, url: str) -> None:
        """Setup remote with authentication."""
        auth_url = self._add_auth_to_url(url)
        self.shell.run(
            ["git", "remote", "set-url", "origin", auth_url],
            cwd=repo_path,
        )

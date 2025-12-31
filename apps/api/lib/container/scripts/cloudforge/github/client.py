# apps/api/sandbox-modules/cloudforge/github/client.py
"""
GitHub API client wrapper.
"""

from github import Github, GithubException
from github.Repository import Repository
from github.Organization import Organization
from typing import Optional
import structlog

from cloudforge.config import get_config

logger = structlog.get_logger(__name__)


class GitHubClient:
    """Wrapper for GitHub API operations."""
    
    def __init__(self, token: Optional[str] = None):
        """Initialize GitHub client."""
        config = get_config()
        self.token = token or config.github_token
        self.org_name = config.github_org
        self._client: Optional[Github] = None
        self._org: Optional[Organization] = None
    
    @property
    def client(self) -> Github:
        """Get or create GitHub client."""
        if self._client is None:
            self._client = Github(self.token)
        return self._client
    
    @property
    def org(self) -> Organization:
        """Get organization."""
        if self._org is None:
            self._org = self.client.get_organization(self.org_name)
        return self._org
    
    def get_repo(self, repo_name: str) -> Repository:
        """Get a repository by name."""
        full_name = f"{self.org_name}/{repo_name}"
        logger.info("Fetching repository", repo=full_name)
        return self.client.get_repo(full_name)
    
    def repo_exists(self, repo_name: str) -> bool:
        """Check if a repository exists."""
        try:
            self.get_repo(repo_name)
            return True
        except GithubException as e:
            if e.status == 404:
                return False
            raise
    
    def create_repo(
        self,
        name: str,
        description: str = "",
        private: bool = True,
        auto_init: bool = False,
    ) -> Repository:
        """Create a new repository in the organization."""
        logger.info("Creating repository", name=name, org=self.org_name)
        
        return self.org.create_repo(
            name=name,
            description=description,
            private=private,
            auto_init=auto_init,
            has_issues=True,
            has_wiki=False,
            has_downloads=False,
            has_projects=False,
        )
    
    def fork_repo(self, source_repo: str, new_name: str) -> Repository:
        """Fork a repository to the organization with a new name."""
        logger.info("Forking repository", source=source_repo, target=new_name)
        
        source = self.client.get_repo(source_repo)
        
        # Fork to organization
        forked = self.org.create_fork(source)
        
        # Rename if different
        if forked.name != new_name:
            forked.edit(name=new_name)
        
        return self.get_repo(new_name)
    
    def delete_repo(self, repo_name: str) -> None:
        """Delete a repository."""
        logger.warning("Deleting repository", repo=repo_name)
        repo = self.get_repo(repo_name)
        repo.delete()

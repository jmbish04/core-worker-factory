# apps/api/sandbox-modules/cloudforge/github/pr.py
"""
Pull request management operations.
"""

from typing import Optional, List, Dict, Any
from github import GithubException
from github.PullRequest import PullRequest
import structlog

from cloudforge.github.client import GitHubClient

logger = structlog.get_logger(__name__)


class PRManager:
    """Manages pull request operations."""
    
    def __init__(self, github_client: Optional[GitHubClient] = None):
        """Initialize PR manager."""
        self.github = github_client or GitHubClient()
    
    def create_pr(
        self,
        repo_name: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
        draft: bool = False,
    ) -> PullRequest:
        """Create a new pull request."""
        logger.info(
            "Creating pull request",
            repo=repo_name,
            title=title,
            head=head_branch,
            base=base_branch,
        )
        
        repo = self.github.get_repo(repo_name)
        
        pr = repo.create_pull(
            title=title,
            body=body,
            head=head_branch,
            base=base_branch,
            draft=draft,
        )
        
        logger.info("Pull request created", pr_number=pr.number, url=pr.html_url)
        return pr
    
    def get_pr(self, repo_name: str, pr_number: int) -> PullRequest:
        """Get a pull request by number."""
        repo = self.github.get_repo(repo_name)
        return repo.get_pull(pr_number)
    
    def list_open_prs(self, repo_name: str) -> List[PullRequest]:
        """List all open pull requests."""
        repo = self.github.get_repo(repo_name)
        return list(repo.get_pulls(state="open"))
    
    def get_pr_comments(self, repo_name: str, pr_number: int) -> List[Dict[str, Any]]:
        """
        Get all comments on a pull request including review comments.
        
        Returns list of comments with structure:
        {
            "type": "issue_comment" | "review_comment",
            "body": str,
            "user": str,
            "created_at": str,
            "path": str | None,  # For review comments
            "line": int | None,  # For review comments
        }
        """
        repo = self.github.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        
        comments = []
        
        # Issue comments (general PR comments)
        for comment in pr.get_issue_comments():
            comments.append({
                "type": "issue_comment",
                "body": comment.body,
                "user": comment.user.login,
                "created_at": comment.created_at.isoformat(),
                "path": None,
                "line": None,
            })
        
        # Review comments (inline code comments)
        for comment in pr.get_review_comments():
            comments.append({
                "type": "review_comment",
                "body": comment.body,
                "user": comment.user.login,
                "created_at": comment.created_at.isoformat(),
                "path": comment.path,
                "line": comment.line,
            })
        
        # Sort by created_at
        comments.sort(key=lambda c: c["created_at"])
        
        return comments
    
    def add_comment(
        self,
        repo_name: str,
        pr_number: int,
        body: str,
    ) -> None:
        """Add a comment to a pull request."""
        repo = self.github.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        pr.create_issue_comment(body)
        logger.info("Comment added to PR", pr_number=pr_number)
    
    def merge_pr(
        self,
        repo_name: str,
        pr_number: int,
        merge_method: str = "squash",
        commit_message: Optional[str] = None,
    ) -> bool:
        """
        Merge a pull request.
        
        Args:
            repo_name: Repository name
            pr_number: PR number
            merge_method: "merge", "squash", or "rebase"
            commit_message: Custom commit message (optional)
            
        Returns:
            True if merged successfully
        """
        repo = self.github.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        
        try:
            result = pr.merge(
                merge_method=merge_method,
                commit_message=commit_message,
            )
            logger.info("PR merged", pr_number=pr_number, sha=result.sha)
            return True
        except GithubException as e:
            logger.error("Failed to merge PR", pr_number=pr_number, error=str(e))
            return False
    
    def close_pr(self, repo_name: str, pr_number: int) -> None:
        """Close a pull request without merging."""
        repo = self.github.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        pr.edit(state="closed")
        logger.info("PR closed", pr_number=pr_number)

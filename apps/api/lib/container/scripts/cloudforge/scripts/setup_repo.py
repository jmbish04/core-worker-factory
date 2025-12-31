# apps/api/sandbox-modules/scripts/setup_repo.py
#!/usr/bin/env python3
"""
Script to setup a new worker repository.

Usage:
    python setup_repo.py --name my-worker --description "My awesome worker"
"""

import click
import structlog

from cloudforge import RepoManager, Config, Logger

logger = structlog.get_logger(__name__)


@click.command()
@click.option("--name", required=True, help="Worker name (kebab-case)")
@click.option("--description", default="", help="Worker description")
@click.option("--clone-only", is_flag=True, help="Only clone, don't create new repo")
def main(name: str, description: str, clone_only: bool):
    """Setup a new worker repository."""
    config = Config.from_env()
    
    errors = config.validate()
    if errors:
        for error in errors:
            click.echo(f"Error: {error}", err=True)
        raise click.Abort()
    
    repo_manager = RepoManager()
    
    if clone_only:
        repo_url = f"https://github.com/{config.github_org}/{name}"
        local_path = config.workspace_dir / name
        repo_manager.clone_repo(repo_url, local_path)
        click.echo(f"Repository cloned to: {local_path}")
    else:
        repo_url, local_path = repo_manager.create_worker_repo(
            worker_name=name,
            description=description,
        )
        click.echo(f"Repository created: {repo_url}")
        click.echo(f"Local path: {local_path}")


if __name__ == "__main__":
    main()

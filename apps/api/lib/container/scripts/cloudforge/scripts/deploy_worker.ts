# apps/api/sandbox-modules/scripts/deploy_worker.py
#!/usr/bin/env python3
"""
Script to deploy a worker.

Usage:
    python deploy_worker.py --path /workspace/my-worker
"""

import click
import structlog
from pathlib import Path

from cloudforge import WranglerRunner, NPMRunner, Config

logger = structlog.get_logger(__name__)


@click.command()
@click.option("--path", required=True, type=click.Path(exists=True), help="Worker path")
@click.option("--env", default=None, help="Environment to deploy to")
@click.option("--skip-build", is_flag=True, help="Skip build step")
def main(path: str, env: str, skip_build: bool):
    """Deploy a worker to Cloudflare."""
    config = Config.from_env()
    
    errors = config.validate()
    if errors:
        for error in errors:
            click.echo(f"Error: {error}", err=True)
        raise click.Abort()
    
    worker_path = Path(path)
    npm = NPMRunner()
    wrangler = WranglerRunner()
    
    # Install dependencies
    click.echo("Installing dependencies...")
    npm.install(worker_path)
    
    # Build
    if not skip_build:
        click.echo("Building worker...")
        npm.build(worker_path)
    
    # Deploy
    click.echo("Deploying worker...")
    result = wrangler.deploy(worker_path, env=env)
    
    if "url" in result:
        click.echo(f"Worker deployed: {result['url']}")
    else:
        click.echo(f"Deployment output: {result}")


if __name__ == "__main__":
    main()

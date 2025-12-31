# apps/api/sandbox-modules/scripts/create_bindings.py
#!/usr/bin/env python3
"""
Script to create Cloudflare bindings for a worker.

Usage:
    python create_bindings.py --name my-worker --d1 --r2 --kv
"""

import click
import json
import structlog

from cloudforge import D1Manager, R2Manager, KVManager, Config

logger = structlog.get_logger(__name__)


@click.command()
@click.option("--name", required=True, help="Worker name")
@click.option("--d1", is_flag=True, help="Create D1 database")
@click.option("--r2", is_flag=True, help="Create R2 bucket")
@click.option("--kv", is_flag=True, help="Create KV namespace")
@click.option("--output", default="bindings.json", help="Output file for binding info")
def main(name: str, d1: bool, r2: bool, kv: bool, output: str):
    """Create Cloudflare bindings for a worker."""
    config = Config.from_env()
    
    errors = config.validate()
    if errors:
        for error in errors:
            click.echo(f"Error: {error}", err=True)
        raise click.Abort()
    
    bindings = {}
    
    if d1:
        d1_manager = D1Manager()
        db = d1_manager.create_database(f"{name}-db")
        bindings["d1"] = {
            "binding": "DB",
            "database_name": db["name"],
            "database_id": db["uuid"],
        }
        click.echo(f"D1 database created: {db['name']} ({db['uuid']})")
    
    if r2:
        r2_manager = R2Manager()
        bucket = r2_manager.create_bucket(f"{name}-assets")
        bindings["r2"] = {
            "binding": "ASSETS",
            "bucket_name": bucket["name"],
        }
        click.echo(f"R2 bucket created: {bucket['name']}")
    
    if kv:
        kv_manager = KVManager()
        namespace = kv_manager.create_namespace(f"{name}-cache")
        bindings["kv"] = {
            "binding": "CACHE",
            "id": namespace["id"],
        }
        click.echo(f"KV namespace created: {namespace['title']} ({namespace['id']})")
    
    # Write bindings info
    with open(output, "w") as f:
        json.dump(bindings, f, indent=2)
    
    click.echo(f"Binding info written to: {output}")


if __name__ == "__main__":
    main()

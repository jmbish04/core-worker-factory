# apps/api/sandbox-modules/cloudforge/cloudflare/workers.py
"""
Workers management operations.
"""

from typing import Optional, List, Dict, Any
from pathlib import Path
import structlog

from cloudforge.cloudflare.client import CloudflareClient

logger = structlog.get_logger(__name__)


class WorkersManager:
    """Manages Cloudflare Workers operations."""
    
    def __init__(self, cf_client: Optional[CloudflareClient] = None):
        """Initialize Workers manager."""
        self.cf = cf_client or CloudflareClient()
    
    def list_workers(self) -> List[Dict[str, Any]]:
        """List all workers in the account."""
        result = self.cf.client.workers.scripts.list(
            account_id=self.cf.account_id,
        )
        
        return [
            {
                "id": script.id,
                "created_on": script.created_on,
                "modified_on": script.modified_on,
            }
            for script in result
        ]
    
    def get_worker(self, script_name: str) -> Dict[str, Any]:
        """Get worker script info."""
        result = self.cf.client.workers.scripts.get(
            script_name=script_name,
            account_id=self.cf.account_id,
        )
        
        return {
            "id": result.id,
            "created_on": result.created_on,
            "modified_on": result.modified_on,
        }
    
    def get_worker_settings(self, script_name: str) -> Dict[str, Any]:
        """Get worker script settings including bindings."""
        result = self.cf.client.workers.scripts.settings.get(
            script_name=script_name,
            account_id=self.cf.account_id,
        )
        
        return {
            "bindings": [
                {
                    "type": b.type,
                    "name": b.name,
                }
                for b in result.bindings
            ] if result.bindings else [],
        }
    
    def delete_worker(self, script_name: str) -> None:
        """Delete a worker script."""
        logger.warning("Deleting worker", script_name=script_name)
        
        self.cf.client.workers.scripts.delete(
            script_name=script_name,
            account_id=self.cf.account_id,
        )
    
    def get_subdomain(self) -> str:
        """Get the workers.dev subdomain for the account."""
        result = self.cf.client.workers.subdomains.get(
            account_id=self.cf.account_id,
        )
        return result.subdomain
    
    def get_worker_url(self, script_name: str) -> str:
        """Get the public URL for a worker."""
        subdomain = self.get_subdomain()
        return f"https://{script_name}.{subdomain}.workers.dev"

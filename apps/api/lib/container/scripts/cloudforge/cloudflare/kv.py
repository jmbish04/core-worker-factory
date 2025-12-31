# apps/api/sandbox-modules/cloudforge/cloudflare/kv.py
"""
KV namespace management operations.
"""

from typing import Optional, List, Dict, Any
import structlog

from cloudforge.cloudflare.client import CloudflareClient

logger = structlog.get_logger(__name__)


class KVManager:
    """Manages KV namespace operations."""
    
    def __init__(self, cf_client: Optional[CloudflareClient] = None):
        """Initialize KV manager."""
        self.cf = cf_client or CloudflareClient()
    
    def create_namespace(self, title: str) -> Dict[str, Any]:
        """
        Create a new KV namespace.
        
        Args:
            title: Namespace title
            
        Returns:
            Namespace info dict with 'id', 'title'
        """
        logger.info("Creating KV namespace", title=title)
        
        result = self.cf.client.kv.namespaces.create(
            account_id=self.cf.account_id,
            title=title,
        )
        
        logger.info("KV namespace created", id=result.id, title=result.title)
        
        return {
            "id": result.id,
            "title": result.title,
        }
    
    def list_namespaces(self) -> List[Dict[str, Any]]:
        """List all KV namespaces."""
        result = self.cf.client.kv.namespaces.list(
            account_id=self.cf.account_id,
        )
        
        return [
            {
                "id": ns.id,
                "title": ns.title,
            }
            for ns in result.result
        ]
    
    def delete_namespace(self, namespace_id: str) -> None:
        """Delete a KV namespace."""
        logger.warning("Deleting KV namespace", namespace_id=namespace_id)
        
        self.cf.client.kv.namespaces.delete(
            namespace_id=namespace_id,
            account_id=self.cf.account_id,
        )

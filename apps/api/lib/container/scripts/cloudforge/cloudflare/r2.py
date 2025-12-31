# apps/api/sandbox-modules/cloudforge/cloudflare/r2.py
"""
R2 storage management operations.
"""

from typing import Optional, List, Dict, Any
import structlog

from cloudforge.cloudflare.client import CloudflareClient

logger = structlog.get_logger(__name__)


class R2Manager:
    """Manages R2 bucket operations."""
    
    def __init__(self, cf_client: Optional[CloudflareClient] = None):
        """Initialize R2 manager."""
        self.cf = cf_client or CloudflareClient()
    
    def create_bucket(
        self,
        name: str,
        location_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new R2 bucket.
        
        Args:
            name: Bucket name (must be globally unique)
            location_hint: Location hint
            
        Returns:
            Bucket info dict
        """
        logger.info("Creating R2 bucket", name=name)
        
        result = self.cf.client.r2.buckets.create(
            account_id=self.cf.account_id,
            name=name,
            location_hint=location_hint,
        )
        
        logger.info("R2 bucket created", name=result.name)
        
        return {
            "name": result.name,
            "creation_date": result.creation_date,
            "location": result.location,
        }
    
    def list_buckets(self) -> List[Dict[str, Any]]:
        """List all R2 buckets."""
        result = self.cf.client.r2.buckets.list(
            account_id=self.cf.account_id,
        )
        
        return [
            {
                "name": bucket.name,
                "creation_date": bucket.creation_date,
            }
            for bucket in result.buckets
        ]
    
    def delete_bucket(self, name: str) -> None:
        """Delete an R2 bucket."""
        logger.warning("Deleting R2 bucket", name=name)
        
        self.cf.client.r2.buckets.delete(
            bucket_name=name,
            account_id=self.cf.account_id,
        )

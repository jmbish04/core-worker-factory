# apps/api/sandbox-modules/cloudforge/cloudflare/client.py
"""
Cloudflare API client wrapper.
"""

from typing import Optional
import cloudflare
from cloudflare import Cloudflare
import structlog

from cloudforge.config import get_config

logger = structlog.get_logger(__name__)


class CloudflareClient:
    """Wrapper for Cloudflare API operations."""
    
    def __init__(
        self,
        api_token: Optional[str] = None,
        account_id: Optional[str] = None,
    ):
        """Initialize Cloudflare client."""
        config = get_config()
        self.api_token = api_token or config.cloudflare_api_token
        self.account_id = account_id or config.cloudflare_account_id
        self._client: Optional[Cloudflare] = None
    
    @property
    def client(self) -> Cloudflare:
        """Get or create Cloudflare client."""
        if self._client is None:
            self._client = Cloudflare(api_token=self.api_token)
        return self._client
    
    def verify_token(self) -> bool:
        """Verify the API token is valid."""
        try:
            result = self.client.user.tokens.verify()
            logger.info("API token verified", status=result.status)
            return result.status == "active"
        except Exception as e:
            logger.error("API token verification failed", error=str(e))
            return False

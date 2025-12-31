# apps/api/sandbox-modules/cloudforge/cloudflare/d1.py
"""
D1 database management operations.
"""

from typing import Optional, List, Dict, Any
import structlog

from cloudforge.cloudflare.client import CloudflareClient

logger = structlog.get_logger(__name__)


class D1Manager:
    """Manages D1 database operations."""
    
    def __init__(self, cf_client: Optional[CloudflareClient] = None):
        """Initialize D1 manager."""
        self.cf = cf_client or CloudflareClient()
    
    def create_database(
        self,
        name: str,
        primary_location_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new D1 database.
        
        Args:
            name: Database name
            primary_location_hint: Location hint (wnam, enam, weur, eeur, apac)
            
        Returns:
            Database info dict with 'uuid', 'name', etc.
        """
        logger.info("Creating D1 database", name=name, location=primary_location_hint)
        
        params = {"name": name}
        if primary_location_hint:
            params["primary_location_hint"] = primary_location_hint
        
        result = self.cf.client.d1.database.create(
            account_id=self.cf.account_id,
            **params,
        )
        
        logger.info("D1 database created", uuid=result.uuid, name=result.name)
        
        return {
            "uuid": result.uuid,
            "name": result.name,
            "created_at": result.created_at,
            "version": result.version,
        }
    
    def list_databases(self) -> List[Dict[str, Any]]:
        """List all D1 databases."""
        result = self.cf.client.d1.database.list(
            account_id=self.cf.account_id,
        )
        
        return [
            {
                "uuid": db.uuid,
                "name": db.name,
                "created_at": db.created_at,
            }
            for db in result
        ]
    
    def get_database(self, database_id: str) -> Dict[str, Any]:
        """Get database info by ID."""
        result = self.cf.client.d1.database.get(
            database_id=database_id,
            account_id=self.cf.account_id,
        )
        
        return {
            "uuid": result.uuid,
            "name": result.name,
            "created_at": result.created_at,
            "version": result.version,
            "num_tables": result.num_tables,
            "file_size": result.file_size,
        }
    
    def delete_database(self, database_id: str) -> None:
        """Delete a D1 database."""
        logger.warning("Deleting D1 database", database_id=database_id)
        
        self.cf.client.d1.database.delete(
            database_id=database_id,
            account_id=self.cf.account_id,
        )
    
    def query(
        self,
        database_id: str,
        sql: str,
        params: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a SQL query against a D1 database.
        
        Note: For production code, always use Drizzle ORM.
        This is for migrations and debugging only.
        """
        logger.debug("Executing D1 query", database_id=database_id, sql=sql[:100])
        
        result = self.cf.client.d1.database.query(
            database_id=database_id,
            account_id=self.cf.account_id,
            sql=sql,
            params=params or [],
        )
        
        return [dict(row) for row in result]

"""
Postgres database integration for maskcomponent service
"""
import asyncpg
from typing import Dict, Optional
from .config import PostgresConfig
from .logger import setup_logger

logger = setup_logger(__name__)


class Database:
    """Postgres database client"""
    
    def __init__(self, config: PostgresConfig):
        """Initialize database config"""
        self.config = config
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self, min_size: int = 2, max_size: int = 10):
        """Create connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.config.dsn,
                min_size=min_size,
                max_size=max_size,
            )
            logger.info("Database connection pool created")
            
            # Ensure table exists
            await self._ensure_table()
        except Exception as e:
            logger.error(f"Error creating database pool: {e}", exc_info=True)
            raise
    
    async def _ensure_table(self):
        """Ensure user_mask_outputs table exists"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS user_mask_outputs (
            user_id TEXT PRIMARY KEY,
            gender TEXT,
            request_id TEXT,
            upper_body_mask TEXT,
            upper_body_tshirts_mask TEXT,
            upper_body_coat_mask TEXT,
            lower_body_mask TEXT,
            ethnic_combined_mask TEXT,
            baggy_lower_mask TEXT,
            dress_mask TEXT,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        );
        """
        
        async with self.pool.acquire() as conn:
            await conn.execute(create_table_sql)
            logger.info("Table user_mask_outputs ensured")
    
    async def upsert_user_masks(
        self,
        user_id: str,
        gender: str,
        request_id: str,
        mask_filenames: Dict[str, str]
    ):
        """
        Upsert user mask filenames into database
        
        Args:
            user_id: User identifier
            gender: Gender string
            request_id: Request ID for URL construction
            mask_filenames: Dictionary of mask_type -> filename (e.g., {"upper_body": "upper_body_mask.png"})
        """
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        
        upsert_sql = """
        INSERT INTO user_mask_outputs (
            user_id, gender, request_id, 
            upper_body_mask, upper_body_tshirts_mask, upper_body_coat_mask,
            lower_body_mask, ethnic_combined_mask, baggy_lower_mask, dress_mask,
            updated_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, now())
        ON CONFLICT (user_id)
        DO UPDATE SET
            gender = EXCLUDED.gender,
            request_id = EXCLUDED.request_id,
            upper_body_mask = EXCLUDED.upper_body_mask,
            upper_body_tshirts_mask = EXCLUDED.upper_body_tshirts_mask,
            upper_body_coat_mask = EXCLUDED.upper_body_coat_mask,
            lower_body_mask = EXCLUDED.lower_body_mask,
            ethnic_combined_mask = EXCLUDED.ethnic_combined_mask,
            baggy_lower_mask = EXCLUDED.baggy_lower_mask,
            dress_mask = EXCLUDED.dress_mask,
            updated_at = now();
        """
        
        try:
            # Extract filenames for each mask type
            upper_body = mask_filenames.get("upper_body")
            upper_body_tshirts = mask_filenames.get("upper_body_tshirts")
            upper_body_coat = mask_filenames.get("upper_body_coat")
            lower_body = mask_filenames.get("lower_body")
            ethnic_combined = mask_filenames.get("ethnic_combined")
            baggy_lower = mask_filenames.get("baggy_lower")
            dress = mask_filenames.get("dress")
            
            async with self.pool.acquire() as conn:
                await conn.execute(
                    upsert_sql,
                    user_id,
                    gender,
                    request_id,
                    upper_body,
                    upper_body_tshirts,
                    upper_body_coat,
                    lower_body,
                    ethnic_combined,
                    baggy_lower,
                    dress
                )
            logger.info(f"Upserted mask filenames for user_id: {user_id}")
        except Exception as e:
            logger.error(f"Error upserting user masks: {e}", exc_info=True)
            raise
    
    async def get_user_masks(self, user_id: str) -> Optional[Dict]:
        """Get user mask filenames from database"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        
        select_sql = """
        SELECT user_id, gender, request_id, 
            upper_body_mask, upper_body_tshirts_mask, upper_body_coat_mask,
            lower_body_mask, ethnic_combined_mask, baggy_lower_mask, dress_mask,
            updated_at
        FROM user_mask_outputs
        WHERE user_id = $1;
        """
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(select_sql, user_id)
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Error getting user masks: {e}", exc_info=True)
            raise
    
    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")




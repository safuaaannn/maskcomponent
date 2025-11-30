"""
MinIO storage integration for maskcomponent service
"""
import io
import asyncio
from typing import Optional
from pathlib import Path
from PIL import Image
from minio import Minio
from minio.error import S3Error
from .config import MinIOConfig
from .logger import setup_logger

logger = setup_logger(__name__)


class MinIOStorage:
    """MinIO storage client wrapper"""
    
    def __init__(self, config: MinIOConfig):
        """Initialize MinIO client"""
        self.config = config
        # Newer minio versions require all parameters as keyword arguments
        minio_kwargs = {
            "endpoint": config.endpoint,
            "access_key": config.access_key,
            "secret_key": config.secret_key,
            "secure": config.secure,
        }
        if config.region:
            minio_kwargs["region"] = config.region
        self.client = Minio(**minio_kwargs)
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        """Ensure bucket exists, create if not"""
        try:
            if not self.client.bucket_exists(bucket_name=self.config.bucket):
                self.client.make_bucket(bucket_name=self.config.bucket)
                logger.info(f"Created bucket: {self.config.bucket}")
            else:
                logger.info(f"Bucket exists: {self.config.bucket}")
        except S3Error as e:
            logger.error(f"Error ensuring bucket exists: {e}", exc_info=True)
            raise
    
    async def upload_image(
        self,
        image: Image.Image,
        key: str,
        content_type: str = "image/png"
    ) -> str:
        """
        Upload PIL Image to MinIO
        
        Args:
            image: PIL Image to upload
            key: Object key (path) in bucket
            content_type: MIME type (default: image/png)
        
        Returns:
            Object key (same as input)
        """
        # Convert image to bytes
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        
        # Upload in executor (MinIO client is sync)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._upload_bytes,
            buffer.getvalue(),
            key,
            content_type
        )
        
        logger.info(f"Uploaded image to MinIO: {key}")
        return key
    
    def _upload_bytes(self, data: bytes, key: str, content_type: str):
        """Synchronous upload helper"""
        try:
            self.client.put_object(
                bucket_name=self.config.bucket,
                object_name=key,
                data=io.BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
        except S3Error as e:
            logger.error(f"Error uploading to MinIO: {e}", exc_info=True)
            raise
    
    async def presigned_get_url(
        self,
        key: str,
        expiry_seconds: int = 604800
    ) -> str:
        """
        Generate presigned GET URL for object
        
        Args:
            key: Object key
            expiry_seconds: URL expiry time in seconds (default: 7 days)
        
        Returns:
            Presigned URL string
        """
        loop = asyncio.get_event_loop()
        url = await loop.run_in_executor(
            None,
            self._generate_presigned_url,
            key,
            expiry_seconds
        )
        return url
    
    def _generate_presigned_url(self, key: str, expiry_seconds: int) -> str:
        """Synchronous presigned URL generation"""
        try:
            from datetime import timedelta
            url = self.client.presigned_get_object(
                bucket_name=self.config.bucket,
                object_name=key,
                expires=timedelta(seconds=expiry_seconds),
            )
            return url
        except S3Error as e:
            logger.error(f"Error generating presigned URL: {e}", exc_info=True)
            raise
    
    async def delete_object(self, key: str):
        """Delete object from MinIO"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._delete_object_sync,
            key
        )
    
    def _delete_object_sync(self, key: str):
        """Synchronous delete helper"""
        try:
            self.client.remove_object(bucket_name=self.config.bucket, object_name=key)
            logger.info(f"Deleted object from MinIO: {key}")
        except S3Error as e:
            logger.error(f"Error deleting from MinIO: {e}", exc_info=True)
            raise


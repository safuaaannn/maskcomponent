"""
Worker for processing mask generation messages
"""
import asyncio
import base64
import io
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from datetime import datetime
import aiohttp
from PIL import Image
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError
)
from .logger import setup_logger
from .mask_gen import generate_masks
from .storage import MinIOStorage
from .db import Database
from .kafka_producer import KafkaProducer
from .config import ServiceConfig, MinIOConfig

logger = setup_logger(__name__)


class MaskWorker:
    """Worker for processing mask generation requests"""
    
    def __init__(
        self,
        storage: MinIOStorage,
        db: Database,
        producer: KafkaProducer,
        service_config: ServiceConfig
    ):
        """Initialize worker"""
        self.storage = storage
        self.db = db
        self.producer = producer
        self.config = service_config
    
    async def download_image(self, image_data: Dict[str, str]) -> Image.Image:
        """
        Download or decode image from message
        
        Args:
            image_data: Dict with "type" ("url" or "base64") and "data"
        
        Returns:
            PIL Image
        """
        image_type = image_data.get("type", "").lower()
        data = image_data.get("data", "")
        
        if not data:
            raise ValueError("Image data is empty")
        
        if image_type == "url":
            # Download from URL
            url = data
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                raise ValueError(f"Invalid URL scheme: {parsed.scheme}. Only http/https allowed.")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise ValueError(f"Failed to download image: HTTP {response.status}")
                    image_bytes = await response.read()
                    image = Image.open(io.BytesIO(image_bytes))
                    return image
        
        elif image_type == "base64":
            # Decode base64
            try:
                # Remove data URL prefix if present
                if "," in data:
                    data = data.split(",", 1)[1]
                image_bytes = base64.b64decode(data)
                image = Image.open(io.BytesIO(image_bytes))
                return image
            except Exception as e:
                raise ValueError(f"Failed to decode base64 image: {e}")
        
        else:
            raise ValueError(f"Unsupported image type: {image_type}")
    
    def _generate_storage_key(
        self,
        user_id: str,
        request_id: Optional[str],
        mask_type: str
    ) -> str:
        """Generate MinIO storage key (returns full path)"""
        if request_id:
            identifier = request_id
        else:
            identifier = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        return f"{user_id}/{identifier}/{mask_type}_mask.png"
    
    def _extract_filename(self, storage_key: str) -> str:
        """Extract just the filename from storage key"""
        return storage_key.split("/")[-1]
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, ConnectionError))
    )
    async def process_message(
        self,
        message: Dict[str, Any],
        models
    ):
        """
        Process a mask generation message
        
        Args:
            message: Kafka message payload
            models: MaskGenerationModels instance
        """
        user_id = message.get("user_id")
        gender = message.get("gender", "other")
        image_data = message.get("image", {})
        request_id = message.get("request_id")
        mask_types = message.get("mask_types")
        
        # Validate required fields
        if not user_id:
            raise ValueError("user_id is required in message")
        if not isinstance(user_id, (str, int)):
            raise ValueError(f"user_id must be string or int, got {type(user_id).__name__}")
        user_id = str(user_id)  # Normalize to string
        
        if not image_data:
            raise ValueError("image data is required in message")
        if not isinstance(image_data, dict):
            raise ValueError(f"image data must be a dictionary, got {type(image_data).__name__}")
        
        # Validate gender
        if gender and gender.upper() not in ("M", "F", "MALE", "FEMALE", "OTHER"):
            logger.warning(f"Invalid gender '{gender}', defaulting to 'other'")
            gender = "other"
        
        # Normalize gender
        gender_map = {"M": "M", "MALE": "M", "F": "F", "FEMALE": "F"}
        gender = gender_map.get(gender.upper(), gender)
        
        # Use default mask types if not specified
        if not mask_types:
            mask_types = self.config.mask_types_default
        elif isinstance(mask_types, str):
            # Handle comma-separated string
            mask_types = [m.strip() for m in mask_types.split(",") if m.strip()]
        elif not isinstance(mask_types, list):
            raise ValueError(f"mask_types must be a list or comma-separated string, got {type(mask_types).__name__}")
        
        # Validate mask types
        valid_mask_types = {"upper_body", "upper_body_tshirts", "upper_body_coat", "lower_body", "ethnic_combined", "baggy_lower", "dress"}
        invalid_types = [mt for mt in mask_types if mt not in valid_mask_types]
        if invalid_types:
            raise ValueError(f"Invalid mask types: {invalid_types}. Valid types: {sorted(valid_mask_types)}")
        
        if not mask_types:
            raise ValueError("No valid mask types specified")
        
        # Set up logging context
        import logging
        old_factory = logging.getLogRecordFactory()
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            if request_id:
                record.request_id = request_id
            if user_id:
                record.user_id = user_id
            record.stage = "process_message"
            record.event = "start"
            return record
        logging.setLogRecordFactory(record_factory)
        
        try:
            logger.info(f"Processing message for user_id: {user_id}")
            # Download/decode image
            logger.info(f"Downloading image for user_id: {user_id}")
            image = await self.download_image(image_data)
            
            # Generate masks
            logger.info(f"Generating masks for user_id: {user_id}")
            masks = await generate_masks(
                image,
                mask_types,
                gender,
                models,
                neck_mask_radius=0.4
            )
            
            if not masks:
                raise ValueError("No masks were generated successfully")
            
            # Upload masks to MinIO and collect filenames only
            mask_filenames = {}
            for mask_type, mask_image in masks.items():
                storage_key = self._generate_storage_key(user_id, request_id, mask_type)
                
                # Upload to MinIO
                await self.storage.upload_image(mask_image, storage_key)
                
                # Store only filename (extract from storage_key)
                filename = self._extract_filename(storage_key)
                mask_filenames[mask_type] = filename
            
            # Upsert to database (only filenames, no URLs)
            logger.info(f"Upserting to database for user_id: {user_id}")
            await self.db.upsert_user_masks(
                user_id,
                gender,
                request_id,
                mask_filenames
            )
            
            # Build full URLs for output message (using base_url from config)
            mask_urls = {}
            for mask_type, filename in mask_filenames.items():
                # Construct full URL: base_url/user_id/request_id/filename
                storage_key = self._generate_storage_key(user_id, request_id, mask_type)
                full_url = f"{self.config.base_url}/{storage_key}"
                mask_urls[mask_type] = full_url
            
            # Publish success message
            await self.producer.publish_mask_output(
                user_id=user_id,
                gender=gender,
                mask_paths=mask_urls,
                request_id=request_id,
                status="completed"
            )
            
            logger.info(f"Successfully processed message for user_id: {user_id}")
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error processing message: {error_msg}", exc_info=True)
            
            # Publish failure message
            try:
                await self.producer.publish_mask_output(
                    user_id=user_id,
                    gender=gender,
                    mask_paths={},
                    request_id=request_id,
                    status="failed",
                    error=error_msg
                )
            except Exception as pub_error:
                logger.error(f"Failed to publish error message: {pub_error}", exc_info=True)
            
            # Re-raise to trigger retry or poison queue
            raise
        finally:
            # Restore logging factory
            logging.setLogRecordFactory(old_factory)


"""
Kafka producer for maskcomponent service using message_broker
"""
import json
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from message_broker.message_broker_provider import MessageBrokerProvider
from .config import KafkaConfig
from .logger import setup_logger

logger = setup_logger(__name__)


class KafkaProducer:
    """Kafka producer for publishing messages"""
    
    def __init__(self, config: KafkaConfig):
        """Initialize Kafka producer"""
        self.config = config
        self.broker = None
        self._loop = None
    
    async def connect(self):
        """Connect to Kafka"""
        try:
            # Build message_broker config
            broker_config = {
                "message_broker": {
                    "type": "kafka",
                    "connection_string": self.config.bootstrap_servers,
                    "topics": {
                        "output": self.config.topic_output,
                        "poison": self.config.topic_poison
                    },
                    "group_id": self.config.consumer_group,
                    "auto_offset_reset": "earliest",
                    "enable_auto_commit": True
                }
            }
            
            # Initialize message broker provider
            broker_provider = MessageBrokerProvider(broker_config)
            self.broker = broker_provider.get_message_broker()
            self._loop = asyncio.get_event_loop()
            
            logger.info("Kafka producer connected")
        except Exception as e:
            logger.error(f"Error connecting Kafka producer: {e}", exc_info=True)
            raise
    
    async def publish_mask_output(
        self,
        user_id: str,
        gender: str,
        mask_paths: Dict[str, str],
        request_id: Optional[str],
        status: str = "completed",
        error: Optional[str] = None
    ):
        """
        Publish mask output message
        
        Args:
            user_id: User identifier
            gender: Gender string
            mask_paths: Dictionary of mask_type -> URL
            request_id: Request ID from input message
            status: "completed" or "failed"
            error: Error message if status is "failed"
        """
        if not self.broker:
            raise RuntimeError("Producer not connected. Call connect() first.")
        
        message = {
            "user_id": user_id,
            "gender": gender,
            "mask_paths": mask_paths,
            "status": status,
            "request_id": request_id,
            "processed_at": datetime.utcnow().isoformat() + "Z",
        }
        
        if error:
            message["error"] = error
        
        try:
            value = json.dumps(message).encode("utf-8")
            
            # Produce message in executor (message_broker uses sync confluent-kafka)
            await self._loop.run_in_executor(
                None,
                self.broker.produce,
                value,
                "output",
                None  # partition=None, let Kafka decide
            )
            
            logger.info(f"Published mask_output message for user_id: {user_id}")
        except Exception as e:
            logger.error(f"Error publishing mask_output: {e}", exc_info=True)
            raise
    
    async def publish_poison_message(
        self,
        original_message: Dict[str, Any],
        error: str,
        attempts: int,
        error_trace: Optional[str] = None
    ):
        """
        Publish message to poison queue
        
        Args:
            original_message: Original input message
            error: Error message
            attempts: Number of retry attempts
            error_trace: Full error traceback
        """
        if not self.broker:
            raise RuntimeError("Producer not connected. Call connect() first.")
        
        poison_message = {
            "original_message": original_message,
            "error": error,
            "attempts": attempts,
            "error_trace": error_trace,
            "failed_at": datetime.utcnow().isoformat() + "Z",
        }
        
        try:
            value = json.dumps(poison_message).encode("utf-8")
            user_id = original_message.get("user_id", "unknown")
            
            # Produce message in executor
            await self._loop.run_in_executor(
                None,
                self.broker.produce,
                value,
                "poison",
                None
            )
            
            logger.warning(f"Published poison message for user_id: {user_id}")
        except Exception as e:
            logger.error(f"Error publishing poison message: {e}", exc_info=True)
            raise
    
    async def close(self):
        """Close producer"""
        if self.broker:
            # Cleanup if needed
            logger.info("Kafka producer closed")



"""
Kafka consumer for maskcomponent service using message_broker
"""
import json
import asyncio
from typing import Callable, Awaitable, Optional
from confluent_kafka import KafkaError
from message_broker.message_broker_provider import MessageBrokerProvider
from .config import KafkaConfig
from .logger import setup_logger

logger = setup_logger(__name__)


class KafkaConsumer:
    """Kafka consumer for processing messages"""
    
    def __init__(
        self,
        config: KafkaConfig,
        message_handler: Callable[[dict], Awaitable[None]]
    ):
        """
        Initialize Kafka consumer
        
        Args:
            config: Kafka configuration
            message_handler: Async function to handle messages
        """
        self.config = config
        self.message_handler = message_handler
        self.broker = None
        self.consumer = None
        self.running = False
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
                        "input": self.config.topic_input
                    },
                    "group_id": self.config.consumer_group,
                    "auto_offset_reset": "earliest",
                    "enable_auto_commit": False  # Manual commit for at-least-once
                }
            }
            
            # Initialize message broker provider
            broker_provider = MessageBrokerProvider(broker_config)
            self.broker = broker_provider.get_message_broker()
            
            # Get consumer from broker
            self.consumer = self.broker.consume(topic_keys=["input"])
            self._loop = asyncio.get_event_loop()
            
            logger.info("Kafka consumer connected")
        except Exception as e:
            logger.error(f"Error connecting Kafka consumer: {e}", exc_info=True)
            raise
    
    async def consume(self, concurrency: int = 4):
        """
        Start consuming messages with concurrency limit
        
        Args:
            concurrency: Maximum number of concurrent message processing tasks
        """
        if not self.consumer:
            raise RuntimeError("Consumer not connected. Call connect() first.")
        
        self.running = True
        semaphore = asyncio.Semaphore(concurrency)
        
        logger.info(f"Starting message consumption (concurrency: {concurrency})")
        
        try:
            while self.running:
                # Poll for messages (non-blocking in executor)
                msg = await self._loop.run_in_executor(
                    None,
                    lambda: self.consumer.poll(timeout=1.0)
                )
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # End of partition, continue
                        continue
                    else:
                        logger.error(f"Kafka consumer error: {msg.error()}")
                        continue
                
                # Acquire semaphore
                await semaphore.acquire()
                
                # Process message in background task
                asyncio.create_task(
                    self._process_message(msg, semaphore)
                )
        
        except Exception as e:
            logger.error(f"Error in consumer loop: {e}", exc_info=True)
        finally:
            await self.stop()
    
    async def _process_message(self, msg, semaphore: asyncio.Semaphore):
        """Process a single message"""
        try:
            # Parse message
            try:
                msg_data = json.loads(msg.value().decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.error(f"Failed to parse message: {e}", exc_info=True)
                # Commit offset even on parse error to avoid infinite loop
                await self._loop.run_in_executor(None, lambda: self.consumer.commit(message=msg, asynchronous=False))
                return
            
            # Process message
            await self.message_handler(msg_data)
            
            # Commit offset after successful processing
            await self._loop.run_in_executor(None, lambda: self.consumer.commit(message=msg, asynchronous=False))
            logger.debug(f"Committed offset for message")
        
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            # Don't commit on error - message will be reprocessed
            # In production, you might want to track retries and send to poison queue
        
        finally:
            # Release semaphore
            semaphore.release()
    
    async def stop(self):
        """Stop consumer gracefully"""
        self.running = False
        if self.consumer:
            # Close consumer in executor
            await self._loop.run_in_executor(None, self.consumer.close)
            logger.info("Kafka consumer stopped")
    
    async def close(self):
        """Close consumer"""
        await self.stop()



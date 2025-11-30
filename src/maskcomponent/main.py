"""
Main entry point for maskcomponent service
"""
import asyncio
import signal
import sys
from pathlib import Path
from typing import Optional

# Add project root to path for mask_generation imports
PROJECT_ROOT = Path(__file__).absolute().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from .config import load_config
from .logger import setup_logger
from .storage import MinIOStorage
from .db import Database
from .kafka_producer import KafkaProducer
from .kafka_consumer import KafkaConsumer
from .worker import MaskWorker

logger = setup_logger(__name__)


class MaskService:
    """Main service class"""
    
    def __init__(self):
        """Initialize service"""
        self.config = None
        self.storage: Optional[MinIOStorage] = None
        self.db: Optional[Database] = None
        self.producer: Optional[KafkaProducer] = None
        self.consumer: Optional[KafkaConsumer] = None
        self.worker: Optional[MaskWorker] = None
        self.models = None
        self.running = False
    
    async def initialize(self):
        """Initialize all components"""
        try:
            # Load configuration
            logger.info("Loading configuration...")
            kafka_config, minio_config, postgres_config, service_config = load_config()
            self.config = {
                "kafka": kafka_config,
                "minio": minio_config,
                "postgres": postgres_config,
                "service": service_config,
            }
            
            # Initialize models (CRITICAL: do this once at startup)
            logger.info("Initializing mask generation models...")
            try:
                from mask_generation.models import get_models
                self.models = get_models(gpu_id=service_config.gpu_id)
                logger.info("Mask generation models initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize models: {e}", exc_info=True)
                raise
            
            # Initialize storage
            logger.info("Initializing MinIO storage...")
            self.storage = MinIOStorage(minio_config)
            
            # Initialize database
            logger.info("Initializing database...")
            self.db = Database(postgres_config)
            await self.db.connect()
            
            # Initialize Kafka producer
            logger.info("Initializing Kafka producer...")
            self.producer = KafkaProducer(kafka_config)
            await self.producer.connect()
            
            # Initialize worker
            self.worker = MaskWorker(
                self.storage,
                self.db,
                self.producer,
                service_config
            )
            
            # Initialize Kafka consumer with message handler
            async def message_handler(msg: dict):
                """Handle incoming Kafka messages"""
                try:
                    await self.worker.process_message(msg, self.models)
                except Exception as e:
                    logger.error(f"Error in message handler: {e}", exc_info=True)
                    # The worker already handles publishing error messages
                    # For poison queue, we'd need to track retry counts
                    # For now, failed messages will be retried by the consumer
            
            self.consumer = KafkaConsumer(kafka_config, message_handler)
            await self.consumer.connect()
            
            logger.info("Service initialized successfully")
        
        except Exception as e:
            logger.error(f"Failed to initialize service: {e}", exc_info=True)
            await self.shutdown()
            raise
    
    async def start(self):
        """Start the service"""
        if not self.consumer:
            raise RuntimeError("Service not initialized. Call initialize() first.")
        
        self.running = True
        logger.info("Starting maskcomponent service...")
        
        # Start consuming messages
        try:
            await self.consumer.consume(concurrency=self.config["service"].concurrency)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Error in consumer loop: {e}", exc_info=True)
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown service gracefully"""
        if not self.running:
            return
        
        logger.info("Shutting down service...")
        self.running = False
        
        try:
            if self.consumer:
                await self.consumer.close()
            
            if self.producer:
                await self.producer.close()
            
            if self.db:
                await self.db.close()
            
            logger.info("Service shut down successfully")
        
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)


async def main():
    """Main entry point"""
    service = MaskService()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        asyncio.create_task(service.shutdown())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await service.initialize()
        await service.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())


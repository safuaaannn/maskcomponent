"""
Configuration management for maskcomponent service
"""
import os
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class KafkaConfig:
    """Kafka configuration"""
    bootstrap_servers: str
    topic_input: str = "mask_input"
    topic_output: str = "mask_output"
    topic_poison: str = "mask_input_poison"
    consumer_group: str = "maskcomponent-group"
    username: Optional[str] = None
    password: Optional[str] = None
    security_protocol: str = "PLAINTEXT"
    sasl_mechanism: Optional[str] = None


@dataclass
class MinIOConfig:
    """MinIO configuration"""
    endpoint: str
    access_key: str
    secret_key: str
    bucket: str = "masks"
    secure: bool = False
    region: Optional[str] = None


@dataclass
class PostgresConfig:
    """Postgres configuration"""
    dsn: str


@dataclass
class ServiceConfig:
    """Service configuration"""
    concurrency: int = 4
    max_retries: int = 5
    presigned_url_expiry: int = 604800  # 7 days in seconds
    mask_types_default: List[str] = None
    gpu_id: int = 0
    checkpoints_dir: str = "./checkpoints"
    base_url: str = "http://127.0.0.1:9000/masks"  # Base URL for mask files


def load_config() -> Tuple[KafkaConfig, MinIOConfig, PostgresConfig, ServiceConfig]:
    """
    Load configuration from environment variables
    
    Raises:
        ValueError: If required environment variables are missing
    
    Returns:
        Tuple of (KafkaConfig, MinIOConfig, PostgresConfig, ServiceConfig)
    """
    # Kafka config
    kafka_config = KafkaConfig(
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092"),
        topic_input=os.getenv("KAFKA_TOPIC_INPUT", "mask_input"),
        topic_output=os.getenv("KAFKA_TOPIC_OUTPUT", "mask_output"),
        topic_poison=os.getenv("KAFKA_TOPIC_POISON", "mask_input_poison"),
        consumer_group=os.getenv("KAFKA_CONSUMER_GROUP", "maskcomponent-group"),
        username=os.getenv("KAFKA_USERNAME"),
        password=os.getenv("KAFKA_PASSWORD"),
        security_protocol=os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
        sasl_mechanism=os.getenv("KAFKA_SASL_MECHANISM"),
    )
    
    # MinIO config
    minio_config = MinIOConfig(
        endpoint=os.getenv("MINIO_ENDPOINT", "127.0.0.1:9000"),
        access_key=os.getenv("MINIO_ACCESS_KEY", "admin"),
        secret_key=os.getenv("MINIO_SECRET_KEY", "admin123"),
        bucket=os.getenv("MINIO_BUCKET", "masks"),
        secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
        region=os.getenv("MINIO_REGION"),
    )
    
    # Postgres config (required)
    postgres_dsn = os.getenv("POSTGRES_DSN")
    if not postgres_dsn:
        raise ValueError(
            "POSTGRES_DSN environment variable is required. "
            "Format: postgresql://user:password@host:port/database"
        )
    postgres_config = PostgresConfig(dsn=postgres_dsn)
    
    # Service config with validation
    mask_types_str = os.getenv("MASK_TYPES_DEFAULT", "upper_body,upper_body_tshirts,upper_body_coat,lower_body,ethnic_combined,baggy_lower,dress")
    valid_mask_types = {"upper_body", "upper_body_tshirts", "upper_body_coat", "lower_body", "ethnic_combined", "baggy_lower", "dress"}
    mask_types_list = [m.strip() for m in mask_types_str.split(",") if m.strip()]
    
    # Validate mask types
    invalid_types = [mt for mt in mask_types_list if mt not in valid_mask_types]
    if invalid_types:
        raise ValueError(f"Invalid mask types: {invalid_types}. Valid types: {sorted(valid_mask_types)}")
    
    try:
        concurrency = int(os.getenv("SERVICE_CONCURRENCY", "4"))
        if concurrency < 1:
            raise ValueError("SERVICE_CONCURRENCY must be >= 1")
        if concurrency > 100:
            raise ValueError("SERVICE_CONCURRENCY must be <= 100")
    except ValueError as e:
        raise ValueError(f"Invalid SERVICE_CONCURRENCY: {e}")
    
    try:
        max_retries = int(os.getenv("MAX_RETRIES", "5"))
        if max_retries < 0:
            raise ValueError("MAX_RETRIES must be >= 0")
        if max_retries > 20:
            raise ValueError("MAX_RETRIES must be <= 20")
    except ValueError as e:
        raise ValueError(f"Invalid MAX_RETRIES: {e}")
    
    try:
        presigned_url_expiry = int(os.getenv("PRESIGNED_URL_EXPIRY", "604800"))
        if presigned_url_expiry < 60:
            raise ValueError("PRESIGNED_URL_EXPIRY must be >= 60 seconds")
        if presigned_url_expiry > 31536000:  # 1 year
            raise ValueError("PRESIGNED_URL_EXPIRY must be <= 31536000 seconds (1 year)")
    except ValueError as e:
        raise ValueError(f"Invalid PRESIGNED_URL_EXPIRY: {e}")
    
    try:
        gpu_id = int(os.getenv("GPU_ID", "0"))
        if gpu_id < 0:
            raise ValueError("GPU_ID must be >= 0")
    except ValueError as e:
        raise ValueError(f"Invalid GPU_ID: {e}")
    
    base_url = os.getenv("BASE_URL", "http://127.0.0.1:9000/masks")
    if not base_url.startswith(("http://", "https://")):
        raise ValueError("BASE_URL must start with http:// or https://")
    
    service_config = ServiceConfig(
        concurrency=concurrency,
        max_retries=max_retries,
        presigned_url_expiry=presigned_url_expiry,
        mask_types_default=mask_types_list,
        gpu_id=gpu_id,
        checkpoints_dir=os.getenv("CHECKPOINTS_DIR", "./checkpoints"),
        base_url=base_url,
    )
    
    return kafka_config, minio_config, postgres_config, service_config


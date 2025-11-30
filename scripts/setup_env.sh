#!/bin/bash
# Quick script to set environment variables for testing

# Kafka Configuration
export KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9092
export KAFKA_TOPIC_INPUT=mask_input
export KAFKA_TOPIC_OUTPUT=mask_output
export KAFKA_TOPIC_POISON=mask_input_poison
export KAFKA_CONSUMER_GROUP=maskcomponent-group

# MinIO Configuration
export MINIO_ENDPOINT=127.0.0.1:9000
export MINIO_ACCESS_KEY=admin
export MINIO_SECRET_KEY=admin123
export MINIO_BUCKET=masks
export MINIO_SECURE=false

# PostgreSQL Configuration
export POSTGRES_DSN=postgresql://admin_user:fashionX%404031@127.0.0.1:5432/kafka_db

# Service Configuration
export SERVICE_CONCURRENCY=4
export MAX_RETRIES=5
export PRESIGNED_URL_EXPIRY=604800
export MASK_TYPES_DEFAULT=upper_body,lower_body,ethnic_combined
export GPU_ID=0
export CHECKPOINTS_DIR=./checkpoints
export BASE_URL=http://127.0.0.1:9000/masks

echo "✓ Environment variables set!"
echo ""
echo "To use these variables, run:"
echo "  source setup_env.sh"
echo ""
echo "Or run the service directly:"
echo "  source setup_env.sh && python -m maskcomponent.main"


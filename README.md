# Mask Component Service

Production-grade Python microservice for generating human segmentation masks from images using Kafka, MinIO, and PostgreSQL.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Integration Guide](#integration-guide)
- [API Documentation](#api-documentation)
- [Database Schema](#database-schema)
- [Supported Mask Types](#supported-mask-types)
- [Error Handling](#error-handling)
- [Monitoring & Logging](#monitoring--logging)
- [Production Deployment](#production-deployment)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## Overview

The Mask Component Service is an asynchronous microservice that processes image data from Kafka messages, generates multiple types of human segmentation masks using deep learning models (OpenPose, Human Parsing, DensePose), stores the generated masks in MinIO object storage, and records metadata in PostgreSQL.

### Key Capabilities

- **7 Mask Types**: Supports upper body, lower body, ethnic wear, baggy pants, dresses, and more
- **Asynchronous Processing**: High-throughput message processing with configurable concurrency
- **Production Ready**: Comprehensive error handling, retry logic, poison queue support
- **Scalable**: Stateless design allows horizontal scaling
- **Robust**: Automatic retries, graceful shutdown, connection pooling

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Backend System                            │
│  ┌──────────────┐                                           │
│  │   API/App    │───Publish──►┌──────────────────────────┐ │
│  └──────────────┘             │   Kafka (mask_input)      │ │
│                                └──────────────┬────────────┘ │
└───────────────────────────────────────────────┼─────────────┘
                                                  │
                                                  ▼
┌─────────────────────────────────────────────────────────────┐
│              Mask Component Service                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Kafka Consumer (mask_input topic)                   │   │
│  └──────────────────┬──────────────────────────────────┘   │
│                      │                                        │
│                      ▼                                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Message Worker (Async Processing)                   │   │
│  │  - Download/Decode Image                             │   │
│  │  - Generate Masks (OpenPose + Human Parsing)         │   │
│  │  - Upload to MinIO                                   │   │
│  │  - Update PostgreSQL                                 │   │
│  └──────────┬───────────────────────┬──────────────────┘   │
│             │                       │                        │
│             ▼                       ▼                        │
│  ┌──────────────┐         ┌──────────────┐                │
│  │    MinIO     │         │  PostgreSQL   │                │
│  │  (Storage)   │         │  (Metadata)   │                │
│  └──────────────┘         └──────────────┘                │
│                                                              │
│                      ┌──────────────┐                       │
│                      │ Kafka Producer│                       │
│                      └──────┬───────┘                       │
│                             │                                 │
└─────────────────────────────┼─────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ mask_output topic │
                    └────────┬─────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Backend System   │
                    │  (Consumer)       │
                    └──────────────────┘
```

### Data Flow

1. **Input**: Backend system publishes message to `mask_input` Kafka topic
2. **Processing**: Service consumes message, generates masks, stores in MinIO
3. **Storage**: Mask filenames stored in PostgreSQL, full URLs constructed using `BASE_URL`
4. **Output**: Success/error message published to `mask_output` Kafka topic
5. **Error Handling**: Failed messages after max retries sent to `mask_input_poison` topic

---

## Features

### Core Features

- ✅ **7 Mask Types**: `upper_body`, `upper_body_tshirts`, `upper_body_coat`, `lower_body`, `ethnic_combined`, `baggy_lower`, `dress`
- ✅ **Asynchronous Processing**: Built with `asyncio` for high concurrency (configurable)
- ✅ **Multiple Image Formats**: Supports URL and base64-encoded images
- ✅ **Gender-Aware**: Optimized mask generation based on gender (M/F)
- ✅ **Request Tracking**: Unique `request_id` for each processing request

### Production Features

- ✅ **Retry Logic**: Automatic retries with exponential backoff (configurable max retries)
- ✅ **Poison Queue**: Failed messages after max retries sent to dedicated poison topic
- ✅ **Structured Logging**: JSON-formatted logs with context (user_id, request_id)
- ✅ **Connection Pooling**: Database and Kafka connections are pooled
- ✅ **Graceful Shutdown**: Handles SIGINT/SIGTERM for clean shutdown
- ✅ **Input Validation**: Comprehensive validation of message payloads
- ✅ **Error Recovery**: Automatic reconnection on connection failures

### Performance Features

- ✅ **Model Optimization**: Models initialized once at startup
- ✅ **GPU Support**: CUDA acceleration for mask generation
- ✅ **Concurrent Processing**: Configurable concurrency level
- ✅ **Efficient Storage**: Only filenames stored in DB, URLs constructed dynamically

---

## Prerequisites

### System Requirements

- **Python**: 3.10 or higher
- **GPU**: CUDA-capable GPU (recommended) or CPU fallback
- **RAM**: Minimum 8GB (16GB+ recommended for GPU)
- **Disk**: Minimum 10GB free space (for models and checkpoints)

### Infrastructure Requirements

- **Kafka**: Kafka broker (2.0+) accessible from service
- **MinIO/S3**: S3-compatible object storage (MinIO, AWS S3, etc.)
- **PostgreSQL**: PostgreSQL 12+ database server
- **Network**: Access to Kafka, MinIO, and PostgreSQL

### Model Checkpoints

The service requires model checkpoints in the `checkpoints/` directory:

```
checkpoints/
├── openpose/
│   └── ckpts/
│       └── body_pose_model.pth
├── humanparsing/
│   ├── parsing_atr.onnx
│   └── parsing_lip.onnx
└── hulk/  (optional, for DensePose)
    └── Pretrain/
        └── ckpt_task*.pth.tar
```

**Note**: Checkpoints are excluded from git. You need to add them manually or download from the model sources.

---

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/safuaaannn/maskcomponent.git
cd maskcomponent
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install message_broker library (if not already installed)
# Navigate to your kafka_component directory and install:
cd ../kafka_component
pip install -e .
cd ../maskcomponent
```

### 4. Install Package

```bash
# Install maskcomponent as a package
pip install -e .
```

### 5. Add Model Checkpoints

Place model checkpoints in the `checkpoints/` directory (see Prerequisites section).

---

## Configuration

All configuration is done via environment variables. The service loads configuration at startup.

### Environment Variables

#### Kafka Configuration

```bash
# Required
export KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9092

# Optional (with defaults)
export KAFKA_TOPIC_INPUT=mask_input
export KAFKA_TOPIC_OUTPUT=mask_output
export KAFKA_TOPIC_POISON=mask_input_poison
export KAFKA_CONSUMER_GROUP=maskcomponent-group

# Optional (for authenticated Kafka)
export KAFKA_USERNAME=your_username
export KAFKA_PASSWORD=your_password
export KAFKA_SECURITY_PROTOCOL=SASL_SSL
export KAFKA_SASL_MECHANISM=PLAIN
```

#### MinIO/S3 Configuration

```bash
# Required
export MINIO_ENDPOINT=127.0.0.1:9000
export MINIO_ACCESS_KEY=admin
export MINIO_SECRET_KEY=admin123
export MINIO_BUCKET=masks

# Optional
export BASE_URL=http://127.0.0.1:9000/masks  # Base URL for mask file URLs
export PRESIGNED_URL_EXPIRY=604800  # 7 days in seconds
```

**Important**: `BASE_URL` is used to construct full URLs for mask files. Format: `{BASE_URL}/{user_id}/{request_id}/{filename}`

#### PostgreSQL Configuration

```bash
# Required (DSN format)
export POSTGRES_DSN=postgresql://username:password@host:5432/database

# Example:
export POSTGRES_DSN=postgresql://admin_user:password123@127.0.0.1:5432/kafka_db
```

#### Service Configuration

```bash
# Optional (with defaults)
export SERVICE_CONCURRENCY=4  # Number of concurrent message processors
export MAX_RETRIES=5  # Maximum retry attempts for failed messages
export GPU_ID=0  # GPU device ID (use -1 for CPU)
export CHECKPOINTS_DIR=./checkpoints  # Path to model checkpoints
export MASK_TYPES_DEFAULT=upper_body,upper_body_tshirts,upper_body_coat,lower_body,ethnic_combined,baggy_lower,dress
```

### Configuration File

You can use the provided script to set environment variables:

```bash
# Source the configuration script
source scripts/setup_env.sh

# Or create your own .env file and source it
source .env
```

### Configuration Validation

The service validates configuration at startup and will raise errors for:
- Missing required environment variables
- Invalid `POSTGRES_DSN` format
- Invalid `BASE_URL` format
- Invalid `SERVICE_CONCURRENCY` (must be > 0)
- Invalid `MAX_RETRIES` (must be >= 0)

---

## Integration Guide

### For Backend Developers

This section explains how to integrate the Mask Component Service into your backend system.

### 1. Setup Kafka Topics

Ensure the following Kafka topics exist:

```bash
# Input topic (where you publish requests)
mask_input

# Output topic (where service publishes results)
mask_output

# Poison topic (for failed messages after max retries)
mask_input_poison
```

**Topic Configuration Recommendations:**
- **Partitions**: 3-6 (for parallel processing)
- **Replication Factor**: 2-3 (for high availability)
- **Retention**: 7 days (adjust based on your needs)

You can use the provided script to create topics:

```bash
./scripts/create_topics.sh
```

### 2. Publish Messages to Kafka

Publish mask generation requests to the `mask_input` topic:

```python
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=['127.0.0.1:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Example message
message = {
    "user_id": "123",
    "gender": "M",  # "M" or "F"
    "request_id": "req-123-001",  # Optional, auto-generated if not provided
    "mask_types": ["upper_body", "lower_body", "ethnic_combined"],  # Optional
    "image": {
        "type": "url",  # "url" or "base64"
        "data": "http://example.com/user_image.jpg"
    }
}

# Publish to mask_input topic
producer.send('mask_input', value=message)
producer.flush()
```

### 3. Consume Results from Kafka

Subscribe to the `mask_output` topic to receive processing results:

```python
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'mask_output',
    bootstrap_servers=['127.0.0.1:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    group_id='your-backend-group'  # Use your own consumer group
)

for message in consumer:
    result = message.value
    
    if result['status'] == 'completed':
        user_id = result['user_id']
        mask_paths = result['mask_paths']  # Dictionary of mask_type -> URL
        
        # Process successful result
        print(f"User {user_id} masks generated:")
        for mask_type, url in mask_paths.items():
            print(f"  {mask_type}: {url}")
    
    elif result['status'] == 'failed':
        # Handle error
        print(f"Error for user {result['user_id']}: {result.get('error')}")
```

### 4. Query Database for Mask URLs

Alternatively, you can query PostgreSQL directly for mask filenames and construct URLs:

```python
import asyncpg
import os

async def get_user_masks(user_id: str):
    dsn = os.getenv("POSTGRES_DSN")
    conn = await asyncpg.connect(dsn)
    
    row = await conn.fetchrow(
        "SELECT * FROM user_mask_outputs WHERE user_id = $1",
        user_id
    )
    
    if row:
        base_url = os.getenv("BASE_URL", "http://127.0.0.1:9000/masks")
        request_id = row['request_id']
        
        masks = {}
        mask_types = [
            'upper_body', 'upper_body_tshirts', 'upper_body_coat',
            'lower_body', 'ethnic_combined', 'baggy_lower', 'dress'
        ]
        
        for mask_type in mask_types:
            filename = row.get(f'{mask_type}_mask')
            if filename:
                # Construct full URL: base_url/user_id/request_id/filename
                url = f"{base_url}/{user_id}/{request_id}/{filename}"
                masks[mask_type] = url
        
        return masks
    
    return None
```

### 5. Error Handling

Monitor the `mask_input_poison` topic for messages that failed after max retries:

```python
poison_consumer = KafkaConsumer(
    'mask_input_poison',
    bootstrap_servers=['127.0.0.1:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

for message in poison_consumer:
    failed_message = message.value
    # Log or alert about failed message
    # Optionally, implement manual retry logic
```

### Integration Checklist

- [ ] Kafka topics created (`mask_input`, `mask_output`, `mask_input_poison`)
- [ ] Kafka producer configured to publish to `mask_input`
- [ ] Kafka consumer configured to consume from `mask_output`
- [ ] Database connection configured (if querying directly)
- [ ] Error handling implemented for poison queue
- [ ] Monitoring/logging setup for mask generation requests
- [ ] Base URL configured correctly for your environment

---

## API Documentation

### Input Message Format (`mask_input` topic)

#### Required Fields

- `user_id` (string): Unique user identifier
- `image` (object): Image data with `type` and `data` fields

#### Optional Fields

- `gender` (string): User gender - `"M"`, `"F"`, `"MALE"`, `"FEMALE"`, or `"other"` (default: `"other"`)
- `request_id` (string): Unique request identifier (auto-generated if not provided)
- `mask_types` (array): List of mask types to generate (default: all 7 types)

#### Image Object

- `type` (string): Either `"url"` or `"base64"`
- `data` (string): 
  - If `type` is `"url"`: HTTP/HTTPS URL to the image
  - If `type` is `"base64"`: Base64-encoded image data (with or without data URL prefix)

#### Example: URL Image

```json
{
  "user_id": "123",
  "gender": "M",
  "request_id": "req-123-001",
  "mask_types": ["upper_body", "lower_body", "ethnic_combined"],
  "image": {
    "type": "url",
    "data": "http://example.com/user_image.jpg"
  }
}
```

#### Example: Base64 Image

```json
{
  "user_id": "456",
  "gender": "F",
  "request_id": "req-456-002",
  "mask_types": ["upper_body_tshirts", "dress"],
  "image": {
    "type": "base64",
    "data": "iVBORw0KGgoAAAANSUhEUgAA..."
  }
}
```

### Output Message Format (`mask_output` topic)

#### Success Response

```json
{
  "user_id": "123",
  "gender": "M",
  "request_id": "req-123-001",
  "status": "completed",
  "mask_paths": {
    "upper_body": "http://127.0.0.1:9000/masks/123/req-123-001/upper_body_mask.png",
    "upper_body_tshirts": "http://127.0.0.1:9000/masks/123/req-123-001/upper_body_tshirts_mask.png",
    "upper_body_coat": "http://127.0.0.1:9000/masks/123/req-123-001/upper_body_coat_mask.png",
    "lower_body": "http://127.0.0.1:9000/masks/123/req-123-001/lower_body_mask.png",
    "ethnic_combined": "http://127.0.0.1:9000/masks/123/req-123-001/ethnic_combined_mask.png",
    "baggy_lower": "http://127.0.0.1:9000/masks/123/req-123-001/baggy_lower_mask.png",
    "dress": "http://127.0.0.1:9000/masks/123/req-123-001/dress_mask.png"
  },
  "processed_at": "2025-11-26T12:00:00Z"
}
```

#### Error Response

```json
{
  "user_id": "123",
  "gender": "M",
  "request_id": "req-123-001",
  "status": "failed",
  "error": "Failed to download image: HTTP 404",
  "mask_paths": {},
  "processed_at": "2025-11-26T12:00:00Z"
}
```

### Field Descriptions

- `user_id`: User identifier from input message
- `gender`: Normalized gender (`"M"` or `"F"`)
- `request_id`: Request identifier (from input or auto-generated)
- `status`: `"completed"` or `"failed"`
- `mask_paths`: Dictionary mapping mask_type to full URL (only present if status is `"completed"`)
- `error`: Error message (only present if status is `"failed"`)
- `processed_at`: ISO 8601 timestamp of processing completion

---

## Database Schema

### Table: `user_mask_outputs`

The service stores mask filenames (not full URLs) in PostgreSQL. Full URLs are constructed using `BASE_URL` configuration.

```sql
CREATE TABLE user_mask_outputs (
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
```

### Column Descriptions

- `user_id`: Primary key, unique user identifier
- `gender`: User gender (`"M"` or `"F"`)
- `request_id`: Request identifier for URL construction
- `upper_body_mask`: Filename for upper body mask (e.g., `"upper_body_mask.png"`)
- `upper_body_tshirts_mask`: Filename for T-shirts mask
- `upper_body_coat_mask`: Filename for coats/jackets mask
- `lower_body_mask`: Filename for lower body mask
- `ethnic_combined_mask`: Filename for ethnic combined mask
- `baggy_lower_mask`: Filename for baggy lower mask
- `dress_mask`: Filename for dress mask
- `updated_at`: Timestamp of last update

### URL Construction

To construct full URLs from database filenames:

```python
base_url = "http://127.0.0.1:9000/masks"  # From BASE_URL config
user_id = "123"
request_id = "req-123-001"
filename = "upper_body_mask.png"

full_url = f"{base_url}/{user_id}/{request_id}/{filename}"
# Result: http://127.0.0.1:9000/masks/123/req-123-001/upper_body_mask.png
```

### Query Examples

```sql
-- Get all masks for a user
SELECT * FROM user_mask_outputs WHERE user_id = '123';

-- Get specific mask types
SELECT user_id, upper_body_mask, lower_body_mask, dress_mask 
FROM user_mask_outputs 
WHERE user_id = '123';

-- Get recent updates
SELECT user_id, request_id, updated_at 
FROM user_mask_outputs 
ORDER BY updated_at DESC 
LIMIT 10;
```

---

## Supported Mask Types

The service supports 7 mask types, each optimized for different garment categories:

| Mask Type | Description | What It Masks |
|-----------|-------------|---------------|
| `upper_body` | Upper body segmentation | Upper clothes, arms, neck region |
| `upper_body_tshirts` | T-shirts mask | Upper clothes, arms with lower body coverage |
| `upper_body_coat` | Coats/jackets mask | Upper clothes, arms with lower body coverage |
| `lower_body` | Lower body segmentation | Pants, legs, skirt |
| `ethnic_combined` | Combined ethnic wear | Upper and lower body with shoes included |
| `baggy_lower` | Baggy pants mask | Lower body with larger dilation radius (includes shoes) |
| `dress` | Full body dress mask | Dress, upper clothes, skirt, pants, arms, neck region |

### Mask Type Selection

- **Default**: If `mask_types` is not provided, all 7 types are generated
- **Custom**: Specify only the types you need: `["upper_body", "lower_body"]`
- **Performance**: Generating fewer mask types reduces processing time

---

## Error Handling

### Retry Logic

The service implements automatic retry with exponential backoff:

- **Max Retries**: Configurable via `MAX_RETRIES` (default: 5)
- **Backoff**: Exponential backoff between retries
- **Retryable Errors**: Network errors, temporary failures, connection issues

### Poison Queue

Messages that fail after `MAX_RETRIES` are sent to the `mask_input_poison` topic:

```json
{
  "user_id": "123",
  "gender": "M",
  "request_id": "req-123-001",
  "status": "failed",
  "error": "Max retries exceeded: Failed to download image",
  "original_message": { ... },
  "retry_count": 5,
  "processed_at": "2025-11-26T12:00:00Z"
}
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Failed to download image: HTTP 404` | Image URL not accessible | Verify image URL is correct and accessible |
| `Invalid image data` | Corrupted base64 or invalid image format | Validate image before sending |
| `Database connection failed` | PostgreSQL unreachable | Check database connection and credentials |
| `MinIO upload failed` | Storage service unreachable | Check MinIO connection and permissions |
| `Mask generation failed` | Model error or invalid image | Check image format and model checkpoints |

### Error Monitoring

Monitor errors by:
1. Consuming `mask_output` topic and filtering `status == "failed"`
2. Consuming `mask_input_poison` topic for critical failures
3. Querying logs for error patterns
4. Setting up alerts for high error rates

---

## Monitoring & Logging

### Structured Logging

The service outputs structured JSON logs:

```json
{
  "timestamp": "2025-11-26T12:00:00Z",
  "level": "INFO",
  "logger": "maskcomponent.worker",
  "user_id": "123",
  "request_id": "req-123-001",
  "message": "Processing message for user_id: 123",
  "stage": "process_message",
  "event": "start"
}
```

### Log Levels

- **DEBUG**: Detailed debugging information
- **INFO**: General informational messages
- **WARNING**: Warning messages (non-critical issues)
- **ERROR**: Error messages (processing failures)
- **CRITICAL**: Critical errors (service failures)

### Key Metrics to Monitor

1. **Processing Rate**: Messages processed per second
2. **Error Rate**: Percentage of failed messages
3. **Processing Time**: Average time to generate masks
4. **Kafka Consumer Lag**: Delay in message consumption
5. **Database Connection Pool**: Active/idle connections
6. **GPU Utilization**: GPU usage during mask generation

### Health Checks

Monitor service health by:
- Checking Kafka consumer lag (should be low)
- Verifying PostgreSQL connection pool (should have available connections)
- Monitoring MinIO connectivity
- Reviewing error rates in logs

### Log Aggregation

For production, configure log aggregation:
- **ELK Stack**: Elasticsearch, Logstash, Kibana
- **Loki**: Grafana Loki for log aggregation
- **CloudWatch**: AWS CloudWatch Logs
- **Datadog**: Datadog log management

---

## Production Deployment

### Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install package
RUN pip install -e .

# Set environment variables (override in docker-compose or k8s)
ENV SERVICE_CONCURRENCY=4
ENV MAX_RETRIES=5

# Run service
CMD ["python", "-m", "maskcomponent.main"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  maskcomponent:
    build: .
    environment:
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=admin
      - MINIO_SECRET_KEY=admin123
      - MINIO_BUCKET=masks
      - BASE_URL=http://minio:9000/masks
      - POSTGRES_DSN=postgresql://user:pass@postgres:5432/db
      - SERVICE_CONCURRENCY=4
      - GPU_ID=0
    volumes:
      - ./checkpoints:/app/checkpoints
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    depends_on:
      - kafka
      - minio
      - postgres
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: maskcomponent
spec:
  replicas: 2
  selector:
    matchLabels:
      app: maskcomponent
  template:
    metadata:
      labels:
        app: maskcomponent
    spec:
      containers:
      - name: maskcomponent
        image: your-registry/maskcomponent:latest
        env:
        - name: KAFKA_BOOTSTRAP_SERVERS
          value: "kafka:9092"
        - name: MINIO_ENDPOINT
          value: "minio:9000"
        - name: POSTGRES_DSN
          valueFrom:
            secretKeyRef:
              name: maskcomponent-secrets
              key: postgres-dsn
        resources:
          requests:
            nvidia.com/gpu: 1
          limits:
            nvidia.com/gpu: 1
        volumeMounts:
        - name: checkpoints
          mountPath: /app/checkpoints
      volumes:
      - name: checkpoints
        persistentVolumeClaim:
          claimName: checkpoints-pvc
```

### Scaling Considerations

- **Horizontal Scaling**: Run multiple service instances (each with unique consumer group)
- **Partitioning**: Ensure Kafka topics have enough partitions for parallel processing
- **GPU Resources**: Each instance needs GPU access (consider GPU sharing)
- **Database Connections**: Monitor connection pool size with multiple instances

### Security Best Practices

1. **Secrets Management**: Use Kubernetes secrets, AWS Secrets Manager, or HashiCorp Vault
2. **Network Security**: Use TLS for Kafka and PostgreSQL connections
3. **Access Control**: Implement proper MinIO bucket policies
4. **Authentication**: Use SASL authentication for Kafka
5. **Image Validation**: Validate image URLs before processing (whitelist domains)

---

## Testing

### Unit Tests

```bash
# Run tests
pytest src/maskcomponent/tests/

# With coverage
pytest --cov=src/maskcomponent src/maskcomponent/tests/
```

### Integration Testing

Use the provided test tools:

```bash
# Send test message
python tools/send_image_message.py \
    --user-id 123 \
    --gender M \
    --image-path /path/to/image.jpg \
    --mask-types upper_body,lower_body

# Check results
python tools/get_mask_urls.py --user-id 123
```

### Load Testing

Test service under load:

```python
from kafka import KafkaProducer
import json
import time

producer = KafkaProducer(
    bootstrap_servers=['127.0.0.1:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Send 100 messages
for i in range(100):
    message = {
        "user_id": str(i),
        "gender": "M",
        "request_id": f"load-test-{i}",
        "mask_types": ["upper_body"],
        "image": {
            "type": "url",
            "data": "http://example.com/test_image.jpg"
        }
    }
    producer.send('mask_input', value=message)
    time.sleep(0.1)  # 10 messages per second

producer.flush()
```

---

## Troubleshooting

### Service Won't Start

**Problem**: Service fails to start

**Solutions**:
1. Check environment variables are set correctly
2. Verify Kafka, MinIO, and PostgreSQL are accessible
3. Check model checkpoints exist in `checkpoints/` directory
4. Review error logs for specific error messages

### Messages Not Processing

**Problem**: Messages in `mask_input` topic but not being processed

**Solutions**:
1. Check Kafka consumer group is correct
2. Verify consumer is connected to Kafka
3. Check for consumer lag: `kafka-consumer-groups.sh --bootstrap-server localhost:9092 --group maskcomponent-group --describe`
4. Review service logs for connection errors

### High Error Rate

**Problem**: Many messages failing

**Solutions**:
1. Check image URLs are accessible
2. Verify image format is supported (JPEG, PNG)
3. Check MinIO bucket permissions
4. Verify database connection pool isn't exhausted
5. Review error messages in logs for patterns

### Slow Processing

**Problem**: Masks taking too long to generate

**Solutions**:
1. Increase `SERVICE_CONCURRENCY` (if CPU/GPU allows)
2. Use GPU instead of CPU (`GPU_ID=0`)
3. Generate fewer mask types per request
4. Optimize image size before sending
5. Check for network latency to MinIO/PostgreSQL

### Database Connection Issues

**Problem**: Database connection errors

**Solutions**:
1. Verify `POSTGRES_DSN` format is correct
2. Check database is accessible from service
3. Verify connection pool size isn't too small
4. Check for connection leaks in logs

### MinIO Upload Failures

**Problem**: Masks not uploading to MinIO

**Solutions**:
1. Verify MinIO endpoint is correct
2. Check access key and secret key
3. Verify bucket exists and is accessible
4. Check network connectivity to MinIO
5. Verify bucket policies allow write access

---

## Project Structure

```
maskcomponent/
├── src/
│   └── maskcomponent/          # Core service code
│       ├── __init__.py
│       ├── main.py             # Service entry point
│       ├── config.py            # Configuration management
│       ├── logger.py             # Structured logging
│       ├── storage.py            # MinIO integration
│       ├── db.py                 # PostgreSQL integration
│       ├── kafka_producer.py     # Kafka producer
│       ├── kafka_consumer.py     # Kafka consumer
│       ├── worker.py             # Message processing logic
│       ├── mask_gen.py           # Mask generation wrapper
│       └── url_helper.py         # URL construction utilities
├── mask_generation/             # Mask generation module
│   ├── models.py                # Model loading
│   ├── mask_generator.py        # Mask generation logic
│   ├── mask_generator_fast.py   # Optimized generator
│   └── utils.py                 # Utility functions
├── preprocess/                  # Preprocessing dependencies
│   ├── detectron2/              # Detectron2 library
│   ├── humanparsing/            # Human parsing models
│   └── openpose/                # OpenPose models
├── checkpoints/                 # Model checkpoints (excluded from git)
├── scripts/                     # Setup and utility scripts
│   ├── setup_env.sh             # Environment setup
│   ├── start_kafka.sh            # Kafka startup script
│   └── create_topics.sh          # Topic creation script
├── tools/                       # Helper tools
│   ├── send_image_message.py    # Send test messages
│   ├── get_mask_urls.py          # Query mask URLs
│   └── migrate_add_mask_types.py # Database migration
├── docs/                        # Documentation
│   ├── API.md                   # API documentation
│   ├── PROJECT_STRUCTURE.md      # Project structure
│   └── TROUBLESHOOTING.md        # Troubleshooting guide
├── examples/                     # Example messages
│   ├── example_input.json        # Example input message
│   └── example_input_base64.json # Example base64 message
├── requirements.txt              # Python dependencies
├── setup.py                      # Package setup
├── pyproject.toml               # Project configuration
└── README.md                     # This file
```

---

## Support & Contact

For issues, questions, or contributions:

- **GitHub Issues**: [Create an issue](https://github.com/safuaaannn/maskcomponent/issues)
- **Documentation**: See `docs/` directory for detailed documentation
- **Examples**: See `examples/` directory for message examples

---

## License

[Your License Here]

---

## Changelog

### Version 1.0.0 (Current)

- ✅ Production-ready mask generation service
- ✅ Support for 7 mask types
- ✅ Kafka-based message processing
- ✅ MinIO/S3 storage integration
- ✅ PostgreSQL metadata storage
- ✅ Comprehensive error handling
- ✅ Structured logging
- ✅ Docker and Kubernetes support

---

**Last Updated**: November 2025

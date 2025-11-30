# Mask Component Service

Production-grade Python microservice for generating human segmentation masks from images using Kafka, MinIO, and PostgreSQL.

## Overview

The Mask Component Service consumes Kafka messages containing image data, generates multiple types of segmentation masks (upper body, lower body, ethnic combined) using OpenPose and Human Parsing models, stores the masks in MinIO object storage, and records metadata in PostgreSQL.

## Architecture

```
┌─────────────┐
│   Kafka     │  mask_input topic
│  Producer   │ ──────────────┐
└─────────────┘                │
                               ▼
                        ┌──────────────┐
                        │ Mask Service │
                        │  (Consumer)  │
                        └──────────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
         ┌──────────┐   ┌──────────┐  ┌──────────┐
         │  MinIO   │   │PostgreSQL │  │  Kafka   │
         │ Storage  │   │ Database  │  │ Producer │
         └──────────┘   └──────────┘  └──────────┘
                               │
                               ▼
                        mask_output topic
```

## Features

- **Asynchronous Processing**: Built with `asyncio` for high concurrency
- **Multiple Mask Types**: Supports `upper_body`, `lower_body`, `ethnic_combined`
- **Robust Error Handling**: Retry logic with exponential backoff, poison queue support
- **Structured Logging**: JSON-formatted logs for centralized monitoring
- **Model Optimization**: Models initialized once at startup for efficiency
- **Idempotent Operations**: Safe to retry without side effects
- **Production Ready**: Comprehensive error handling, graceful shutdown, health checks

## Prerequisites

- **Python**: 3.10 or higher
- **GPU**: CUDA-capable GPU (recommended) or CPU fallback
- **Kafka**: Accessible Kafka broker
- **MinIO**: S3-compatible object storage
- **PostgreSQL**: Database server
- **Model Checkpoints**: Required model files in `checkpoints/` directory

## Quick Start

### 1. Installation

```bash
# Clone repository
git clone <repository-url>
cd maskcomponent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Copy and edit the environment configuration:

```bash
cp scripts/setup_env.sh .env
# Edit .env with your settings
```

Required environment variables:

```bash
# Kafka
export KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9092

# MinIO
export MINIO_ENDPOINT=127.0.0.1:9000
export MINIO_ACCESS_KEY=admin
export MINIO_SECRET_KEY=admin123
export MINIO_BUCKET=masks
export BASE_URL=http://127.0.0.1:9000/masks

# PostgreSQL
export POSTGRES_DSN=postgresql://user:password@host:5432/database

# Service
export SERVICE_CONCURRENCY=4
export GPU_ID=0
```

### 3. Setup Infrastructure

**Start Kafka:**
```bash
./scripts/start_kafka.sh
```

**Create Kafka Topics:**
```bash
./scripts/create_topics.sh
```

**Ensure MinIO is running** (default: `http://127.0.0.1:9000`)

**Ensure PostgreSQL is accessible**

### 4. Run Service

```bash
# Load environment variables
source scripts/setup_env.sh

# Run service
python -m maskcomponent.main
```

Or use the wrapper script:

```bash
python run_maskcomponent.py
```

## Project Structure

```
maskcomponent/
├── src/
│   └── maskcomponent/          # Core service code
│       ├── __init__.py
│       ├── main.py             # Service entry point
│       ├── config.py            # Configuration management
│       ├── logger.py            # Structured logging
│       ├── storage.py           # MinIO integration
│       ├── db.py                # PostgreSQL integration
│       ├── kafka_producer.py    # Kafka producer
│       ├── kafka_consumer.py    # Kafka consumer
│       ├── worker.py            # Message processing logic
│       ├── mask_gen.py          # Mask generation wrapper
│       └── url_helper.py        # URL construction utilities
├── mask_generation/             # Mask generation module
├── preprocess/                  # Preprocessing dependencies
├── checkpoints/                 # Model checkpoints
├── scripts/                     # Setup and utility scripts
├── tools/                       # Helper tools
├── docs/                        # Documentation
├── examples/                    # Example messages
├── requirements.txt             # Python dependencies
├── pyproject.toml               # Project configuration
└── README.md                    # This file
```

## Message Format

### Input Message (mask_input topic)

```json
{
  "user_id": "123",
  "gender": "M",
  "request_id": "req-123-001",
  "mask_types": ["upper_body", "lower_body", "ethnic_combined"],
  "image": {
    "type": "url",
    "data": "http://example.com/image.jpg"
  }
}
```

### Output Message (mask_output topic)

```json
{
  "user_id": "123",
  "gender": "M",
  "request_id": "req-123-001",
  "status": "completed",
  "mask_paths": {
    "upper_body": "http://127.0.0.1:9000/masks/123/req-123-001/upper_body_mask.png",
    "lower_body": "http://127.0.0.1:9000/masks/123/req-123-001/lower_body_mask.png",
    "ethnic_combined": "http://127.0.0.1:9000/masks/123/req-123-001/ethnic_combined_mask.png"
  },
  "processed_at": "2025-11-26T12:00:00Z"
}
```

## Database Schema

```sql
CREATE TABLE user_mask_outputs (
    user_id TEXT PRIMARY KEY,
    gender TEXT,
    request_id TEXT,
    upper_body_mask TEXT,
    lower_body_mask TEXT,
    ethnic_combined_mask TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

## Configuration

All configuration is done via environment variables. See `scripts/setup_env.sh` for defaults.

### Key Settings

- `SERVICE_CONCURRENCY`: Number of concurrent message processors (default: 4)
- `MAX_RETRIES`: Maximum retry attempts for failed messages (default: 5)
- `PRESIGNED_URL_EXPIRY`: MinIO presigned URL expiry in seconds (default: 604800 = 7 days)
- `BASE_URL`: Base URL for constructing mask file URLs
- `GPU_ID`: GPU device ID for mask generation (default: 0)

## Monitoring

### Logs

The service outputs structured JSON logs:

```json
{
  "timestamp": "2025-11-26T12:00:00Z",
  "level": "INFO",
  "logger": "maskcomponent.worker",
  "user_id": "123",
  "request_id": "req-123-001",
  "message": "Processing message for user_id: 123"
}
```

### Health Checks

Monitor the service by:
- Checking Kafka consumer lag
- Monitoring PostgreSQL connection pool
- Verifying MinIO connectivity
- Reviewing error rates in logs

## Error Handling

- **Retry Logic**: Automatic retries with exponential backoff
- **Poison Queue**: Failed messages after max retries sent to `mask_input_poison` topic
- **Graceful Shutdown**: Handles SIGINT/SIGTERM for clean shutdown
- **Connection Pooling**: Database and Kafka connections are pooled and managed

## Development

### Running Tests

```bash
pytest src/maskcomponent/tests/
```

### Code Quality

```bash
# Format code
black src/

# Lint code
flake8 src/

# Type checking
mypy src/
```

## Troubleshooting

See `docs/TROUBLESHOOTING.md` for common issues and solutions.

## License

[Your License Here]

## Support

[Your Support Information Here]



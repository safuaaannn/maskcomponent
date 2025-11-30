# Project Structure

## Directory Layout

```
maskcomponent/
├── src/
│   └── maskcomponent/          # Core service code
│       ├── __init__.py
│       ├── main.py             # Service entry point
│       ├── config.py            # Configuration management
│       ├── logger.py            # Structured JSON logging
│       ├── storage.py           # MinIO/S3 integration
│       ├── db.py                # PostgreSQL integration
│       ├── kafka_producer.py    # Kafka producer
│       ├── kafka_consumer.py    # Kafka consumer
│       ├── worker.py            # Message processing logic
│       ├── mask_gen.py          # Mask generation wrapper
│       ├── url_helper.py        # URL construction utilities
│       └── tests/               # Unit tests
│
├── mask_generation/             # Mask generation module
│   ├── models.py               # Model initialization
│   ├── mask_generator.py       # Mask generation logic
│   └── utils.py                # Utility functions
│
├── preprocess/                 # Preprocessing dependencies
│   ├── openpose/               # OpenPose integration
│   ├── humanparsing/            # Human parsing models
│   └── detectron2/             # Detectron2 framework
│
├── checkpoints/                # Model checkpoints
│   ├── openpose/
│   ├── humanparsing/
│   └── hulk/
│
├── scripts/                    # Setup and deployment scripts
│   ├── setup_env.sh            # Environment configuration
│   ├── start_kafka.sh          # Kafka startup script
│   └── create_topics.sh        # Topic creation script
│
├── tools/                      # Utility tools
│   ├── send_image_message.py   # Send test messages
│   ├── get_mask_urls.py        # Get mask URLs from DB
│   ├── get_presigned_urls.py   # Generate presigned URLs
│   ├── check_user.py           # Check user in database
│   ├── check_results.py         # Check processing results
│   └── migrate_database.py      # Database migration tool
│
├── docs/                       # Documentation
│   ├── API.md                  # API documentation
│   ├── DEPLOYMENT.md           # Deployment guide
│   └── [other docs]
│
├── examples/                   # Example messages
│   ├── example_input.json      # Example input message
│   └── example_input_base64.json
│
├── README.md                   # Main documentation
├── requirements.txt            # Python dependencies
├── pyproject.toml              # Project configuration
├── setup.py                    # Package setup
├── run_maskcomponent.py        # Service entry point
└── .gitignore                  # Git ignore rules
```

## Key Files

### Service Entry Points
- `run_maskcomponent.py`: Production entry point wrapper
- `src/maskcomponent/main.py`: Main service implementation

### Configuration
- `scripts/setup_env.sh`: Environment variable template
- `src/maskcomponent/config.py`: Configuration management

### Core Components
- `src/maskcomponent/worker.py`: Message processing logic
- `src/maskcomponent/storage.py`: MinIO storage operations
- `src/maskcomponent/db.py`: Database operations
- `src/maskcomponent/kafka_*.py`: Kafka integration

### Utilities
- `tools/`: Helper scripts for testing and debugging
- `scripts/`: Setup and deployment scripts

## File Organization Principles

1. **Core Service**: All production code in `src/maskcomponent/`
2. **Dependencies**: External modules in `mask_generation/` and `preprocess/`
3. **Scripts**: Setup scripts in `scripts/`, utilities in `tools/`
4. **Documentation**: All docs in `docs/` directory
5. **Examples**: Sample messages in `examples/`

## Production Considerations

- **No test files in root**: All test scripts moved to `tools/`
- **Clean root directory**: Only essential files at root level
- **Organized docs**: All documentation consolidated in `docs/`
- **Version control**: `.gitignore` excludes temporary files


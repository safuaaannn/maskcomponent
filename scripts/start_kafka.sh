#!/bin/bash
# Quick script to start Kafka and create topics

set -e

echo "=" | head -c 70 && echo ""
echo "Starting Kafka for Mask Component Service"
echo "=" | head -c 70 && echo ""

# Check if Kafka is already running
if docker ps --format '{{.Names}}' | grep -q "^kafka$"; then
    echo "✓ Kafka container already running"
    KAFKA_RUNNING=true
else
    echo "Starting Kafka container..."
    docker run -d --name kafka -p 9092:9092 apache/kafka:latest
    KAFKA_RUNNING=false
fi

# Wait for Kafka to be ready
if [ "$KAFKA_RUNNING" = false ]; then
    echo "Waiting for Kafka to start (15 seconds)..."
    sleep 15
fi

# Check if Kafka is responding
echo "Checking Kafka connection..."
if nc -z localhost 9092 2>/dev/null; then
    echo "✓ Kafka is accessible on port 9092"
else
    echo "⚠ Kafka port not accessible yet, waiting a bit more..."
    sleep 10
    if ! nc -z localhost 9092 2>/dev/null; then
        echo "✗ Kafka is not responding. Check logs: docker logs kafka"
        exit 1
    fi
fi

# Create topics
echo ""
echo "Creating Kafka topics..."

create_topic() {
    local topic=$1
    # Try different paths for kafka-topics.sh
    KAFKA_TOPICS_CMD=""
    if docker exec kafka /opt/kafka/bin/kafka-topics.sh --version >/dev/null 2>&1; then
        KAFKA_TOPICS_CMD="/opt/kafka/bin/kafka-topics.sh"
    elif docker exec kafka kafka-topics.sh --version >/dev/null 2>&1; then
        KAFKA_TOPICS_CMD="kafka-topics.sh"
    elif docker exec kafka /usr/bin/kafka-topics.sh --version >/dev/null 2>&1; then
        KAFKA_TOPICS_CMD="/usr/bin/kafka-topics.sh"
    else
        echo "  ✗ Could not find kafka-topics.sh"
        return 1
    fi
    
    if docker exec kafka $KAFKA_TOPICS_CMD --bootstrap-server localhost:9092 --list 2>/dev/null | grep -q "^${topic}$"; then
        echo "  ✓ Topic '$topic' already exists"
    else
        docker exec kafka $KAFKA_TOPICS_CMD --create \
            --bootstrap-server localhost:9092 \
            --topic "$topic" \
            --partitions 1 \
            --replication-factor 1 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "  ✓ Created topic '$topic'"
        else
            echo "  ✗ Failed to create topic '$topic'"
        fi
    fi
}

create_topic "mask_input"
create_topic "mask_output"
create_topic "mask_input_poison"

# List all topics
echo ""
echo "Available topics:"
# Try different paths
if docker exec kafka /opt/kafka/bin/kafka-topics.sh --version >/dev/null 2>&1; then
    docker exec kafka /opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092
elif docker exec kafka kafka-topics.sh --version >/dev/null 2>&1; then
    docker exec kafka kafka-topics.sh --list --bootstrap-server localhost:9092
else
    echo "  (Could not list topics - but Kafka is running)"
fi

echo ""
echo "=" | head -c 70 && echo ""
echo "✓ Kafka is ready!"
echo "=" | head -c 70 && echo ""
echo ""
echo "Next steps:"
echo "  1. Set environment: source setup_env.sh"
echo "  2. Run service: python run_maskcomponent.py"
echo ""


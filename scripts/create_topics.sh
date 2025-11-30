#!/bin/bash
# Create Kafka topics - run after Kafka is started

echo "Creating Kafka topics..."

# Use the correct path for kafka-topics.sh
KAFKA_CMD="/opt/kafka/bin/kafka-topics.sh"

# Create topics
docker exec kafka $KAFKA_CMD --create --bootstrap-server localhost:9092 --topic mask_input --partitions 1 --replication-factor 1 2>/dev/null && echo "✓ mask_input" || echo "  mask_input (may already exist)"

docker exec kafka $KAFKA_CMD --create --bootstrap-server localhost:9092 --topic mask_output --partitions 1 --replication-factor 1 2>/dev/null && echo "✓ mask_output" || echo "  mask_output (may already exist)"

docker exec kafka $KAFKA_CMD --create --bootstrap-server localhost:9092 --topic mask_input_poison --partitions 1 --replication-factor 1 2>/dev/null && echo "✓ mask_input_poison" || echo "  mask_input_poison (may already exist)"

echo ""
echo "Listing all topics:"
docker exec kafka $KAFKA_CMD --list --bootstrap-server localhost:9092

echo ""
echo "✓ Done!"


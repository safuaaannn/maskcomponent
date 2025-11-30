#!/usr/bin/env python
"""
Simple script to send image message to Kafka
Usage: python send_image_message.py --user-id 7 --gender M --image-path 2.png --mask-types upper_body,lower_body
"""
import json
import sys
import argparse
from pathlib import Path
from kafka import KafkaProducer
from minio import Minio
from minio.error import S3Error
import io
from datetime import timedelta

def upload_to_minio(image_path, user_id, request_id):
    """Upload image to MinIO and return presigned URL"""
    client = Minio(
        endpoint="127.0.0.1:9000",
        access_key="admin",
        secret_key="admin123",
        secure=False
    )
    
    bucket_name = "masks"
    try:
        if not client.bucket_exists(bucket_name=bucket_name):
            client.make_bucket(bucket_name=bucket_name)
    except S3Error:
        pass
    
    # Upload as PNG
    object_name = f"input_images/{user_id}/{request_id}/original.png"
    
    with open(image_path, 'rb') as file_data:
        image_bytes = file_data.read()
        client.put_object(
            bucket_name=bucket_name,
            object_name=object_name,
            data=io.BytesIO(image_bytes),
            length=len(image_bytes),
            content_type="image/png"
        )
    
    # Generate presigned URL (7 days)
    url = client.presigned_get_object(
        bucket_name=bucket_name,
        object_name=object_name,
        expires=timedelta(days=7)
    )
    
    return url

def send_message(user_id, gender, image_path, mask_types=None):
    """Send message to Kafka"""
    
    # Check image exists
    if not Path(image_path).exists():
        print(f"✗ Error: Image file not found: {image_path}")
        return False
    
    request_id = f"test-{user_id}-{gender}"
    
    # Default mask types if not provided
    if mask_types is None:
        mask_types = ["upper_body", "lower_body", "ethnic_combined"]
    elif isinstance(mask_types, str):
        mask_types = [m.strip() for m in mask_types.split(",")]
    
    print("=" * 70)
    print("Sending Image Message to Kafka")
    print("=" * 70)
    print(f"Image: {image_path}")
    print(f"User ID: {user_id}")
    print(f"Gender: {gender}")
    print(f"Request ID: {request_id}")
    print(f"Mask Types: {', '.join(mask_types)}")
    print()
    
    # Step 1: Upload to MinIO
    print("Step 1: Uploading image to MinIO...")
    try:
        image_url = upload_to_minio(image_path, user_id, request_id)
        print(f"✓ Image uploaded: {image_url[:80]}...")
    except Exception as e:
        print(f"✗ Failed to upload: {e}")
        return False
    
    # Step 2: Create message
    message = {
        "user_id": str(user_id),
        "gender": gender,
        "request_id": request_id,
        "mask_types": mask_types,
        "image": {
            "type": "url",
            "data": image_url
        }
    }
    
    # Step 3: Send to Kafka
    print("\nStep 2: Sending message to Kafka...")
    try:
        producer = KafkaProducer(
            bootstrap_servers=["127.0.0.1:9092"],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        producer.send("mask_input", value=message)
        producer.flush()
        producer.close()
        
        print("✓ Message sent successfully!")
        print()
        print("=" * 70)
        print("✅ SUCCESS!")
        print("=" * 70)
        print(f"Message sent to topic: mask_input")
        print(f"User ID: {user_id}")
        print(f"Gender: {gender}")
        print()
        print("The service will process this message in 20-40 seconds.")
        print()
        print("To check results:")
        print("  1. Watch service logs (where run_maskcomponent.py is running)")
        print("  2. Check database: python check_results.py")
        print("  3. Check Kafka output: ./show_all_kafka.sh")
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"✗ Failed to send message: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send image message to Kafka")
    parser.add_argument("--user-id", type=str, default="2", help="User ID")
    parser.add_argument("--gender", type=str, default="M", help="Gender (M/F)")
    parser.add_argument("--image-path", type=str, required=True, help="Path to image file")
    parser.add_argument("--mask-types", type=str, help="Comma-separated mask types (default: upper_body,lower_body,ethnic_combined)")
    
    args = parser.parse_args()
    
    success = send_message(args.user_id, args.gender, args.image_path, args.mask_types)
    sys.exit(0 if success else 1)


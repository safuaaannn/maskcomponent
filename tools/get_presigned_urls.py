#!/usr/bin/env python
"""
Get presigned URLs for mask images from database
This script generates working MinIO URLs that can be accessed directly
"""
import asyncio
import asyncpg
import os
import sys
sys.path.insert(0, 'src')

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Try to load from setup_env.sh
setup_env_path = os.path.join(os.path.dirname(__file__), 'setup_env.sh')
if os.path.exists(setup_env_path):
    import subprocess
    result = subprocess.run(
        f'source {setup_env_path} && env',
        shell=True,
        capture_output=True,
        text=True,
        executable='/bin/bash'
    )
    for line in result.stdout.splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            os.environ[key] = value

from minio import Minio
from datetime import timedelta

async def get_presigned_urls(user_id: str = None):
    """Get presigned URLs for mask images"""
    
    # MinIO config
    minio_endpoint = os.getenv("MINIO_ENDPOINT", "127.0.0.1:9000")
    minio_access_key = os.getenv("MINIO_ACCESS_KEY", "admin")
    minio_secret_key = os.getenv("MINIO_SECRET_KEY", "admin123")
    minio_secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
    minio_bucket = os.getenv("MINIO_BUCKET", "masks")
    
    # PostgreSQL config
    dsn = os.getenv("POSTGRES_DSN", "postgresql://admin_user:fashionX%404031@127.0.0.1:5432/kafka_db")
    
    print("=" * 70)
    print("GETTING PRESIGNED URLs FOR MASK IMAGES")
    print("=" * 70)
    print(f"MinIO: {minio_endpoint}")
    print(f"Bucket: {minio_bucket}")
    print()
    
    try:
        # Connect to database
        conn = await asyncpg.connect(dsn)
        
        # Get user records
        if user_id:
            query = """
                SELECT user_id, gender, request_id, upper_body_mask, lower_body_mask, ethnic_combined_mask
                FROM user_mask_outputs
                WHERE user_id = $1;
            """
            rows = await conn.fetch(query, user_id)
        else:
            query = """
                SELECT user_id, gender, request_id, upper_body_mask, lower_body_mask, ethnic_combined_mask
                FROM user_mask_outputs
                ORDER BY updated_at DESC;
            """
            rows = await conn.fetch(query)
        
        if not rows:
            print("No records found")
            await conn.close()
            return
        
        # Connect to MinIO
        minio_client = Minio(
            endpoint=minio_endpoint,
            access_key=minio_access_key,
            secret_key=minio_secret_key,
            secure=minio_secure
        )
        
        print(f"Found {len(rows)} record(s)\n")
        
        # Generate presigned URLs
        for row in rows:
            uid = row['user_id']
            gender = row['gender']
            request_id = row.get('request_id') or f"test-{uid}-{gender}"
            
            print(f"{'=' * 70}")
            print(f"User ID: {uid}, Gender: {gender}, Request ID: {request_id}")
            print(f"{'=' * 70}")
            print()
            print("Presigned URLs (valid for 7 days):")
            print()
            
            # Generate presigned URL for each mask
            mask_types = {
                'upper_body': row.get('upper_body_mask'),
                'lower_body': row.get('lower_body_mask'),
                'ethnic_combined': row.get('ethnic_combined_mask')
            }
            
            for mask_type, filename in mask_types.items():
                if filename:
                    # Construct storage key (full path in MinIO)
                    storage_key = f"{uid}/{request_id}/{filename}"
                    
                    try:
                        # Generate presigned URL (valid for 7 days)
                        url = minio_client.presigned_get_object(
                            bucket_name=minio_bucket,
                            object_name=storage_key,
                            expires=timedelta(days=7)
                        )
                        print(f"  • {mask_type}:")
                        print(f"    {url}")
                        print()
                    except Exception as e:
                        print(f"  • {mask_type}: ERROR - {e}")
                        print()
                else:
                    print(f"  • {mask_type}: (not available)")
                    print()
            
            print()
        
        await conn.close()
        
        print("=" * 70)
        print("NOTE:")
        print("  • These URLs are presigned and work directly in browser")
        print("  • URLs expire after 7 days")
        print("  • To regenerate, run this script again")
        print("=" * 70)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    user_id = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(get_presigned_urls(user_id))


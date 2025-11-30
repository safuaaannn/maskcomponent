#!/usr/bin/env python
"""
Helper script to get full mask URLs from database
Shows how to construct URLs using base_url from config
"""
import asyncio
import asyncpg
import os
import sys
sys.path.insert(0, 'src')

# Load environment variables if setup_env.sh exists
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

from maskcomponent.config import load_config

async def get_mask_urls(user_id: str = None):
    """Get full mask URLs for user(s)"""
    
    # Load config to get base_url
    _, _, _, service_config = load_config()
    base_url = service_config.base_url
    
    print("=" * 70)
    print("GETTING MASK URLs")
    print("=" * 70)
    print(f"Base URL: {base_url}")
    print()
    
    dsn = os.getenv("POSTGRES_DSN", "postgresql://admin_user:fashionX%404031@127.0.0.1:5432/kafka_db")
    
    try:
        conn = await asyncpg.connect(dsn)
        
        # Check if request_id column exists
        columns = await conn.fetch("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'user_mask_outputs' AND column_name = 'request_id';
        """)
        has_request_id = len(columns) > 0
        
        if user_id:
            # Get specific user
            if has_request_id:
                query = """
                    SELECT user_id, gender, request_id, 
                        upper_body_mask, upper_body_tshirts_mask, upper_body_coat_mask,
                        lower_body_mask, ethnic_combined_mask, baggy_lower_mask, dress_mask
                    FROM user_mask_outputs
                    WHERE user_id = $1;
                """
            else:
                query = """
                    SELECT user_id, gender, 
                        upper_body_mask, upper_body_tshirts_mask, upper_body_coat_mask,
                        lower_body_mask, ethnic_combined_mask, baggy_lower_mask, dress_mask
                    FROM user_mask_outputs
                    WHERE user_id = $1;
                """
            rows = await conn.fetch(query, user_id)
        else:
            # Get all users
            if has_request_id:
                query = """
                    SELECT user_id, gender, request_id, 
                        upper_body_mask, upper_body_tshirts_mask, upper_body_coat_mask,
                        lower_body_mask, ethnic_combined_mask, baggy_lower_mask, dress_mask
                    FROM user_mask_outputs
                    ORDER BY updated_at DESC;
                """
            else:
                query = """
                    SELECT user_id, gender, 
                        upper_body_mask, upper_body_tshirts_mask, upper_body_coat_mask,
                        lower_body_mask, ethnic_combined_mask, baggy_lower_mask, dress_mask
                    FROM user_mask_outputs
                    ORDER BY updated_at DESC;
                """
            rows = await conn.fetch(query)
        
        if not rows:
            print("No records found")
            await conn.close()
            return
        
        print(f"Found {len(rows)} record(s)\n")
        
        for row in rows:
            uid = row['user_id']
            gender = row['gender']
            # Get request_id from row if exists, otherwise construct it
            request_id = row.get('request_id')
            if not request_id:
                # Fallback: construct request_id from pattern
                request_id = f"test-{uid}-{gender}"
                print(f"⚠ Note: request_id column not found, using pattern: {request_id}")
            
            print(f"User ID: {uid}, Gender: {gender}")
            print(f"Request ID: {request_id}")
            print()
            print("Full URLs:")
            
            # All mask types
            mask_types = [
                ('upper_body_mask', 'upper_body'),
                ('upper_body_tshirts_mask', 'upper_body_tshirts'),
                ('upper_body_coat_mask', 'upper_body_coat'),
                ('lower_body_mask', 'lower_body'),
                ('ethnic_combined_mask', 'ethnic_combined'),
                ('baggy_lower_mask', 'baggy_lower'),
                ('dress_mask', 'dress')
            ]
            
            # Construct full URLs for all mask types
            for col_name, mask_type in mask_types:
                if row.get(col_name):
                    url = f"{base_url}/{uid}/{request_id}/{row[col_name]}"
                    print(f"  • {mask_type}: {url}")
            
            print()
        
        await conn.close()
        
        print("=" * 70)
        print("To change the base URL/IP:")
        print("  1. Update BASE_URL in setup_env.sh or .env")
        print("  2. Restart service")
        print("=" * 70)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Get mask URLs from database")
    parser.add_argument("--user-id", type=str, help="User ID to query (optional, shows all if not provided)")
    args = parser.parse_args()
    
    user_id = args.user_id if args.user_id else (sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else None)
    asyncio.run(get_mask_urls(user_id))


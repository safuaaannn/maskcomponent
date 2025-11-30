#!/usr/bin/env python
"""
Migration script to add new mask type columns to existing database:
- upper_body_tshirts_mask
- upper_body_coat_mask
- baggy_lower_mask
- dress_mask

This script adds columns to the existing table without dropping data.
"""
import asyncio
import asyncpg
import os

async def migrate():
    """Add new mask type columns to database"""
    dsn = os.getenv("POSTGRES_DSN", "postgresql://admin_user:fashionX%404031@127.0.0.1:5432/kafka_db")
    
    print("=" * 70)
    print("DATABASE MIGRATION: Adding New Mask Type Columns")
    print("=" * 70)
    print()
    
    try:
        conn = await asyncpg.connect(dsn)
        
        # Check existing columns
        print("Step 1: Checking existing schema...")
        columns = await conn.fetch("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'user_mask_outputs'
            ORDER BY ordinal_position;
        """)
        
        existing_columns = {col['column_name'] for col in columns}
        print(f"  Found {len(existing_columns)} existing columns:")
        for col in columns:
            print(f"    - {col['column_name']}")
        
        # New columns to add
        new_columns = {
            'upper_body_tshirts_mask': 'TEXT',
            'upper_body_coat_mask': 'TEXT',
            'baggy_lower_mask': 'TEXT',
            'dress_mask': 'TEXT'
        }
        
        # Step 2: Add new columns
        print("\nStep 2: Adding new columns...")
        added_count = 0
        for col_name, col_type in new_columns.items():
            if col_name in existing_columns:
                print(f"  ⚠ {col_name} already exists, skipping")
            else:
                try:
                    await conn.execute(f"""
                        ALTER TABLE user_mask_outputs 
                        ADD COLUMN IF NOT EXISTS {col_name} {col_type};
                    """)
                    print(f"  ✓ Added {col_name}")
                    added_count += 1
                except Exception as e:
                    print(f"  ✗ Failed to add {col_name}: {e}")
        
        if added_count == 0:
            print("  All columns already exist, no changes needed")
        
        # Step 3: Verify final schema
        print("\nStep 3: Verifying final schema...")
        final_columns = await conn.fetch("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'user_mask_outputs'
            ORDER BY ordinal_position;
        """)
        print("  Final columns:")
        for col in final_columns:
            print(f"    - {col['column_name']}: {col['data_type']}")
        
        # Step 4: Check data integrity
        print("\nStep 4: Checking data integrity...")
        row_count = await conn.fetchval("SELECT COUNT(*) FROM user_mask_outputs;")
        print(f"  Total records: {row_count}")
        
        if row_count > 0:
            # Check for any NULL values in new columns (expected for existing data)
            null_counts = {}
            for col_name in new_columns.keys():
                count = await conn.fetchval(f"""
                    SELECT COUNT(*) 
                    FROM user_mask_outputs 
                    WHERE {col_name} IS NULL;
                """)
                null_counts[col_name] = count
            
            print("  NULL values in new columns (expected for existing data):")
            for col_name, count in null_counts.items():
                print(f"    - {col_name}: {count} NULL values")
        
        await conn.close()
        
        print("\n" + "=" * 70)
        print("✅ MIGRATION COMPLETE!")
        print("=" * 70)
        print()
        print("New columns added:")
        print("  - upper_body_tshirts_mask (TEXT)")
        print("  - upper_body_coat_mask (TEXT)")
        print("  - baggy_lower_mask (TEXT)")
        print("  - dress_mask (TEXT)")
        print()
        print("Note: Existing data will have NULL values in new columns")
        print("Note: New mask generation will populate these columns")
        print()
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(migrate())
    exit(0 if success else 1)


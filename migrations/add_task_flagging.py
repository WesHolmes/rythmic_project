#!/usr/bin/env python3
"""
Migration to add task flagging functionality
Adds fields to track flagged tasks that need clarification
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from sqlalchemy import text, inspect
from datetime import datetime

def add_task_flagging_fields():
    """Add flagging fields to task table"""
    try:
        with db.engine.connect() as conn:
            # Check if columns already exist
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('task')]
            
            new_columns = ['is_flagged', 'flag_comment', 'flagged_by', 'flagged_at', 'flag_resolved', 'flag_resolved_at', 'flag_resolved_by']
            existing_columns = [col for col in new_columns if col in columns]
            
            if len(existing_columns) == len(new_columns):
                print("✓ All flagging columns already exist")
                return True
            
            print(f"Adding {len(new_columns) - len(existing_columns)} flagging columns...")
            
            # Add is_flagged column
            if 'is_flagged' not in columns:
                conn.execute(text("""
                    ALTER TABLE task 
                    ADD is_flagged BIT DEFAULT 0
                """))
                print("✓ Added 'is_flagged' column")
            
            # Add flag_comment column
            if 'flag_comment' not in columns:
                conn.execute(text("""
                    ALTER TABLE task 
                    ADD flag_comment TEXT
                """))
                print("✓ Added 'flag_comment' column")
            
            # Add flagged_by column
            if 'flagged_by' not in columns:
                conn.execute(text("""
                    ALTER TABLE task 
                    ADD flagged_by INTEGER REFERENCES [user](id)
                """))
                print("✓ Added 'flagged_by' column")
            
            # Add flagged_at column
            if 'flagged_at' not in columns:
                conn.execute(text("""
                    ALTER TABLE task 
                    ADD flagged_at DATETIME2
                """))
                print("✓ Added 'flagged_at' column")
            
            # Add flag_resolved column
            if 'flag_resolved' not in columns:
                conn.execute(text("""
                    ALTER TABLE task 
                    ADD flag_resolved BIT DEFAULT 0
                """))
                print("✓ Added 'flag_resolved' column")
            
            # Add flag_resolved_at column
            if 'flag_resolved_at' not in columns:
                conn.execute(text("""
                    ALTER TABLE task 
                    ADD flag_resolved_at DATETIME2
                """))
                print("✓ Added 'flag_resolved_at' column")
            
            # Add flag_resolved_by column
            if 'flag_resolved_by' not in columns:
                conn.execute(text("""
                    ALTER TABLE task 
                    ADD flag_resolved_by INTEGER REFERENCES [user](id)
                """))
                print("✓ Added 'flag_resolved_by' column")
            
            conn.commit()
            
            # Verify columns were added
            inspector = inspect(db.engine)
            updated_columns = [col['name'] for col in inspector.get_columns('task')]
            
            added_columns = [col for col in new_columns if col in updated_columns]
            
            if len(added_columns) == len(new_columns):
                print(f"\n✓ Migration completed successfully! Added {len(added_columns)} columns.")
                return True
            else:
                print(f"\n✗ Migration partially failed. Added {len(added_columns)}/{len(new_columns)} columns.")
                return False
                
    except Exception as e:
        print(f"✗ Error adding flagging columns: {e}")
        return False

def add_flagging_indexes():
    """Add indexes for flagging fields for better performance"""
    try:
        with db.engine.connect() as conn:
            # Add index for is_flagged for quick filtering
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_task_is_flagged 
                ON task(is_flagged)
            """))
            print("✓ Added index for is_flagged")
            
            # Add index for flagged_by for user queries
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_task_flagged_by 
                ON task(flagged_by)
            """))
            print("✓ Added index for flagged_by")
            
            # Add index for flag_resolved for filtering
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_task_flag_resolved 
                ON task(flag_resolved)
            """))
            print("✓ Added index for flag_resolved")
            
            conn.commit()
            print("✓ All flagging indexes added successfully!")
            return True
            
    except Exception as e:
        print(f"✗ Error adding flagging indexes: {e}")
        return False

def run_migration():
    """Run the complete flagging migration"""
    print("Starting task flagging migration...")
    print("=" * 50)
    
    # Add flagging fields
    if not add_task_flagging_fields():
        print("✗ Failed to add flagging fields")
        return False
    
    # Add indexes
    if not add_flagging_indexes():
        print("✗ Failed to add flagging indexes")
        return False
    
    print("=" * 50)
    print("✓ Task flagging migration completed successfully!")
    return True

def rollback_migration():
    """Rollback the flagging migration"""
    print("Rolling back task flagging migration...")
    try:
        with db.engine.connect() as conn:
            # Drop indexes first
            conn.execute(text("DROP INDEX IF EXISTS idx_task_is_flagged"))
            conn.execute(text("DROP INDEX IF EXISTS idx_task_flagged_by"))
            conn.execute(text("DROP INDEX IF EXISTS idx_task_flag_resolved"))
            
            # Drop columns
            conn.execute(text("ALTER TABLE task DROP COLUMN IF EXISTS is_flagged"))
            conn.execute(text("ALTER TABLE task DROP COLUMN IF EXISTS flag_comment"))
            conn.execute(text("ALTER TABLE task DROP COLUMN IF EXISTS flagged_by"))
            conn.execute(text("ALTER TABLE task DROP COLUMN IF EXISTS flagged_at"))
            conn.execute(text("ALTER TABLE task DROP COLUMN IF EXISTS flag_resolved"))
            conn.execute(text("ALTER TABLE task DROP COLUMN IF EXISTS flag_resolved_at"))
            conn.execute(text("ALTER TABLE task DROP COLUMN IF EXISTS flag_resolved_by"))
            
            conn.commit()
            print("✓ Rollback completed successfully!")
            return True
            
    except Exception as e:
        print(f"✗ Error during rollback: {e}")
        return False

if __name__ == "__main__":
    with app.app_context():
        if len(sys.argv) > 1 and sys.argv[1] == "rollback":
            rollback_migration()
        else:
            run_migration()

#!/usr/bin/env python3
"""
Migration to add task workflow functionality
Adds workflow_status field to track task progression: backlog -> in_progress -> committed -> completed
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from sqlalchemy import text, inspect
from datetime import datetime

def add_workflow_status_column():
    """Add workflow_status column to task table"""
    try:
        with db.engine.connect() as conn:
            # Check if column already exists
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('task')]
            
            if 'workflow_status' in columns:
                print("✓ workflow_status column already exists")
                return True
            
            # Add workflow_status column
            conn.execute(text("""
                ALTER TABLE task 
                ADD workflow_status VARCHAR(20) DEFAULT 'backlog'
            """))
            
            # Update existing tasks to have proper workflow_status based on their current status
            conn.execute(text("""
                UPDATE task 
                SET workflow_status = CASE 
                    WHEN status = 'backlog' THEN 'backlog'
                    WHEN status = 'committed' THEN 'committed' 
                    WHEN status = 'in_progress' THEN 'in_progress'
                    WHEN status = 'blocked' THEN 'in_progress'  -- blocked tasks are still in progress
                    WHEN status = 'completed' THEN 'completed'
                    ELSE 'backlog'
                END
            """))
            
            conn.commit()
            print("✓ Added workflow_status column and migrated existing data")
            return True
            
    except Exception as e:
        print(f"✗ Error adding workflow_status column: {e}")
        return False

def add_workflow_timestamps():
    """Add workflow timestamp columns"""
    try:
        with db.engine.connect() as conn:
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('task')]
            
            # Add started_at column
            if 'started_at' not in columns:
                conn.execute(text("""
                    ALTER TABLE task 
                    ADD started_at DATETIME2
                """))
                print("✓ Added started_at column")
            
            # Add committed_at column  
            if 'committed_at' not in columns:
                conn.execute(text("""
                    ALTER TABLE task 
                    ADD committed_at DATETIME2
                """))
                print("✓ Added committed_at column")
            
            # Add completed_at column
            if 'completed_at' not in columns:
                conn.execute(text("""
                    ALTER TABLE task 
                    ADD completed_at DATETIME2
                """))
                print("✓ Added completed_at column")
            
            conn.commit()
            return True
            
    except Exception as e:
        print(f"✗ Error adding workflow timestamp columns: {e}")
        return False

def add_workflow_indexes():
    """Add indexes for workflow queries"""
    try:
        with db.engine.connect() as conn:
            # Add index on workflow_status for filtering
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_task_workflow_status 
                ON task(workflow_status)
            """))
            
            # Add index on started_at for sorting
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_task_started_at 
                ON task(started_at)
            """))
            
            # Add index on committed_at for sorting
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_task_committed_at 
                ON task(committed_at)
            """))
            
            # Add index on completed_at for sorting
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_task_completed_at 
                ON task(completed_at)
            """))
            
            conn.commit()
            print("✓ Added workflow indexes")
            return True
            
    except Exception as e:
        print(f"✗ Error adding workflow indexes: {e}")
        return False

def run_migration():
    """Run the complete workflow migration"""
    print("Starting task workflow migration...")
    print("=" * 50)
    
    with app.app_context():
        try:
            # Add workflow_status column
            if not add_workflow_status_column():
                return False
            
            # Add workflow timestamp columns
            if not add_workflow_timestamps():
                return False
            
            # Add workflow indexes
            if not add_workflow_indexes():
                return False
            
            print("\n" + "=" * 50)
            print("✓ Task workflow migration completed successfully!")
            print("✓ Added workflow_status, started_at, committed_at, completed_at columns")
            print("✓ Added performance indexes")
            print("✓ Migrated existing task data")
            
            return True
            
        except Exception as e:
            print(f"\n✗ Migration failed: {e}")
            return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)

"""
Database migration script to add task assignment functionality.
This script adds the new fields to the Task model for task assignment features.
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import sys

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_migration():
    """Run the migration to add task assignment fields"""
    
    # Import the app and db from the main application
    from app import app, db
    
    with app.app_context():
        try:
            print("Starting migration: Adding task assignment functionality...")
            
            # Check if the columns already exist
            from sqlalchemy import inspect, text
            
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('task')]
            
            new_columns = ['assigned_to', 'assigned_by', 'assigned_at']
            existing_columns = [col for col in new_columns if col in columns]
            
            if existing_columns:
                print(f"Warning: Some columns already exist: {existing_columns}")
                print("Skipping existing columns...")
            
            columns_to_add = [col for col in new_columns if col not in columns]
            
            if not columns_to_add:
                print("All task assignment columns already exist. Migration not needed.")
                return True
            
            # Add the new columns
            with db.engine.connect() as conn:
                # Add assigned_to column
                if 'assigned_to' not in columns:
                    conn.execute(text("""
                        ALTER TABLE task 
                        ADD assigned_to INTEGER REFERENCES [user](id)
                    """))
                    print("✓ Added 'assigned_to' column")
                
                # Add assigned_by column
                if 'assigned_by' not in columns:
                    conn.execute(text("""
                        ALTER TABLE task 
                        ADD assigned_by INTEGER REFERENCES [user](id)
                    """))
                    print("✓ Added 'assigned_by' column")
                
                # Add assigned_at column
                if 'assigned_at' not in columns:
                    conn.execute(text("""
                        ALTER TABLE task 
                        ADD assigned_at DATETIME2
                    """))
                    print("✓ Added 'assigned_at' column")
                
                conn.commit()
            
            # Verify columns were added
            inspector = inspect(db.engine)
            updated_columns = [col['name'] for col in inspector.get_columns('task')]
            
            added_columns = [col for col in new_columns if col in updated_columns]
            
            if len(added_columns) == len(columns_to_add):
                print(f"\n✓ Migration completed successfully! Added {len(added_columns)} columns.")
                
                # Add indexes for performance
                print("\nAdding database indexes...")
                add_indexes(db)
                
                print("✓ Database indexes added successfully!")
                
            else:
                print(f"\n✗ Migration partially failed. Added {len(added_columns)}/{len(columns_to_add)} columns.")
                return False
                
        except Exception as e:
            print(f"✗ Migration failed with error: {str(e)}")
            return False
    
    return True

def add_indexes(db):
    """Add database indexes for task assignment queries"""
    
    try:
        from sqlalchemy import text
        
        # Index for task assignment lookups
        with db.engine.connect() as conn:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_task_assigned_to 
                ON task(assigned_to)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_task_assigned_by 
                ON task(assigned_by)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_task_assigned_at 
                ON task(assigned_at)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_task_project_assigned 
                ON task(project_id, assigned_to)
            """))
            
            conn.commit()
        
        print("✓ Task assignment indexes created successfully")
        
    except Exception as e:
        print(f"Warning: Some indexes may not have been created: {str(e)}")

def rollback_migration():
    """Rollback the migration by removing the task assignment columns"""
    
    from app import app, db
    
    with app.app_context():
        try:
            print("Starting rollback: Removing task assignment columns...")
            
            from sqlalchemy import text
            
            with db.engine.connect() as conn:
                # Drop indexes first
                try:
                    conn.execute(text("DROP INDEX IF EXISTS idx_task_assigned_to"))
                    conn.execute(text("DROP INDEX IF EXISTS idx_task_assigned_by"))
                    conn.execute(text("DROP INDEX IF EXISTS idx_task_assigned_at"))
                    conn.execute(text("DROP INDEX IF EXISTS idx_task_project_assigned"))
                    print("✓ Dropped task assignment indexes")
                except Exception as e:
                    print(f"Warning: Could not drop some indexes: {str(e)}")
                
                # Drop columns
                try:
                    conn.execute(text("ALTER TABLE task DROP COLUMN assigned_to"))
                    print("✓ Dropped 'assigned_to' column")
                except Exception as e:
                    print(f"Warning: Could not drop 'assigned_to' column: {str(e)}")
                
                try:
                    conn.execute(text("ALTER TABLE task DROP COLUMN assigned_by"))
                    print("✓ Dropped 'assigned_by' column")
                except Exception as e:
                    print(f"Warning: Could not drop 'assigned_by' column: {str(e)}")
                
                try:
                    conn.execute(text("ALTER TABLE task DROP COLUMN assigned_at"))
                    print("✓ Dropped 'assigned_at' column")
                except Exception as e:
                    print(f"Warning: Could not drop 'assigned_at' column: {str(e)}")
                
                conn.commit()
            
            print("✓ Rollback completed successfully!")
            
        except Exception as e:
            print(f"✗ Rollback failed with error: {str(e)}")
            return False
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Database migration for task assignment functionality')
    parser.add_argument('--rollback', action='store_true', help='Rollback the migration')
    args = parser.parse_args()
    
    if args.rollback:
        success = rollback_migration()
    else:
        success = run_migration()
    
    sys.exit(0 if success else 1)

"""
Database migration script to add sharing functionality models.
This script creates the new tables for project sharing features.
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import sys

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_migration():
    """Run the migration to add sharing models"""
    
    # Import the app and db from the main application
    from app import app, db
    
    with app.app_context():
        try:
            print("Starting migration: Adding sharing functionality models...")
            
            # Create the new tables
            db.create_all()
            
            # Verify tables were created
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            expected_tables = [
                'project_collaborators',
                'sharing_tokens', 
                'sharing_activity_log',
                'active_sessions'
            ]
            
            created_tables = []
            for table in expected_tables:
                if table in tables:
                    created_tables.append(table)
                    print(f"✓ Table '{table}' created successfully")
                else:
                    print(f"✗ Table '{table}' was not created")
            
            if len(created_tables) == len(expected_tables):
                print(f"\n✓ Migration completed successfully! Created {len(created_tables)} tables.")
                
                # Add indexes for performance
                print("\nAdding database indexes...")
                add_indexes(db)
                
                print("✓ Database indexes added successfully!")
                
            else:
                print(f"\n✗ Migration partially failed. Created {len(created_tables)}/{len(expected_tables)} tables.")
                return False
                
        except Exception as e:
            print(f"✗ Migration failed with error: {str(e)}")
            return False
    
    return True

def add_indexes(db):
    """Add database indexes for sharing-related queries"""
    
    try:
        # Use the new Azure-optimized index creation
        from azure_database_config import SharingDatabaseIndexes
        
        created_count, errors = SharingDatabaseIndexes.create_indexes(db.engine)
        
        if created_count > 0:
            print(f"✓ Created {created_count} database indexes successfully")
        
        if errors:
            print(f"Warning: {len(errors)} index creation errors:")
            for error in errors:
                print(f"  - {error}")
        
    except ImportError:
        # Fallback to basic index creation if azure_database_config is not available
        print("Azure database config not available, using basic index creation")
        
        from sqlalchemy import text
        
        # Index for project collaborator lookups
        with db.engine.connect() as conn:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_project_collaborators_project_user 
                ON project_collaborators(project_id, user_id)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_project_collaborators_user_status 
                ON project_collaborators(user_id, status)
            """))
            
            # Index for sharing token lookups
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_sharing_tokens_token 
                ON sharing_tokens(token)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_sharing_tokens_project_active 
                ON sharing_tokens(project_id, is_active)
            """))
            
            # Index for activity log queries
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_sharing_activity_log_project_created 
                ON sharing_activity_log(project_id, created_at)
            """))
            
            # Index for active session lookups
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_active_sessions_user_project 
                ON active_sessions(user_id, project_id)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_active_sessions_last_activity 
                ON active_sessions(last_activity)
            """))
            
            conn.commit()
        
        print("✓ Basic database indexes created successfully")
        
    except Exception as e:
        print(f"Warning: Some indexes may not have been created: {str(e)}")

def rollback_migration():
    """Rollback the migration by dropping the sharing tables"""
    
    from app import app, db
    
    with app.app_context():
        try:
            print("Starting rollback: Removing sharing functionality models...")
            
            # Drop tables in reverse order to handle foreign key constraints
            tables_to_drop = [
                'active_sessions',
                'sharing_activity_log',
                'sharing_tokens',
                'project_collaborators'
            ]
            
            from sqlalchemy import text
            
            for table in tables_to_drop:
                try:
                    with db.engine.connect() as conn:
                        conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
                        conn.commit()
                    print(f"✓ Table '{table}' dropped successfully")
                except Exception as e:
                    print(f"Warning: Could not drop table '{table}': {str(e)}")
            
            print("✓ Rollback completed successfully!")
            
        except Exception as e:
            print(f"✗ Rollback failed with error: {str(e)}")
            return False
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Database migration for sharing functionality')
    parser.add_argument('--rollback', action='store_true', help='Rollback the migration')
    args = parser.parse_args()
    
    if args.rollback:
        success = rollback_migration()
    else:
        success = run_migration()
    
    sys.exit(0 if success else 1)
"""
Migration script to add is_expanded field to Task table for Azure SQL Database.
This field is required for the new task hierarchy toggle functionality.
"""

import os
import sys
import logging
from datetime import datetime

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def add_task_hierarchy_field():
    """
    Add is_expanded field to Task table for hierarchy toggle functionality.
    This field tracks whether a parent task is expanded to show its children.
    """
    try:
        from app import app, db
        from sqlalchemy import inspect, text
        
        with app.app_context():
            logger.info("Starting task hierarchy field migration...")
            
            # Check if the field already exists
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('task')]
            
            if 'is_expanded' in columns:
                logger.info("is_expanded field already exists in Task table")
                return True
            
            # Add the is_expanded field
            logger.info("Adding is_expanded field to Task table...")
            
            with db.engine.connect() as conn:
                # Add the column with default value True (expanded by default)
                conn.execute(text("""
                    ALTER TABLE task 
                    ADD is_expanded BIT DEFAULT 1
                """))
                
                # Update existing tasks to have is_expanded = True
                conn.execute(text("""
                    UPDATE task 
                    SET is_expanded = 1 
                    WHERE is_expanded IS NULL
                """))
                
                conn.commit()
            
            # Verify the field was added
            inspector = inspect(db.engine)
            updated_columns = [col['name'] for col in inspector.get_columns('task')]
            
            if 'is_expanded' in updated_columns:
                logger.info("✓ Successfully added is_expanded field to Task table")
                return True
            else:
                logger.error("Failed to add is_expanded field to Task table")
                return False
                
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return False


def rollback_task_hierarchy_field():
    """
    Rollback the is_expanded field addition.
    WARNING: This will remove the field and any data in it.
    """
    try:
        from app import app, db
        from sqlalchemy import inspect, text
        
        with app.app_context():
            logger.info("Rolling back task hierarchy field migration...")
            
            # Check if the field exists
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('task')]
            
            if 'is_expanded' not in columns:
                logger.info("is_expanded field does not exist, nothing to rollback")
                return True
            
            # Remove the field
            with db.engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE task 
                    DROP COLUMN is_expanded
                """))
                conn.commit()
            
            logger.info("✓ Successfully removed is_expanded field from Task table")
            return True
            
    except Exception as e:
        logger.error(f"Rollback failed: {str(e)}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Task hierarchy field migration')
    parser.add_argument('--rollback', action='store_true', 
                       help='Rollback the migration (remove is_expanded field)')
    
    args = parser.parse_args()
    
    if args.rollback:
        success = rollback_task_hierarchy_field()
    else:
        success = add_task_hierarchy_field()
    
    if success:
        logger.info("Migration completed successfully")
        sys.exit(0)
    else:
        logger.error("Migration failed")
        sys.exit(1)

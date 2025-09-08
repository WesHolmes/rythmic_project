#!/usr/bin/env python3
"""
Database migration script for Advanced Task Management features
Adds support for:
- Task reordering (sort_order)
- Risk tracking (risk_level, risk_description, mitigation_plan)
- Task hierarchy expansion (is_expanded)
- Task dependencies (TaskDependency table)
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def migrate_advanced_features():
    """Add advanced task management features to the database"""
    with app.app_context():
        print("🚀 Starting Advanced Task Management migration...")
        
        # Check if migration is needed
        try:
            # Check if new columns already exist
            with db.engine.connect() as connection:
                result = connection.execute(db.text("PRAGMA table_info(task)"))
                columns = [row[1] for row in result.fetchall()]
                
                if 'sort_order' in columns and 'risk_level' in columns:
                    print("✅ Advanced features already migrated!")
                    return
        except Exception as e:
            print(f"❌ Error checking existing schema: {e}")
            return
        
        print("📋 Adding new columns to task table...")
        
        try:
            with db.engine.connect() as connection:
                # Add new columns to task table
                connection.execute(db.text('''
                    ALTER TABLE task ADD COLUMN sort_order INTEGER DEFAULT 0
                '''))
                print("✅ Added sort_order column")
                
                connection.execute(db.text('''
                    ALTER TABLE task ADD COLUMN risk_level VARCHAR(20) DEFAULT 'low'
                '''))
                print("✅ Added risk_level column")
                
                connection.execute(db.text('''
                    ALTER TABLE task ADD COLUMN risk_description TEXT
                '''))
                print("✅ Added risk_description column")
                
                connection.execute(db.text('''
                    ALTER TABLE task ADD COLUMN mitigation_plan TEXT
                '''))
                print("✅ Added mitigation_plan column")
                
                connection.execute(db.text('''
                    ALTER TABLE task ADD COLUMN is_expanded BOOLEAN DEFAULT 1
                '''))
                print("✅ Added is_expanded column")
                
                # Create TaskDependency table
                connection.execute(db.text('''
                    CREATE TABLE task_dependency (
                        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        task_id INTEGER NOT NULL,
                        depends_on_id INTEGER NOT NULL,
                        dependency_type VARCHAR(20) DEFAULT 'finish_to_start',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(task_id) REFERENCES task (id),
                        FOREIGN KEY(depends_on_id) REFERENCES task (id)
                    )
                '''))
                print("✅ Created task_dependency table")
                
                # Create indexes for better performance
                connection.execute(db.text('CREATE INDEX ix_task_sort_order ON task (sort_order)'))
                connection.execute(db.text('CREATE INDEX ix_task_risk_level ON task (risk_level)'))
                connection.execute(db.text('CREATE INDEX ix_task_dependency_task_id ON task_dependency (task_id)'))
                connection.execute(db.text('CREATE INDEX ix_task_dependency_depends_on_id ON task_dependency (depends_on_id)'))
                print("✅ Created indexes")
                
                # Update existing tasks with sort_order based on creation time
                connection.execute(db.text('''
                    UPDATE task SET sort_order = (
                        SELECT COUNT(*) FROM task t2 
                        WHERE t2.project_id = task.project_id 
                        AND t2.created_at <= task.created_at
                    )
                '''))
                print("✅ Updated existing tasks with sort_order")
                
                connection.commit()
            
            print("🎉 Advanced Task Management migration completed successfully!")
            print("\nNew features added:")
            print("  • Drag-and-drop task reordering")
            print("  • Risk tracking and mitigation planning")
            print("  • Task hierarchy expansion/collapse")
            print("  • Task dependency management")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            print("Please check your database and try again.")

if __name__ == '__main__':
    migrate_advanced_features()

#!/usr/bin/env python3
"""
Database migration script to add labels system tables
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Project, Task, Label, TaskLabel

def migrate_database():
    """Add the new label tables to the existing database"""
    
    with app.app_context():
        print("🔄 Starting database migration...")
        
        # Check if label table already exists
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        if 'label' in existing_tables:
            print("✅ Label tables already exist. Migration not needed.")
            return
        
        print("📋 Creating new tables...")
        
        # Create the new tables
        try:
            with db.engine.connect() as connection:
                # Create label table
                connection.execute(db.text('''
                    CREATE TABLE label (
                        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(100) NOT NULL,
                        color VARCHAR(7) DEFAULT '#3B82F6',
                        icon VARCHAR(50) DEFAULT 'fas fa-tag',
                        project_id INTEGER NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(project_id) REFERENCES project (id)
                    )
                '''))
                connection.commit()
                print("✅ Created 'label' table")
                
                # Create task_labels junction table
                connection.execute(db.text('''
                    CREATE TABLE task_labels (
                        task_id INTEGER NOT NULL,
                        label_id INTEGER NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (task_id, label_id),
                        FOREIGN KEY(task_id) REFERENCES task (id),
                        FOREIGN KEY(label_id) REFERENCES label (id)
                    )
                '''))
                connection.commit()
                print("✅ Created 'task_labels' table")
                
                # Create indexes for better performance
                connection.execute(db.text('CREATE INDEX ix_label_project_id ON label (project_id)'))
                connection.execute(db.text('CREATE INDEX ix_task_labels_task_id ON task_labels (task_id)'))
                connection.execute(db.text('CREATE INDEX ix_task_labels_label_id ON task_labels (label_id)'))
                connection.commit()
                print("✅ Created indexes")
            
            print("🎉 Database migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            raise

if __name__ == "__main__":
    migrate_database()

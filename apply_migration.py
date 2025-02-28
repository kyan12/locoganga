#!/usr/bin/env python
"""
Script to directly apply migrations without using Flask CLI
"""
import os
import sys

# Add the current directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def main():
    # Import the Flask app
    try:
        from app import create_app, db
        app = create_app()
    except ImportError as e:
        print(f"Error: Could not import the Flask app: {e}")
        sys.exit(1)
    
    # Import Flask-Migrate
    try:
        from flask_migrate import Migrate, upgrade
        migrate_instance = Migrate(app, db)
        
        # Run the upgrade within the application context
        with app.app_context():
            # Import the models to ensure they are registered with SQLAlchemy
            from app.models import WinitProduct
            
            print("Applying database migrations...")
            upgrade()
            print("Migrations applied successfully.")
            
            # Verify the table exists
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            if 'winit_products' in inspector.get_table_names():
                print("✅ WinitProduct table created successfully.")
            else:
                print("❌ WinitProduct table not found in the database.")
                
    except ImportError as e:
        print(f"Error: Could not import Flask-Migrate: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 
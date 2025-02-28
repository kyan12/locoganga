#!/usr/bin/env python
"""
Script to check if the migration environment is properly set up
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
        print("✅ Successfully imported Flask app")
    except ImportError as e:
        print(f"❌ Error: Could not import the Flask app: {e}")
        sys.exit(1)
    
    # Check if the app has the database configured
    try:
        with app.app_context():
            print(f"✅ Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
            
            # Check if the database is accessible
            try:
                db.engine.connect()
                print("✅ Successfully connected to the database")
            except Exception as e:
                print(f"❌ Error connecting to the database: {e}")
                
            # Check if the migration extension is registered
            if 'migrate' in app.extensions:
                print("✅ Flask-Migrate extension is registered")
                
                # Check if the migration directory exists
                migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
                if os.path.exists(migrations_dir):
                    print(f"✅ Migrations directory exists: {migrations_dir}")
                    
                    # Check if the versions directory exists
                    versions_dir = os.path.join(migrations_dir, 'versions')
                    if os.path.exists(versions_dir):
                        print(f"✅ Versions directory exists: {versions_dir}")
                        
                        # Count migration files
                        migration_files = [f for f in os.listdir(versions_dir) if f.endswith('.py')]
                        print(f"✅ Found {len(migration_files)} migration files")
                    else:
                        print(f"❌ Versions directory does not exist: {versions_dir}")
                else:
                    print(f"❌ Migrations directory does not exist: {migrations_dir}")
            else:
                print("❌ Flask-Migrate extension is not registered")
                
            # Check if the WinitProduct model is defined
            try:
                from app.models import WinitProduct
                print("✅ WinitProduct model is defined")
                
                # Check if the table exists
                from sqlalchemy import inspect
                inspector = inspect(db.engine)
                if 'winit_products' in inspector.get_table_names():
                    print("✅ WinitProduct table exists in the database")
                else:
                    print("❌ WinitProduct table does not exist in the database")
            except ImportError:
                print("❌ WinitProduct model is not defined")
                
    except Exception as e:
        print(f"❌ Error checking migration environment: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 
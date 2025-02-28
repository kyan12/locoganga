#!/usr/bin/env python
"""
Script to run Flask migrations with proper application context
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def setup_app_context():
    """Set up the Flask application context properly"""
    # Force set the FLASK_APP environment variable
    os.environ['FLASK_APP'] = 'wsgi.py'
    
    # Import the app and db
    from app import create_app, db
    app = create_app()
    
    # Import the WinitProduct model to ensure it's registered with SQLAlchemy
    from app.models import WinitProduct
    
    return app, db

def run_migration():
    """Run the migration command"""
    import subprocess
    
    # Run the migration command
    print("Running 'flask db migrate -m \"add winit products table\"'...")
    result = subprocess.run(['flask', 'db', 'migrate', '-m', 'add winit products table'], 
                           capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Migration created successfully")
        print(result.stdout)
    else:
        print("❌ Migration creation failed")
        print(result.stderr)
        return False
    
    # Apply the migration
    print("\nRunning 'flask db upgrade'...")
    result = subprocess.run(['flask', 'db', 'upgrade'], 
                           capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Migration applied successfully")
        print(result.stdout)
    else:
        print("❌ Migration application failed")
        print(result.stderr)
        return False
    
    return True

def verify_table_exists():
    """Verify that the WinitProduct table exists in the database"""
    app, db = setup_app_context()
    
    with app.app_context():
        # Check if the table exists
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        if 'winit_products' in inspector.get_table_names():
            print("✅ WinitProduct table exists in the database")
            return True
        else:
            print("❌ WinitProduct table does not exist in the database")
            return False

def main():
    try:
        print("Setting up Flask application context...")
        app, db = setup_app_context()
        
        # First verify if the table already exists
        with app.app_context():
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            if 'winit_products' in inspector.get_table_names():
                print("WinitProduct table already exists.")
                proceed = input("Do you want to continue anyway? (y/n): ")
                if proceed.lower() != 'y':
                    print("Operation cancelled.")
                    sys.exit(0)
        
        # Run the migration
        if not run_migration():
            print("\nMigration failed. Using direct table creation as fallback...")
            proceed = input("Do you want to create the table directly? (y/n): ")
            if proceed.lower() == 'y':
                print("\nRunning direct table creation...")
                import subprocess
                result = subprocess.run(['python', 'create_db_direct.py'], 
                                      capture_output=True, text=True)
                print(result.stdout)
                if result.returncode != 0:
                    print(result.stderr)
                    print("❌ Direct table creation failed")
                    return
            else:
                print("Operation cancelled.")
                return
        
        # Verify that the table exists
        verify_table_exists()
        
        print("\nNext steps:")
        print("1. Run 'python import_winit_products.py' to import products")
        print("2. Use WinitProductService to retrieve products with database fallback")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main() 
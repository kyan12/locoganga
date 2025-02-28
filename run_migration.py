#!/usr/bin/env python
"""
Script to run Flask migrations with proper application context
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
        from flask_migrate import Migrate
        migrate_instance = Migrate(app, db)
        
        # Run the migration within the application context
        with app.app_context():
            # Import the models to ensure they are registered with SQLAlchemy
            from app.models import WinitProduct
            
            # Create the migration command
            from flask import current_app
            from flask_migrate import stamp, migrate, upgrade
            
            print("Creating migration for WinitProduct table...")
            migrate(message='add_winit_products_table')
            print("Migration created successfully.")
            print("To apply the migration, run:")
            print("flask db upgrade")
            
            # Optionally apply the migration immediately
            apply_now = input("Do you want to apply the migration now? (y/n): ")
            if apply_now.lower() == 'y':
                print("Applying migration...")
                upgrade()
                print("Migration applied successfully.")
    except ImportError as e:
        print(f"Error: Could not import Flask-Migrate: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 
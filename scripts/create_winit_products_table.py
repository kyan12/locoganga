#!/usr/bin/env python
"""
Script to generate a migration for the WinitProduct table
"""
import os
import sys
import argparse
from dotenv import load_dotenv

# Add the current directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Load environment variables
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description='Generate a migration for the WinitProduct table')
    parser.add_argument('--message', type=str, default='add_winit_products_table', help='Migration message')
    args = parser.parse_args()
    
    # Import the Flask app
    try:
        from app import create_app, db
        from flask_migrate import Migrate
        app = create_app()
        migrate = Migrate(app, db)
    except ImportError:
        print("Error: Could not import the Flask app or Flask-Migrate. Make sure they are correctly installed.")
        sys.exit(1)
    
    # Import the models to ensure they are registered with SQLAlchemy
    try:
        from app.models import WinitProduct
    except ImportError:
        print("Error: Could not import the WinitProduct model. Make sure it is correctly defined.")
        sys.exit(1)
    
    # Generate the migration
    print(f"Generating migration for WinitProduct table with message: {args.message}")
    
    # Use Flask-Migrate to generate the migration
    from flask_migrate import migrate as _migrate
    
    with app.app_context():
        _migrate.init_app(app, db)
        _migrate.migrate(message=args.message)
    
    print("Migration generated successfully.")
    print("To apply the migration, run:")
    print("flask db upgrade")

if __name__ == '__main__':
    main() 
#!/usr/bin/env python
"""
Script to directly create the WinitProduct table without using migrations
"""
import os
import sys

# Add the current directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def main():
    # Import the Flask app
    try:
        from app import create_app, db
        
        # Ensure the MySQL driver is installed
        try:
            import pymysql
            pymysql.install_as_MySQLdb()
            print("PyMySQL installed as MySQLdb")
        except ImportError:
            print("PyMySQL not installed, trying to use mysqlclient")
            try:
                import MySQLdb
                print("Using mysqlclient")
            except ImportError:
                print("Warning: Neither PyMySQL nor mysqlclient is installed.")
                print("Installing PyMySQL...")
                import pip
                pip.main(['install', 'pymysql'])
                import pymysql
                pymysql.install_as_MySQLdb()
                print("PyMySQL installed successfully")
        
        # Create the app
        app = create_app()
        print(f"App created with database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    except ImportError as e:
        print(f"Error: Could not import the Flask app: {e}")
        sys.exit(1)
    
    try:
        # Run within the application context
        with app.app_context():
            # Import the models to ensure they are registered with SQLAlchemy
            from app.models import WinitProduct
            
            # Check if the table already exists
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            if 'winit_products' in inspector.get_table_names():
                print("WinitProduct table already exists.")
                proceed = input("Do you want to drop and recreate the table? (y/n): ")
                if proceed.lower() != 'y':
                    print("Operation cancelled.")
                    return
                
                # Drop the table
                print("Dropping WinitProduct table...")
                WinitProduct.__table__.drop(db.engine)
                print("Table dropped.")
            
            # Create the table
            print("Creating WinitProduct table...")
            WinitProduct.__table__.create(db.engine)
            print("✅ WinitProduct table created successfully.")
            
    except Exception as e:
        print(f"Error creating table: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main() 
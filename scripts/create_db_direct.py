#!/usr/bin/env python
"""
Script to directly create the WinitProduct table using SQLAlchemy without Flask-Migrate
"""
import os
import sys
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, Boolean, Text, DateTime
from sqlalchemy.sql import text
import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the database URL from environment variable
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("❌ Error: DATABASE_URL not found in environment variables")
    sys.exit(1)

print(f"Using database URL: {DATABASE_URL}")

# Create engine
try:
    # Try to connect to the database
    engine = create_engine(DATABASE_URL)
    connection = engine.connect()
    print("✅ Successfully connected to the database")
except Exception as e:
    print(f"❌ Error connecting to the database: {e}")
    sys.exit(1)

# Create metadata
metadata = MetaData()

# Define the WinitProduct table
winit_products = Table(
    'winit_products', 
    metadata,
    Column('id', Integer, primary_key=True),
    Column('spu', String(50), unique=True, index=True),
    Column('sku', String(50), index=True),
    Column('name', String(200), nullable=False),
    Column('description', Text),
    Column('price', Float),
    Column('stock', Integer, default=0),
    Column('image_url', String(500)),
    Column('thumbnail_url', String(500)),
    Column('category', String(100)),
    Column('brand', String(100)),
    Column('weight', Float),
    Column('dimensions', String(100)),
    Column('is_active', Boolean, default=True),
    Column('additional_data', Text),
    Column('created_at', DateTime, default=datetime.datetime.utcnow),
    Column('updated_at', DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
)

# Check if table exists
try:
    insp = engine.dialect.has_table(connection, 'winit_products')
    if insp:
        print("WinitProduct table already exists.")
        proceed = input("Do you want to drop and recreate the table? (y/n): ")
        if proceed.lower() == 'y':
            # Drop the table
            print("Dropping WinitProduct table...")
            winit_products.drop(engine)
            print("Table dropped.")
        else:
            print("Operation cancelled.")
            sys.exit(0)
except Exception as e:
    print(f"Error checking if table exists: {e}")

# Create the table
try:
    print("Creating WinitProduct table...")
    metadata.create_all(engine)
    print("✅ WinitProduct table created successfully")
    
    # Verify that the table was created
    insp = engine.dialect.has_table(connection, 'winit_products')
    if insp:
        print("✅ Verified that WinitProduct table exists")
    else:
        print("❌ Table creation failed for unknown reason")
except Exception as e:
    print(f"❌ Error creating table: {e}")
    sys.exit(1)

# Close connection
connection.close()
print("Database connection closed")

print("\nNext steps:")
print("1. Run 'python import_winit_products.py' to import products into the database")
print("2. Use WinitProductService to retrieve products with database fallback") 
#!/usr/bin/env python
"""
Script to test the database fallback for Winit products
"""
import os
import sys
import json
import argparse
from dotenv import load_dotenv

# Add the current directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Load environment variables
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description='Test the database fallback for Winit products')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show verbose output')
    args = parser.parse_args()
    
    # Import the Flask app
    try:
        from app import create_app, db
        app = create_app()
    except ImportError:
        print("Error: Could not import the Flask app. Make sure you're in the correct directory.")
        sys.exit(1)
    
    # Import the services
    try:
        from app.services.winit_product_service import WinitProductService
        from app.models import WinitProduct
    except ImportError:
        print("Error: Could not import the required services. Make sure they are correctly defined.")
        sys.exit(1)
    
    # Test the database fallback
    with app.app_context():
        print("Testing database fallback for Winit products...")
        
        # Check if we have any products in the database
        product_count = WinitProduct.query.count()
        print(f"Found {product_count} products in the database.")
        
        if product_count == 0:
            print("Warning: No products found in the database. The fallback will return empty results.")
            print("Run the import_winit_products.py script first to import products.")
        
        # Create a product service with an invalid API to force fallback
        from app.services.winit_api import WinitAPI
        invalid_api = WinitAPI(
            base_url="https://invalid-url-to-force-fallback.example.com",
            app_key="invalid",
            token="invalid"
        )
        
        product_service = WinitProductService(app=app, db=db, api=invalid_api)
        
        # Test getting products
        print("\n1. Testing get_products with fallback...")
        try:
            result = product_service.get_products(page=1, page_size=10, use_fallback=True)
            
            if args.verbose:
                print(json.dumps(result, indent=2))
            
            product_count = len(result.get('data', {}).get('list', []))
            print(f"✅ get_products with fallback returned {product_count} products")
        except Exception as e:
            print(f"❌ get_products with fallback failed: {e}")
        
        # Test getting product details
        print("\n2. Testing get_product_details with fallback...")
        
        # Get a product SPU from the database
        spu = None
        product = WinitProduct.query.first()
        if product:
            spu = product.spu
            
            try:
                result = product_service.get_product_details(spu, use_fallback=True)
                
                if args.verbose:
                    print(json.dumps(result, indent=2))
                
                product_count = len(result.get('data', {}).get('list', []))
                print(f"✅ get_product_details with fallback returned {product_count} products for SPU {spu}")
            except Exception as e:
                print(f"❌ get_product_details with fallback failed: {e}")
        else:
            print("❌ No products found in the database to test get_product_details")
        
        # Test without fallback
        print("\n3. Testing get_products without fallback...")
        try:
            product_service.get_products(use_fallback=False)
            print("❌ get_products without fallback unexpectedly succeeded")
        except Exception as e:
            print(f"✅ get_products without fallback correctly failed: {type(e).__name__}")
        
        print("\nDatabase fallback test complete!")

if __name__ == '__main__':
    main() 
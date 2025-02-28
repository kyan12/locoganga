#!/usr/bin/env python
import json
import os
import logging
from flask import Flask
from app import create_app
from app.services.winit_api import WinitAPI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_and_save_products(app, output_file='app/static/fallback_products.json', pages=2):
    """
    Fetch products from Winit API and save to JSON file
    Args:
        app: Flask application instance
        output_file: Path to output JSON file
        pages: Number of pages to fetch (each page is 50 products)
    """
    with app.app_context():
        try:
            # Initialize WinitAPI service
            winit_api = WinitAPI.from_app(app)
            
            # Check if required API credentials are available
            if not winit_api.app_key or not winit_api.token or not winit_api.base_url:
                logger.error("Missing Winit API credentials")
                return False
                
            all_products = []
            api_page_size = 50
            
            # Fetch multiple pages of products
            for page in range(1, pages + 1):
                logger.info(f"Fetching product page {page}...")
                
                # Get products from Winit API for the specific page
                response_data = winit_api.get_product_base_list(
                    warehouse_code='UKGF',
                    page_no=page,
                    page_size=api_page_size
                )
                
                # Ensure response_data is a dictionary
                if not isinstance(response_data, dict):
                    logger.error(f"Invalid API response type: {type(response_data)}")
                    continue
                
                if response_data.get('code') != '0':
                    error_message = f"API Error: {response_data.get('msg', 'Unknown error')} (Code: {response_data.get('code', 'Unknown')})"
                    logger.error(error_message)
                    continue

                # Get products from response with safe fallbacks
                data = response_data.get('data', {}) or {}
                products = data.get('SPUList', []) or []
                
                # Filter in-stock products
                in_stock_products = [
                    product for product in products
                    if product.get('totalInventory', 0) > 0
                ]
                
                logger.info(f"Found {len(in_stock_products)} in-stock products on page {page}")
                all_products.extend(in_stock_products)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Save products to JSON file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_products, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Saved {len(all_products)} products to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error fetching products: {e}")
            logger.exception("Detailed traceback:")
            return False

if __name__ == "__main__":
    app = create_app()
    success = fetch_and_save_products(app)
    if success:
        print("✅ Product fallback file created successfully!")
    else:
        print("❌ Failed to create product fallback file.") 
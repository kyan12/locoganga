#!/usr/bin/env python
"""
Script to import Winit products from the homepage at localhost:5000
"""
import os
import sys
import json
import argparse
import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from dotenv import load_dotenv

# Add the current directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Load environment variables
load_dotenv()

def fetch_products_from_homepage(base_url, page=1):
    """Fetch products by scraping the homepage"""
    try:
        # If page > 1, append page parameter
        url = base_url
        if page > 1:
            url = f"{base_url}?page={page}"
        
        print(f"Fetching products from {url}...")
        
        # Make the request
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find product cards/containers
        # This selector needs to be adjusted based on the actual HTML structure
        product_elements = soup.select('.product-card, .product-container, .product-item')
        
        if not product_elements:
            # Try alternative selectors if the specific ones don't work
            product_elements = soup.find_all('div', class_=lambda c: c and ('product' in c.lower()))
        
        print(f"Found {len(product_elements)} product elements on page {page}")
        
        products = []
        for element in product_elements:
            # Extract product data from the element
            product = extract_product_data(element, base_url)
            if product:
                products.append(product)
        
        # Check for pagination to determine if there are more pages
        pagination = soup.select('.pagination')
        has_next_page = False
        if pagination:
            next_button = soup.select('.pagination .next, .pagination [aria-label="Next"]')
            has_next_page = bool(next_button and not 'disabled' in next_button[0].get('class', []))
        
        return {
            'products': products,
            'has_next_page': has_next_page
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching products from homepage: {e}")
        return None

def extract_product_data(element, base_url):
    """Extract product data from a product element"""
    product = {}
    
    # Try to find product SPU/SKU
    # Look for data attributes first
    spu = element.get('data-spu') or element.get('data-product-id')
    
    # If not found in data attributes, try to extract from URLs or hidden inputs
    if not spu:
        # Try to find it in the product URL
        link = element.find('a', href=True)
        if link:
            href = link.get('href')
            # Extract SPU from URL patterns like /product/ABC123 or ?spu=ABC123
            match = re.search(r'/product/([^/?&#]+)|[?&]spu=([^&#]+)', href)
            if match:
                spu = match.group(1) or match.group(2)
    
    # If we still don't have an SPU, search for hidden inputs or other elements
    if not spu:
        spu_input = element.find('input', {'name': 'spu'})
        if spu_input:
            spu = spu_input.get('value')
    
    # If we couldn't find an SPU, we can't uniquely identify this product
    if not spu:
        # As a last resort, look for any unique identifier
        id_element = element.get('id')
        if id_element and 'product' in id_element:
            # Extract numeric part if it exists
            id_match = re.search(r'\d+', id_element)
            if id_match:
                spu = id_match.group(0)
        
        if not spu:
            print("Warning: Could not extract SPU/SKU for a product, skipping.")
            return None
    
    product['SPU'] = spu
    product['SKU'] = spu  # Use SPU as SKU if no separate SKU is available
    
    # Extract product title
    title_element = element.find('h2') or element.find('h3') or element.find('h4') or element.find(class_=lambda c: c and 'title' in c.lower())
    if title_element:
        product['title'] = title_element.get_text(strip=True)
    
    # Extract price
    price_element = element.find(class_=lambda c: c and 'price' in c.lower())
    if price_element:
        price_text = price_element.get_text(strip=True)
        # Extract numbers from the price text
        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
        if price_match:
            try:
                product['price'] = float(price_match.group(0).replace(',', ''))
            except ValueError:
                pass
    
    # Extract image URL
    img = element.find('img')
    if img:
        img_src = img.get('src') or img.get('data-src')
        if img_src:
            # Make sure the URL is absolute
            product['images'] = [{'url': urljoin(base_url, img_src)}]
    
    # Extract product URL for fetching details later
    product_url = None
    link = element.find('a', href=True)
    if link:
        product_url = urljoin(base_url, link.get('href'))
        product['url'] = product_url
    
    return product

def fetch_product_details(product_url):
    """Fetch detailed product information by visiting the product page"""
    if not product_url:
        return None
    
    try:
        response = requests.get(product_url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract additional details from the product page
        details = {}
        
        # Description
        description_elem = soup.find(id=lambda i: i and 'description' in i.lower()) or \
                          soup.find(class_=lambda c: c and 'description' in c.lower())
        if description_elem:
            details['description'] = description_elem.get_text(strip=True)
        
        # Additional images
        image_elements = soup.select('.product-images img, .gallery img')
        if image_elements:
            images = []
            for img in image_elements:
                img_src = img.get('src') or img.get('data-src')
                if img_src:
                    images.append({'url': urljoin(product_url, img_src)})
            if images:
                details['images'] = images
        
        # Stock information
        stock_elem = soup.find(text=re.compile(r'in stock', re.I)) or \
                    soup.find(class_=lambda c: c and 'stock' in c.lower())
        if stock_elem:
            stock_text = stock_elem.get_text(strip=True) if hasattr(stock_elem, 'get_text') else str(stock_elem)
            # Try to extract a number
            stock_match = re.search(r'\d+', stock_text)
            if stock_match:
                details['stock'] = int(stock_match.group(0))
            elif 'out of stock' in stock_text.lower():
                details['stock'] = 0
            else:
                details['stock'] = 1  # Assume at least one is in stock if it says "in stock"
        
        # Category
        breadcrumbs = soup.select('.breadcrumbs li, nav[aria-label="breadcrumb"] li')
        if breadcrumbs and len(breadcrumbs) > 1:
            # Usually the category is the second-to-last breadcrumb
            category = breadcrumbs[-2].get_text(strip=True)
            details['category'] = category
        
        return details
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching product details from {product_url}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Import Winit products from the homepage into the database')
    parser.add_argument('--url', type=str, default='http://localhost:5000', help='Homepage URL')
    parser.add_argument('--max-pages', type=int, default=10, help='Maximum number of pages to fetch')
    parser.add_argument('--details', action='store_true', help='Fetch detailed product information by visiting product pages')
    parser.add_argument('--output', type=str, help='Output file for product data (optional)')
    parser.add_argument('--dry-run', action='store_true', help='Don\'t save to database, just print info')
    args = parser.parse_args()
    
    # Import the Flask app
    try:
        from app import create_app, db
        from app.models import WinitProduct
        app = create_app()
    except ImportError:
        print("Error: Could not import the Flask app. Make sure you're in the correct directory.")
        sys.exit(1)
    
    # Initialize product data storage
    all_products = []
    product_count = 0
    
    # Fetch products from the homepage
    with app.app_context():
        print(f"Fetching products from homepage at {args.url}...")
        
        # Fetch products page by page
        for page in range(1, args.max_pages + 1):
            print(f"Fetching page {page}...")
            
            # Fetch the current page of products
            response = fetch_products_from_homepage(args.url, page)
            
            if not response:
                print(f"No response from server for page {page}. Stopping.")
                break
            
            # Get products from the response
            products = response.get('products', [])
            
            if not products:
                print(f"No products found on page {page}. Stopping.")
                break
            
            print(f"Found {len(products)} products on page {page}")
            
            # Process each product
            for product_data in products:
                # Get the SPU
                spu = product_data.get('SPU')
                
                if not spu:
                    print(f"Warning: Product without SPU found. Skipping.")
                    continue
                
                # Fetch detailed product information if requested
                if args.details and 'url' in product_data:
                    print(f"Fetching details for product {spu}...")
                    details = fetch_product_details(product_data['url'])
                    
                    if details:
                        # Merge details with product data
                        product_data.update(details)
                
                # Add to the list of all products
                all_products.append(product_data)
                product_count += 1
                
                # Create or update the product in the database
                if not args.dry_run:
                    # Check if the product already exists
                    existing_product = WinitProduct.query.filter_by(spu=spu).first()
                    
                    if existing_product:
                        print(f"Updating existing product {spu}...")
                        
                        # Update the product
                        existing_product.additional_data_dict = product_data
                        existing_product.name = product_data.get('title') or product_data.get('name') or existing_product.name
                        
                        if 'price' in product_data:
                            existing_product.price = float(product_data.get('price', 0))
                        
                        if 'stock' in product_data:
                            existing_product.stock = int(product_data.get('stock', 0))
                        
                        # Extract image URLs
                        images = product_data.get('images', [])
                        if images and isinstance(images, list) and len(images) > 0:
                            existing_product.image_url = images[0].get('url')
                            existing_product.thumbnail_url = images[0].get('url')
                        
                        # Extract description
                        if 'description' in product_data:
                            existing_product.description = product_data.get('description', '')
                        
                        # Extract category
                        if 'category' in product_data:
                            existing_product.category = product_data.get('category')
                    else:
                        print(f"Creating new product {spu}...")
                        
                        # Create a new product from the scraped data
                        new_product = WinitProduct(
                            spu=spu,
                            sku=product_data.get('SKU') or spu,
                            name=product_data.get('title') or '',
                            price=float(product_data.get('price', 0)),
                            stock=int(product_data.get('stock', 0)),
                            description=product_data.get('description', ''),
                            category=product_data.get('category', ''),
                            additional_data=json.dumps(product_data)
                        )
                        
                        # Set image URLs if available
                        images = product_data.get('images', [])
                        if images and isinstance(images, list) and len(images) > 0:
                            new_product.image_url = images[0].get('url')
                            new_product.thumbnail_url = images[0].get('url')
                        
                        db.session.add(new_product)
                    
                    # Commit the changes
                    db.session.commit()
            
            # Check if we've reached the end of the products
            if not response.get('has_next_page', False):
                print(f"Reached the end of products. Stopping.")
                break
        
        print(f"Processed {product_count} products in total.")
        
        # Save the product data to a file if requested
        if args.output:
            print(f"Saving product data to {args.output}...")
            with open(args.output, 'w') as f:
                json.dump(all_products, f, indent=2)
            print(f"Product data saved to {args.output}")
        
        # Print database statistics
        if not args.dry_run:
            db_product_count = WinitProduct.query.count()
            print(f"Database now contains {db_product_count} Winit products.")

if __name__ == '__main__':
    main() 
from flask import Blueprint, render_template, current_app, request
import requests
import hashlib
from datetime import datetime
import json

bp = Blueprint('main', __name__)

# config.py
class Config:
    API_CONFIG = {
        'base_url': 'https://openapi.wanyilian.com/cedpopenapi/service',
        'app_key': 'your_username',  # Replace with your username
        'token': 'b309954f-7656-4948-937f-9f4978f35caa',  # This is their example token, use yours
        'platform': 'cavendish'  # They're using this platform code
    }

def generate_sign(params):
    """Generate API signature matching the JavaScript implementation"""
    TOKEN = 'b309954f-7656-4948-937f-9f4978f35caa'
    
    # Create clean params copy
    param_copy = {k: v for k, v in params.items() if k not in ['sign', 'language']}
    
    # Build signature string starting with token
    sign_string = TOKEN
    
    # Sort and concatenate parameters
    for key in sorted(param_copy.keys()):
        value = param_copy[key]
        if key == 'data':
            # Ensure consistent JSON serialization
            sign_string += key + json.dumps(value, separators=(',', ':'))
        else:
            sign_string += key + str(value)
            
    # Add token at end
    sign_string += TOKEN
    
    # Generate MD5 hash and convert to uppercase
    return hashlib.md5(sign_string.encode('utf-8')).hexdigest().upper()

@bp.route('/')
def index():
    requested_page = request.args.get('page', 1, type=int)
    items_per_page = 20  # 5 columns × 4 rows
    in_stock_products = []
    current_api_page = 1
    total_in_stock_count = 0
    first_page = True

    while len(in_stock_products) < (requested_page * items_per_page):
        params = {
            'action': 'wanyilian.supplier.spu.getProductBaseList',
            'app_key': current_app.config['API_CONFIG']['app_key'],
            'data': {
                'pageParams': {
                    'pageNo': current_api_page,
                    'pageSize': 50,  # Request more items per API call to reduce number of calls
                    'totalCount': 0
                },
                'warehouseCode': 'UKGF'
            },
            'format': 'json',
            'language': 'zh_CN',
            'platform': current_app.config['API_CONFIG']['platform'],
            'sign_method': 'md5',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'version': '1.0'
        }

        params['sign'] = generate_sign(params)
        
        try:
            response = requests.post(current_app.config['API_CONFIG']['base_url'], json=params)
            response_data = response.json()
            
            if response_data.get('code') != '0':
                error_message = f"API Error: {response_data.get('msg')} (Code: {response_data.get('code')})"
                return render_template('main/index.html', 
                                     products=[], 
                                     error=error_message,
                                     pagination={'page': requested_page, 'total_pages': 1})

            # Get products from response
            new_products = response_data.get('data', {}).get('SPUList', [])
            
            # If no more products, break
            if not new_products:
                break

            # Filter and add in-stock products
            in_stock_products.extend([
                product for product in new_products
                if product.get('totalInventory', 0) > 0
            ])

            # On first page, estimate total in-stock items for pagination
            if first_page:
                total_api_count = response_data.get('data', {}).get('pageParams', {}).get('totalCount', 0)
                in_stock_ratio = len([p for p in new_products if p.get('totalInventory', 0) > 0]) / len(new_products)
                total_in_stock_count = int(total_api_count * in_stock_ratio)
                first_page = False

            current_api_page += 1

        except Exception as e:
            current_app.logger.error(f"Error fetching products: {e}")
            return render_template('main/index.html', 
                                 products=[], 
                                 error=str(e),
                                 pagination={'page': requested_page, 'total_pages': 1})

    # Calculate total pages based on estimated total in-stock items
    total_pages = (total_in_stock_count + items_per_page - 1) // items_per_page

    # Get the slice of products for the requested page
    start_idx = (requested_page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_products = in_stock_products[start_idx:end_idx]

    return render_template('main/index.html', 
                         products=page_products,
                         pagination={'page': requested_page, 'total_pages': total_pages})
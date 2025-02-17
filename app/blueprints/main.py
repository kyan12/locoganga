from flask import Blueprint, render_template, current_app, request
import requests
import hashlib
from datetime import datetime, timedelta
import json
from ..services.product_service import ProductService
from ..services.winit_api import WinitAPI
from ..models import Product, ProductSKU, db

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

def sync_products(winit_api, force=False):
    """
    Sync products from Winit to local database
    Returns the number of products synced
    """
    try:
        # Check if we need to sync
        last_product = Product.query.order_by(Product.updated_at.desc()).first()
        if not force and last_product and last_product.updated_at > datetime.utcnow() - timedelta(hours=1):
            return 0  # Skip if last sync was less than 1 hour ago

        # Get products from Winit
        page = 1
        total_synced = 0
        while True:
            response = winit_api.get_product_list(page=page, page_size=100)
            products = response.get('list', [])
            
            if not products:
                break

            for product_data in products:
                # Get or create product
                product = Product.query.filter_by(spu=product_data['spu']).first()
                if not product:
                    product = Product(spu=product_data['spu'])
                
                # Update product details
                product.title = product_data.get('title', '')
                product.description = product_data.get('description', '')
                product.category_id = product_data.get('categoryId')
                product.sale_type_id = product_data.get('saleTypeId')
                product.warehouse_code = product_data.get('warehouseCode')
                product.thumbnail = product_data.get('thumbnail')
                product.total_inventory = product_data.get('totalInventory', 0)
                product.updated_at = datetime.utcnow()

                # Get detailed product info including SKUs
                detail = winit_api.get_product_detail(product.spu)
                if detail and 'skuList' in detail:
                    # Clear existing SKUs
                    ProductSKU.query.filter_by(product_id=product.id).delete()
                    
                    # Add new SKUs
                    for sku_data in detail['skuList']:
                        sku = ProductSKU(
                            product=product,
                            sku=sku_data['sku'],
                            title=sku_data.get('title', ''),
                            image=sku_data.get('image'),
                            price=float(sku_data.get('price', 0)),
                            settle_price=float(sku_data.get('settlePrice', 0)),
                            inventory=int(sku_data.get('inventory', 0))
                        )
                        db.session.add(sku)

                db.session.add(product)
                total_synced += 1

            page += 1
            
        db.session.commit()
        current_app.logger.info(f"Successfully synced {total_synced} products from Winit")
        return total_synced

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error syncing products from Winit: {str(e)}")
        raise

@bp.route('/')
@bp.route('/index')
def index():
    """Home page"""
    print('home')
    # Initialize services
    winit_api = WinitAPI.from_app(current_app)
    product_service = ProductService(winit_api)

    try:
        # Sync products from Winit
        sync_products(winit_api)
        
        # Get featured products from our database
        featured_products = Product.query.filter(
            Product.total_inventory > 0
        ).order_by(
            Product.updated_at.desc()
        ).limit(8).all()
        
        return render_template('main/index.html', products=featured_products)

    except Exception as e:
        current_app.logger.error(f"Error in index route: {str(e)}")
        # If sync fails, try to get products from database anyway
        featured_products = Product.query.filter(
            Product.total_inventory > 0
        ).order_by(
            Product.updated_at.desc()
        ).limit(8).all()
        return render_template('main/index.html', products=featured_products)

@bp.route('/about')
def about():
    """About page"""
    return render_template('main/about.html')


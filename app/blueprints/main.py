from flask import Blueprint, render_template, current_app, request
from ..services.winit_api import WinitAPI
from ..services.cache_service import get_cached_products, cache_products, get_cached_product_count, cache_product_count

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    requested_page = request.args.get('page', 1, type=int)
    items_per_page = current_app.config.get('PRODUCT_PAGE_SIZE', 20)
    
    # Try to get products from cache first
    cached_products = get_cached_products(requested_page)
    cached_count = get_cached_product_count()
    
    if cached_products is not None and cached_count is not None:
        current_app.logger.info(f"Serving products for page {requested_page} from cache")
        total_pages = (cached_count + items_per_page - 1) // items_per_page
        return render_template('main/index.html', 
                             products=cached_products,
                             pagination={'page': requested_page, 'total_pages': total_pages})
    
    # Initialize WinitAPI service
    try:
        winit_api = WinitAPI.from_app(current_app)
        
        # Check if required API credentials are available
        if not winit_api.app_key or not winit_api.token or not winit_api.base_url:
            current_app.logger.error("Missing Winit API credentials")
            return render_template('main/index.html', 
                                products=[], 
                                error="API configuration is incomplete. Please check your environment variables.",
                                pagination={'page': requested_page, 'total_pages': 1})
    except Exception as e:
        current_app.logger.error(f"Error initializing Winit API: {e}")
        return render_template('main/index.html', 
                             products=[], 
                             error=f"API initialization error: {str(e)}",
                             pagination={'page': requested_page, 'total_pages': 1})
    
    try:
        # Calculate which API page we need based on items_per_page
        # We request a larger page size from the API to account for filtering out of stock items
        api_page_size = 50  # Request more items than we need to account for filtering
        api_page = ((requested_page - 1) * items_per_page) // api_page_size + 1
        
        # Get products from Winit API for the specific page
        response_data = winit_api.get_product_base_list(
            warehouse_code='UKGF',
            page_no=api_page,
            page_size=api_page_size
        )
        
        # Ensure response_data is a dictionary
        if not isinstance(response_data, dict):
            current_app.logger.error(f"Invalid API response type: {type(response_data)}")
            return render_template('main/index.html', 
                                products=[], 
                                error=f"Invalid API response format: {type(response_data)}",
                                pagination={'page': requested_page, 'total_pages': 1})
        
        if response_data.get('code') != '0':
            error_message = f"API Error: {response_data.get('msg', 'Unknown error')} (Code: {response_data.get('code', 'Unknown')})"
            return render_template('main/index.html', 
                                products=[], 
                                error=error_message,
                                pagination={'page': requested_page, 'total_pages': 1})

        # Get products from response with safe fallbacks
        data = response_data.get('data', {}) or {}
        all_products = data.get('SPUList', []) or []
        
        # Filter in-stock products
        in_stock_products = [
            product for product in all_products
            if product.get('totalInventory', 0) > 0
        ]
        
        # Get total count for pagination with safe fallbacks
        page_params = data.get('pageParams', {}) or {}
        total_api_count = page_params.get('totalCount', 0) or 0
        
        # Estimate total in-stock items for pagination
        in_stock_ratio = len(in_stock_products) / max(len(all_products), 1)  # Avoid division by zero
        total_in_stock_count = int(total_api_count * in_stock_ratio)
        
        # Cache the total count
        cache_product_count(total_in_stock_count)
        
        # Calculate total pages
        total_pages = max((total_in_stock_count + items_per_page - 1) // items_per_page, 1)  # At least 1 page
        
        # If we don't have enough products for this page, we need to fetch more
        offset = ((requested_page - 1) * items_per_page) % api_page_size
        
        # If we need more products than what we got from the first API call
        if len(in_stock_products) < offset + items_per_page and api_page < total_pages:
            try:
                # Get next page from API
                next_response = winit_api.get_product_base_list(
                    warehouse_code='UKGF',
                    page_no=api_page + 1,
                    page_size=api_page_size
                )
                
                if isinstance(next_response, dict) and next_response.get('code') == '0':
                    next_data = next_response.get('data', {}) or {}
                    next_products = next_data.get('SPUList', []) or []
                    next_in_stock = [p for p in next_products if p.get('totalInventory', 0) > 0]
                    in_stock_products.extend(next_in_stock)
            except Exception as e:
                current_app.logger.warning(f"Error fetching additional products: {e}")
                # Continue with what we have
        
        # Get the slice of products for the requested page
        start_idx = offset
        end_idx = min(start_idx + items_per_page, len(in_stock_products))
        page_products = in_stock_products[start_idx:end_idx] if start_idx < len(in_stock_products) else []
        
        # Cache the products for this page
        if page_products:
            cache_products(requested_page, page_products)
        
        return render_template('main/index.html', 
                             products=page_products,
                             pagination={'page': requested_page, 'total_pages': total_pages})
                             
    except Exception as e:
        current_app.logger.error(f"Error fetching products: {e}")
        current_app.logger.exception("Detailed traceback:")
        return render_template('main/index.html', 
                             products=[], 
                             error=f"Error loading products: {str(e)}",
                             pagination={'page': requested_page, 'total_pages': 1})


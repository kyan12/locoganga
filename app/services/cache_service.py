from flask_caching import Cache
from flask import current_app
import json
import threading

cache = Cache()

def init_cache(app):
    """Initialize the cache with the application"""
    cache_config = {
        'CACHE_TYPE': app.config['CACHE_TYPE'],
        'CACHE_DEFAULT_TIMEOUT': app.config['CACHE_DEFAULT_TIMEOUT']
    }
    
    # Add Redis URL if using Redis
    if app.config['CACHE_TYPE'] == 'redis':
        cache_config['CACHE_REDIS_URL'] = app.config['CACHE_REDIS_URL']
    
    # Add additional cache options if defined
    if 'CACHE_OPTIONS' in app.config:
        for key, value in app.config['CACHE_OPTIONS'].items():
            cache_config[key] = value
    
    cache.init_app(app, config=cache_config)
    app.logger.info(f"Cache initialized with type: {app.config['CACHE_TYPE']}")

def get_cached_products(page):
    """Get products for a specific page from cache"""
    cache_key = f'products_page_{page}'
    return cache.get(cache_key)

def cache_products(page, products, timeout=None):
    """Cache products for a specific page"""
    if timeout is None:
        timeout = current_app.config['PRODUCT_CACHE_TIMEOUT']
    cache_key = f'products_page_{page}'
    cache.set(cache_key, products, timeout=timeout)
    current_app.logger.debug(f"Cached {len(products)} products for page {page}")

def get_cached_product_count():
    """Get the total number of products from cache"""
    return cache.get('total_product_count')

def cache_product_count(count, timeout=None):
    """Cache the total number of products"""
    if timeout is None:
        timeout = current_app.config['PRODUCT_CACHE_TIMEOUT']
    cache.set('total_product_count', count, timeout=timeout)
    current_app.logger.debug(f"Cached total product count: {count}")

def invalidate_product_cache():
    """Invalidate all product-related cache entries"""
    cache.delete('total_product_count')
    # We'll implement a more sophisticated cache invalidation if needed
    # For now, we let the cache expire naturally for product pages
    current_app.logger.info("Product cache invalidated")

def get_cached_categories():
    """Get product categories from cache"""
    return cache.get('product_categories')

def cache_categories(categories, timeout=None):
    """Cache product categories"""
    if timeout is None:
        timeout = current_app.config['CACHE_DEFAULT_TIMEOUT']
    cache.set('product_categories', categories, timeout=timeout)

def preload_popular_pages(app, pages=[1, 2, 3]):
    """Preload popular pages into cache in a background thread"""
    def _preload_worker():
        with app.app_context():
            from ..services.winit_api import WinitAPI
            
            app.logger.info(f"Preloading {len(pages)} popular product pages into cache")
            winit_api = WinitAPI.from_app(app)
            items_per_page = app.config.get('PRODUCT_PAGE_SIZE', 20)
            
            for page in pages:
                # Skip if already cached
                if get_cached_products(page) is not None:
                    continue
                    
                try:
                    # Similar logic to the main blueprint but simplified
                    api_page_size = 50
                    api_page = ((page - 1) * items_per_page) // api_page_size + 1
                    
                    response_data = winit_api.get_product_base_list(
                        warehouse_code='UKGF',
                        page_no=api_page,
                        page_size=api_page_size
                    )
                    
                    if response_data.get('code') == '0':
                        all_products = response_data.get('data', {}).get('SPUList', [])
                        in_stock_products = [p for p in all_products if p.get('totalInventory', 0) > 0]
                        
                        # Get total count for pagination if not already cached
                        if get_cached_product_count() is None and page == 1:
                            total_api_count = response_data.get('data', {}).get('pageParams', {}).get('totalCount', 0)
                            in_stock_ratio = len(in_stock_products) / len(all_products) if all_products else 0
                            total_in_stock_count = int(total_api_count * in_stock_ratio)
                            cache_product_count(total_in_stock_count)
                        
                        # Calculate which products to show for this page
                        offset = ((page - 1) * items_per_page) % api_page_size
                        
                        # If we need more products than what we got from the first API call
                        if len(in_stock_products) < offset + items_per_page:
                            # Get next page from API
                            next_response = winit_api.get_product_base_list(
                                warehouse_code='UKGF',
                                page_no=api_page + 1,
                                page_size=api_page_size
                            )
                            
                            if next_response.get('code') == '0':
                                next_products = next_response.get('data', {}).get('SPUList', [])
                                next_in_stock = [p for p in next_products if p.get('totalInventory', 0) > 0]
                                in_stock_products.extend(next_in_stock)
                        
                        # Get the slice of products for the requested page
                        start_idx = offset
                        end_idx = min(start_idx + items_per_page, len(in_stock_products))
                        page_products = in_stock_products[start_idx:end_idx]
                        
                        # Cache the products for this page
                        cache_products(page, page_products)
                        app.logger.info(f"Preloaded page {page} with {len(page_products)} products")
                except Exception as e:
                    app.logger.error(f"Error preloading page {page}: {str(e)}")
    
    # Start preloading in a background thread
    thread = threading.Thread(target=_preload_worker)
    thread.daemon = True
    thread.start()
    return thread 
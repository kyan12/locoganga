from flask_caching import Cache
from flask import current_app
import json

cache = Cache()

def init_cache(app):
    cache.init_app(app)

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

def get_cached_product_count():
    """Get the total number of products from cache"""
    return cache.get('total_product_count')

def cache_product_count(count, timeout=None):
    """Cache the total number of products"""
    if timeout is None:
        timeout = current_app.config['PRODUCT_CACHE_TIMEOUT']
    cache.set('total_product_count', count, timeout=timeout)

def invalidate_product_cache():
    """Invalidate all product-related cache entries"""
    cache.delete('total_product_count')
    # We'll implement a more sophisticated cache invalidation if needed
    # For now, we let the cache expire naturally for product pages

def get_cached_categories():
    """Get product categories from cache"""
    return cache.get('product_categories')

def cache_categories(categories, timeout=None):
    """Cache product categories"""
    if timeout is None:
        timeout = current_app.config['CACHE_DEFAULT_TIMEOUT']
    cache.set('product_categories', categories, timeout=timeout) 
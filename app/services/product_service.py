import json
import os
import logging
from flask import current_app, has_app_context, request
from .winit_api import WinitAPI

logger = logging.getLogger('product_service')

class ProductService:
    """Service for retrieving products with fallback mechanism"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.winit_api = WinitAPI.from_app(app)
        self.using_fallback = False
        
    @staticmethod
    def load_fallback_products(fallback_file=None):
        """Load products from fallback JSON file"""
        try:
            if has_app_context():
                fallback_file = fallback_file or os.path.join(
                    current_app.static_folder, 'fallback_products.json')
            else:
                fallback_file = fallback_file or 'app/static/fallback_products.json'
                
            if not os.path.exists(fallback_file):
                if has_app_context():
                    current_app.logger.error(f"Fallback file not found: {fallback_file}")
                else:
                    logger.error(f"Fallback file not found: {fallback_file}")
                return []
                
            with open(fallback_file, 'r', encoding='utf-8') as f:
                products = json.load(f)
                
            if has_app_context():
                current_app.logger.info(f"Loaded {len(products)} products from fallback file")
            else:
                logger.info(f"Loaded {len(products)} products from fallback file")
                
            return products
        except Exception as e:
            error_message = f"Error loading fallback products: {str(e)}"
            if has_app_context():
                current_app.logger.error(error_message)
            else:
                logger.error(error_message)
            return []
            
    def get_products(self, page=1, items_per_page=20, warehouse_code='UKGF', use_fallback=True):
        """
        Get products with fallback to JSON file if API fails
        
        Args:
            page: Page number (1-indexed)
            items_per_page: Number of items per page
            warehouse_code: Warehouse code
            use_fallback: Whether to use fallback JSON if API fails
            
        Returns:
            tuple: (products_for_page, pagination_info)
        """
        self.using_fallback = False
        
        if not has_app_context():
            if not self.app:
                return [], {'page': page, 'total_pages': 1}
            current_app = self.app
        
        try:
            # Try to fetch from API first with shorter timeout
            api_page_size = 50
            api_page = ((page - 1) * items_per_page) // api_page_size + 1
            
            # Get products from Winit API for the specific page
            response_data = self.winit_api._make_request(
                'wanyilian.supplier.spu.getProductBaseList',
                data={
                    'pageParams': {
                        'pageNo': api_page,
                        'pageSize': api_page_size,
                        'totalCount': 0
                    },
                    'warehouseCode': warehouse_code
                },
                timeout=5  # Short timeout to quickly fall back
            )
            
            # Process API response
            if not isinstance(response_data, dict) or response_data.get('code') != '0':
                if use_fallback:
                    return self._process_fallback(page, items_per_page)
                return [], {'page': page, 'total_pages': 1}
                
            # Process API products
            data = response_data.get('data', {}) or {}
            all_products = data.get('SPUList', []) or []
            
            # Filter in-stock products
            in_stock_products = [
                product for product in all_products
                if product.get('totalInventory', 0) > 0
            ]
            
            # Calculate pagination
            page_params = data.get('pageParams', {}) or {}
            total_api_count = page_params.get('totalCount', 0) or 0
            in_stock_ratio = len(in_stock_products) / max(len(all_products), 1)
            total_in_stock_count = int(total_api_count * in_stock_ratio)
            total_pages = max((total_in_stock_count + items_per_page - 1) // items_per_page, 1)
            
            # Get slice for current page
            offset = ((page - 1) * items_per_page) % api_page_size
            start_idx = offset
            end_idx = min(start_idx + items_per_page, len(in_stock_products))
            page_products = in_stock_products[start_idx:end_idx] if start_idx < len(in_stock_products) else []
            
            return page_products, {'page': page, 'total_pages': total_pages}
            
        except Exception as e:
            current_app.logger.warning(f"API request failed, using fallback: {str(e)}")
            if use_fallback:
                return self._process_fallback(page, items_per_page)
            return [], {'page': page, 'total_pages': 1}
            
    def _process_fallback(self, page, items_per_page):
        """Process fallback products for pagination"""
        self.using_fallback = True
        all_products = self.load_fallback_products()
        
        # Calculate pagination
        total_count = len(all_products)
        total_pages = max((total_count + items_per_page - 1) // items_per_page, 1)
        
        # Get slice for current page
        start_idx = (page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_count)
        page_products = all_products[start_idx:end_idx] if start_idx < total_count else []
        
        if has_app_context():
            current_app.logger.info(f"Using fallback products for page {page} ({len(page_products)} items)")
        
        return page_products, {'page': page, 'total_pages': total_pages, 'source': 'fallback'} 
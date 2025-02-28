"""
Service for handling Winit products, with fallback to database when API is unavailable
"""
import logging
from flask import current_app, has_app_context
from sqlalchemy.exc import SQLAlchemyError

from app.services.winit_api import WinitAPI

logger = logging.getLogger('winit_product_service')

class WinitProductService:
    """Service for handling Winit products with database fallback"""
    
    def __init__(self, app=None, db=None, api=None):
        self.app = app
        self.db = db
        self.api = api
        
        # Initialize API if not provided
        if self.api is None and self.app is not None:
            self.api = WinitAPI.from_app(self.app)
    
    def get_products(self, page=1, page_size=20, use_fallback=True):
        """
        Get products from Winit API with fallback to database
        
        Args:
            page: Page number for pagination
            page_size: Number of products per page
            use_fallback: Whether to use database fallback if API fails
            
        Returns:
            Dictionary with product list and pagination information
        """
        try:
            # Try to get products from the Winit API
            return self.api.get_product_base_list(page_no=page, page_size=page_size)
        except Exception as e:
            # Log the error
            error_message = f"Error getting products from Winit API: {e}"
            if has_app_context():
                current_app.logger.error(error_message)
            else:
                logger.error(error_message)
            
            # Use database fallback if enabled
            if use_fallback:
                return self._get_products_from_database(page, page_size)
            else:
                # Re-raise the exception if fallback is disabled
                raise
    
    def get_product_details(self, spu, use_fallback=True):
        """
        Get product details from Winit API with fallback to database
        
        Args:
            spu: Product SPU code
            use_fallback: Whether to use database fallback if API fails
            
        Returns:
            Dictionary with product details
        """
        try:
            # Try to get product details from the Winit API
            return self.api.get_product_details(spu)
        except Exception as e:
            # Log the error
            error_message = f"Error getting product details from Winit API: {e}"
            if has_app_context():
                current_app.logger.error(error_message)
            else:
                logger.error(error_message)
            
            # Use database fallback if enabled
            if use_fallback:
                return self._get_product_details_from_database(spu)
            else:
                # Re-raise the exception if fallback is disabled
                raise
    
    def _get_products_from_database(self, page=1, page_size=20):
        """
        Get products from the database
        
        Args:
            page: Page number for pagination
            page_size: Number of products per page
            
        Returns:
            Dictionary with product list and pagination information
        """
        try:
            # Import models here to avoid circular imports
            from app.models import WinitProduct
            
            # Log the fallback
            log_message = "Using products from database (API unavailable)"
            if has_app_context():
                current_app.logger.warning(log_message)
            else:
                logger.warning(log_message)
            
            # Query products from the database
            query = WinitProduct.query.filter_by(is_active=True)
            
            # Get total count
            total_count = query.count()
            
            # Apply pagination
            products = query.order_by(WinitProduct.name).offset((page - 1) * page_size).limit(page_size).all()
            
            # Convert to API response format
            product_list = []
            for product in products:
                # Use the stored additional data if available
                if product.additional_data:
                    product_data = product.additional_data_dict
                    product_list.append(product_data)
                else:
                    # Create a basic product data structure
                    product_list.append({
                        'SPU': product.spu,
                        'SKU': product.sku,
                        'title': product.name,
                        'price': product.price,
                        'stock': product.stock,
                        'images': [{'url': product.image_url}] if product.image_url else [],
                        'description': product.description,
                        'category': product.category,
                        'is_fallback': True
                    })
            
            # Format the response to match the Winit API response
            return {
                'code': '0',
                'message': 'Using database fallback',
                'data': {
                    'list': product_list,
                    'pageParams': {
                        'pageNo': page,
                        'pageSize': page_size,
                        'totalCount': total_count
                    }
                }
            }
        except SQLAlchemyError as e:
            error_message = f"Database error retrieving products: {e}"
            if has_app_context():
                current_app.logger.error(error_message)
            else:
                logger.error(error_message)
            
            # Return empty response
            return {
                'code': '1',
                'message': 'Database error',
                'data': {
                    'list': [],
                    'pageParams': {
                        'pageNo': page,
                        'pageSize': page_size,
                        'totalCount': 0
                    }
                }
            }
        except Exception as e:
            error_message = f"Error retrieving products from database: {e}"
            if has_app_context():
                current_app.logger.error(error_message)
            else:
                logger.error(error_message)
            
            # Return empty response
            return {
                'code': '1',
                'message': 'Error',
                'data': {
                    'list': [],
                    'pageParams': {
                        'pageNo': page,
                        'pageSize': page_size,
                        'totalCount': 0
                    }
                }
            }
    
    def _get_product_details_from_database(self, spu):
        """
        Get product details from the database
        
        Args:
            spu: Product SPU code
            
        Returns:
            Dictionary with product details
        """
        try:
            # Import models here to avoid circular imports
            from app.models import WinitProduct
            
            # Log the fallback
            log_message = f"Using product details from database for SPU {spu} (API unavailable)"
            if has_app_context():
                current_app.logger.warning(log_message)
            else:
                logger.warning(log_message)
            
            # Query the product from the database
            product = WinitProduct.query.filter_by(spu=spu, is_active=True).first()
            
            if product:
                # Use the stored additional data if available
                if product.additional_data:
                    product_data = product.additional_data_dict
                    
                    # Format the response to match the Winit API response
                    return {
                        'code': '0',
                        'message': 'Using database fallback',
                        'data': {
                            'list': [product_data]
                        }
                    }
                else:
                    # Create a basic product data structure
                    product_data = {
                        'SPU': product.spu,
                        'SKU': product.sku,
                        'title': product.name,
                        'price': product.price,
                        'stock': product.stock,
                        'images': [{'url': product.image_url}] if product.image_url else [],
                        'description': product.description,
                        'category': product.category,
                        'is_fallback': True
                    }
                    
                    # Format the response to match the Winit API response
                    return {
                        'code': '0',
                        'message': 'Using database fallback',
                        'data': {
                            'list': [product_data]
                        }
                    }
            else:
                # Product not found
                return {
                    'code': '0',
                    'message': 'Product not found',
                    'data': {
                        'list': []
                    }
                }
        except SQLAlchemyError as e:
            error_message = f"Database error retrieving product details: {e}"
            if has_app_context():
                current_app.logger.error(error_message)
            else:
                logger.error(error_message)
            
            # Return empty response
            return {
                'code': '1',
                'message': 'Database error',
                'data': {
                    'list': []
                }
            }
        except Exception as e:
            error_message = f"Error retrieving product details from database: {e}"
            if has_app_context():
                current_app.logger.error(error_message)
            else:
                logger.error(error_message)
            
            # Return empty response
            return {
                'code': '1',
                'message': 'Error',
                'data': {
                    'list': []
                }
            } 
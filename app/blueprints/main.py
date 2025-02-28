from flask import Blueprint, render_template, current_app, request, url_for, redirect
from ..services.winit_api import WinitAPI
from ..services.product_service import ProductService

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    requested_page = request.args.get('page', 1, type=int)
    items_per_page = current_app.config.get('PRODUCT_PAGE_SIZE', 20)
    
    # Create ProductService
    product_service = ProductService(current_app)
    
    try:
        # Get products with automatic fallback
        page_products, pagination = product_service.get_products(
            page=requested_page,
            items_per_page=items_per_page
        )
        
        # Check if we're using fallback
        using_fallback = 'source' in pagination and pagination['source'] == 'fallback'
        
        # If using fallback and not already indicating it in query params, redirect to add the indicator
        if using_fallback and request.args.get('source') != 'fallback':
            # Preserve existing query parameters
            args = request.args.copy()
            args['source'] = 'fallback'
            return redirect(url_for('main.index', **args))
        
        # If we got products (either from API or fallback), render the page
        return render_template('main/index.html', 
                             products=page_products,
                             pagination=pagination)
                             
    except Exception as e:
        current_app.logger.error(f"Error in index route: {e}")
        current_app.logger.exception("Detailed traceback:")
        
        # Try fallback as last resort
        try:
            fallback_products = ProductService.load_fallback_products()
            
            # Calculate pagination for fallback
            total_count = len(fallback_products)
            total_pages = max((total_count + items_per_page - 1) // items_per_page, 1)
            
            # Get slice for current page
            start_idx = (requested_page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, total_count)
            page_products = fallback_products[start_idx:end_idx] if start_idx < total_count else []
            
            current_app.logger.info(f"Using direct fallback after exception ({len(page_products)} items)")
            
            # Always show fallback notice in this case
            args = request.args.copy()
            args['source'] = 'fallback'
            return redirect(url_for('main.index', **args))
            
        except Exception as fallback_error:
            current_app.logger.error(f"Fallback also failed: {fallback_error}")
            return render_template('main/index.html', 
                                products=[], 
                                error=f"Error loading products. Please try again later.",
                                pagination={'page': requested_page, 'total_pages': 1})


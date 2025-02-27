from flask import Blueprint, render_template, current_app, request
from ..services.winit_api import WinitAPI

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    requested_page = request.args.get('page', 1, type=int)
    items_per_page = 20  # 5 columns × 4 rows
    in_stock_products = []
    current_api_page = 1
    total_in_stock_count = 0
    first_page = True

    # Initialize WinitAPI service
    winit_api = WinitAPI.from_app(current_app)

    while len(in_stock_products) < (requested_page * items_per_page):
        try:
            # Get products from Winit API
            response_data = winit_api.get_product_base_list(
                warehouse_code='UKGF',
                page_no=current_api_page,
                page_size=50
            )
            
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


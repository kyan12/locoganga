from flask import Blueprint, jsonify, request, current_app
from ..services.product_service import ProductService
from ..services.winit_api import WinitAPI

bp = Blueprint('products', __name__)

@bp.route('/api/products', methods=['GET'])
def get_products():
    """Get paginated list of products"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    category_id = request.args.get('category_id', type=int)

    winit_api = WinitAPI.from_app(current_app)
    product_service = ProductService(winit_api)
    
    products = product_service.get_products(page, per_page, category_id)
    
    return jsonify({
        'items': [{
            'spu': p.spu,
            'title': p.title,
            'description': p.description,
            'thumbnail': p.thumbnail,
            'total_inventory': p.total_inventory,
            'skus': [{
                'sku': sku.sku,
                'price': sku.settle_price,
                'inventory': sku.supply_inventory,
                'specification': sku.specification
            } for sku in p.skus]
        } for p in products.items],
        'total': products.total,
        'pages': products.pages,
        'current_page': products.page
    })

@bp.route('/api/products/<string:spu>', methods=['GET'])
def get_product(spu):
    """Get product details"""
    winit_api = WinitAPI.from_app(current_app)
    product_service = ProductService(winit_api)
    
    product = product_service.get_product(spu)
    if not product:
        return jsonify({'error': 'Product not found'}), 404

    return jsonify({
        'spu': product.spu,
        'title': product.title,
        'description': product.description,
        'thumbnail': product.thumbnail,
        'total_inventory': product.total_inventory,
        'skus': [{
            'sku': sku.sku,
            'price': sku.settle_price,
            'inventory': sku.supply_inventory,
            'specification': sku.specification,
            'weight': sku.weight,
            'dimensions': {
                'length': sku.length,
                'width': sku.width,
                'height': sku.height
            }
        } for sku in product.skus]
    })

@bp.route('/api/products/sync', methods=['POST'])
def sync_products():
    """Sync products from Winit API"""
    warehouse_code = request.json.get('warehouse_code')
    
    winit_api = WinitAPI.from_app(current_app)
    product_service = ProductService(winit_api)
    
    try:
        total_synced = product_service.sync_products(warehouse_code)
        return jsonify({
            'message': f'Successfully synced {total_synced} products',
            'total_synced': total_synced
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500 
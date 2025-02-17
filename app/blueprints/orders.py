from flask import Blueprint, jsonify, request, current_app, session
from flask_login import current_user, login_required
from ..services.order_service import OrderService
from ..services.cart_service import CartService
from ..services.payment_service import PaymentService
from ..services.winit_api import WinitAPI

bp = Blueprint('orders', __name__)

@bp.route('/api/orders', methods=['GET'])
@login_required
def get_orders():
    """Get user's orders"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    winit_api = WinitAPI.from_app(current_app)
    order_service = OrderService(winit_api)
    
    orders = order_service.get_user_orders(current_user, page, per_page)
    
    return jsonify({
        'items': [{
            'order_number': order.order_number,
            'status': order.status,
            'total_amount': order.total_amount,
            'created_at': order.created_at.isoformat(),
            'tracking_number': order.tracking_number,
            'items': [{
                'sku': item.sku,
                'quantity': item.quantity,
                'price': item.price,
                'title': item.title
            } for item in order.items]
        } for order in orders.items],
        'total': orders.total,
        'pages': orders.pages,
        'current_page': orders.page
    })

@bp.route('/api/orders/<string:order_number>', methods=['GET'])
@login_required
def get_order(order_number):
    """Get order details"""
    winit_api = WinitAPI.from_app(current_app)
    order_service = OrderService(winit_api)
    
    order = order_service.get_order(order_number)
    if not order or order.user_id != current_user.id:
        return jsonify({'error': 'Order not found'}), 404

    # Sync order status with Winit
    order_service.sync_order_status(order)

    return jsonify({
        'order_number': order.order_number,
        'status': order.status,
        'total_amount': order.total_amount,
        'created_at': order.created_at.isoformat(),
        'tracking_number': order.tracking_number,
        'shipping_info': {
            'name': order.shipping_name,
            'address': order.shipping_address,
            'city': order.shipping_city,
            'state': order.shipping_state,
            'country': order.shipping_country,
            'zipcode': order.shipping_zipcode,
            'phone': order.shipping_phone,
            'email': order.shipping_email
        },
        'items': [{
            'sku': item.sku,
            'quantity': item.quantity,
            'price': item.price,
            'title': item.title
        } for item in order.items]
    })

@bp.route('/api/orders', methods=['POST'])
@login_required
def create_order():
    """Create a new order"""
    # Validate shipping information
    shipping_info = request.json.get('shipping_info')
    if not shipping_info:
        return jsonify({'error': 'Shipping information is required'}), 400

    required_fields = ['name', 'address', 'city', 'state', 'country', 'zipcode', 'phone', 'email', 'delivery_method']
    missing_fields = [field for field in required_fields if field not in shipping_info]
    if missing_fields:
        return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

    # Get cart items
    cart_service = CartService()
    cart_items = cart_service.get_cart(session.id)
    if not cart_items:
        return jsonify({'error': 'Cart is empty'}), 400

    # Validate cart
    issues = cart_service.validate_cart(session.id)
    if issues:
        return jsonify({'error': 'Cart validation failed', 'issues': issues}), 400

    try:
        # Create order
        winit_api = WinitAPI.from_app(current_app)
        order_service = OrderService(winit_api)
        order = order_service.create_order(current_user, cart_items, shipping_info)

        # Create payment intent
        payment_service = PaymentService.from_app(current_app)
        payment_intent = payment_service.create_payment_intent(order)

        # Clear cart after successful order creation
        cart_service.clear_cart(session.id)

        return jsonify({
            'order': {
                'order_number': order.order_number,
                'total_amount': order.total_amount
            },
            'payment': payment_intent
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Failed to create order'}), 500

@bp.route('/api/orders/<string:order_number>/cancel', methods=['POST'])
@login_required
def cancel_order(order_number):
    """Cancel an order"""
    winit_api = WinitAPI.from_app(current_app)
    order_service = OrderService(winit_api)
    
    order = order_service.get_order(order_number)
    if not order or order.user_id != current_user.id:
        return jsonify({'error': 'Order not found'}), 404

    try:
        order_service.cancel_order(order)
        return jsonify({'message': 'Order cancelled successfully'})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Failed to cancel order'}), 500

@bp.route('/api/shipping/methods', methods=['GET'])
def get_shipping_methods():
    """Get available shipping methods for a warehouse"""
    warehouse_code = request.args.get('warehouse_code')
    if not warehouse_code:
        return jsonify({'error': 'Warehouse code is required'}), 400

    try:
        winit_api = WinitAPI.from_app(current_app)
        order_service = OrderService(winit_api)
        methods = order_service.get_delivery_methods(warehouse_code)
        
        return jsonify(methods)
    except Exception as e:
        return jsonify({'error': 'Failed to get shipping methods'}), 500 
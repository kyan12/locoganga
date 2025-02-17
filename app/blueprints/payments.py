from flask import Blueprint, jsonify, request, current_app
from flask_login import current_user, login_required
from ..services.payment_service import PaymentService
from ..services.order_service import OrderService
from ..services.winit_api import WinitAPI

bp = Blueprint('payments', __name__)

@bp.route('/api/payments/intent', methods=['POST'])
@login_required
def create_payment_intent():
    """Create a payment intent for an order"""
    order_number = request.json.get('order_number')
    if not order_number:
        return jsonify({'error': 'Order number is required'}), 400

    winit_api = WinitAPI.from_app(current_app)
    order_service = OrderService(winit_api)
    order = order_service.get_order(order_number)
    
    if not order or order.user_id != current_user.id:
        return jsonify({'error': 'Order not found'}), 404

    if order.status != 'pending':
        return jsonify({'error': 'Order is not in pending status'}), 400

    try:
        payment_service = PaymentService.from_app(current_app)
        payment_intent = payment_service.create_payment_intent(order)
        
        return jsonify(payment_intent)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/payments/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')

    try:
        payment_service = PaymentService.from_app(current_app)
        success = payment_service.handle_webhook(payload, sig_header)
        
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 400 
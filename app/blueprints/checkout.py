from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from datetime import datetime
import stripe
from ..models import CartItem, db
from ..services.winit_api import WinitAPI

bp = Blueprint('checkout', __name__)

@bp.route('/', methods=['GET'])
def checkout_page():
    # Ensure there is an active session with cart items
    if 'session_id' not in session:
        flash('Your cart is empty.', 'info')
        return redirect(url_for('main.index'))
    cart_items = CartItem.query.filter_by(session_id=session['session_id']).all()
    if not cart_items:
        flash('Your cart is empty.', 'info')
        return redirect(url_for('main.index'))

    # Fetch delivery methods via WinitAPI (using a default warehouse code e.g., 'UKGF')
    winit_api = WinitAPI.from_app(current_app)
    try:
        delivery_response = winit_api.get_delivery_methods('UKGF')
        # Assume delivery_response is a dict containing delivery methods in data key
        delivery_methods = delivery_response.get('data', []) if isinstance(delivery_response, dict) else []
    except Exception as e:
        current_app.logger.error('Error fetching delivery methods: ' + str(e))
        delivery_methods = []

    return render_template('checkout/checkout.html', cart_items=cart_items, delivery_methods=delivery_methods)

@bp.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    if 'session_id' not in session:
        return jsonify({'error': 'No cart session found'}), 400

    cart_items = CartItem.query.filter_by(session_id=session['session_id']).all()
    if not cart_items:
        return jsonify({'error': 'Cart is empty'}), 400

    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']

    # Store shipping info in session if provided
    shipping_data = request.form.to_dict() if request.form else {}
    if shipping_data:
        session['shipping_data'] = shipping_data

    # Create line items for Stripe
    line_items = []
    for item in cart_items:
        line_items.append({
            'price_data': {
                'currency': 'usd',  # You might want to make this dynamic based on the warehouse location
                'product_data': {
                    'name': item.title,
                    'images': [item.thumbnail] if item.thumbnail else [],
                },
                'unit_amount': int(item.price * 100),  # Stripe expects amounts in cents
            },
            'quantity': item.quantity,
        })

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=current_app.config['DOMAIN_URL'] + url_for('checkout.success') + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=current_app.config['DOMAIN_URL'] + url_for('checkout.cancel'),
            shipping_address_collection={
                'allowed_countries': ['US', 'GB', 'AU'],  # Add countries based on your warehouses
            },
            metadata={
                'cart_session_id': session['session_id']
            }
        )
        return jsonify({'id': checkout_session.id})
    except Exception as e:
        current_app.logger.error(f'Error creating checkout session: {str(e)}')
        return jsonify({'error': str(e)}), 403

@bp.route('/success')
def success():
    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
    
    # Get the Stripe checkout session
    checkout_session = stripe.checkout.Session.retrieve(request.args.get('session_id'))
    
    if not checkout_session:
        flash('Could not verify payment. Please contact support.', 'error')
        return redirect(url_for('main.index'))

    # Get cart items
    cart_items = CartItem.query.filter_by(session_id=checkout_session.metadata.cart_session_id).all()
    if not cart_items:
        flash('No items found in cart.', 'error')
        return redirect(url_for('main.index'))

    # Get shipping details from Stripe session
    shipping_details = checkout_session.shipping_details

    # Create Winit outbound order
    winit_api = WinitAPI.from_app(current_app)
    
    # Prepare package data
    package = {
        'packageNo': '',
        'warehouseCode': 'UKGF',  # You might want to make this dynamic
        'deliveryWayCode': 'OSF1010520',  # You might want to make this dynamic based on shipping method
        'authBarcode': '',
        'eBayOrderID': f'STRIPE_{checkout_session.id}',
        'productList': []
    }

    for item in cart_items:
        package['productList'].append({
            'productCode': item.sku,
            'productNum': item.quantity
        })

    # Prepare order data
    order_data = {
        'repeatable': 'Y',
        'isAuto': 'N',
        'sellerOrderNo': f'STRIPE_{checkout_session.id}',
        'recipientName': shipping_details.name,
        'phoneNum': shipping_details.phone or '0000000000',  # Stripe doesn't always provide phone
        'zipCode': shipping_details.address.postal_code,
        'emailAddress': checkout_session.customer_details.email,
        'state': shipping_details.address.country,
        'region': shipping_details.address.state,
        'city': shipping_details.address.city,
        'address1': shipping_details.address.line1,
        'address2': shipping_details.address.line2 or '',
        'packageList': [package]
    }

    try:
        # Create outbound order
        outbound_response = winit_api.create_outbound_order(order_data)
        order_nums = outbound_response.get('data', {}).get('orderNums', [])

        # Clear cart
        for item in cart_items:
            db.session.delete(item)
        db.session.commit()

        return render_template('checkout/confirmation.html', 
                             order_nums=order_nums,
                             seller_order_no=f'STRIPE_{checkout_session.id}')

    except Exception as e:
        current_app.logger.error(f'Error creating outbound order: {str(e)}')
        flash('There was an error processing your order. Our team has been notified.', 'error')
        return redirect(url_for('main.index'))

@bp.route('/cancel')
def cancel():
    flash('Payment was cancelled.', 'info')
    return redirect(url_for('cart.view_cart'))

@bp.route('/webhook', methods=['POST'])
def webhook():
    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
    webhook_secret = current_app.config['STRIPE_WEBHOOK_SECRET']
    
    try:
        event = stripe.Webhook.construct_event(
            payload=request.data,
            sig_header=request.headers.get('Stripe-Signature'),
            secret=webhook_secret
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 400

    # Handle specific events
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # You could add additional handling here, like sending confirmation emails
        current_app.logger.info(f'Payment successful for session {session.id}')
    
    return jsonify({'status': 'success'}) 
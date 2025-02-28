from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from datetime import datetime
import stripe
from ..models import CartItem, db
from ..services.winit_api import WinitAPI
from ..services.email_service import EmailService

bp = Blueprint('checkout', __name__)
email_service = EmailService()

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

    try:
        stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
        if not stripe.api_key:
            raise ValueError('Stripe API key is not configured')

        # Store shipping info in session if provided
        shipping_data = request.form.to_dict() if request.form else {}
        if shipping_data:
            session['shipping_data'] = shipping_data

        # Create line items for Stripe
        line_items = []
        for item in cart_items:
            if not item.price or item.price <= 0:
                raise ValueError(f'Invalid price for item {item.title}')
                
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': item.title,
                        'images': [item.thumbnail] if item.thumbnail else [],
                    },
                    'unit_amount': int(item.price * 100),  # Stripe expects amounts in cents
                },
                'quantity': item.quantity,
            })

        # Build absolute URLs for success and cancel endpoints
        domain_url = current_app.config.get('DOMAIN_URL') or request.host_url.rstrip('/')
        success_url = f"{domain_url}{url_for('checkout.success')}?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{domain_url}{url_for('checkout.cancel')}"

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            shipping_address_collection={
                'allowed_countries': ['US', 'GB', 'AU'],
            },
            metadata={
                'cart_session_id': session['session_id']
            }
        )
        return jsonify({'id': checkout_session.id})
    except ValueError as e:
        current_app.logger.error(f'Validation error in checkout: {str(e)}')
        return jsonify({'error': str(e)}), 400
    except stripe.error.StripeError as e:
        current_app.logger.error(f'Stripe error: {str(e)}')
        return jsonify({'error': 'Payment processing error. Please try again later.'}), 503
    except Exception as e:
        current_app.logger.error(f'Unexpected error in checkout: {str(e)}')
        return jsonify({'error': 'An unexpected error occurred. Please try again later.'}), 500

@bp.route('/success')
def success():
    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
    
    try:
        # Get the Stripe checkout session
        session_id = request.args.get('session_id')
        current_app.logger.info(f"Processing checkout with session_id: {session_id}")
        if not session_id:
            flash('Invalid checkout session.', 'error')
            return redirect(url_for('main.index'))
            
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        current_app.logger.info(f"Retrieved checkout session with ID: {session_id}")
        current_app.logger.debug(f"Checkout session type: {type(checkout_session)}")
        
        if not checkout_session:
            flash('Could not verify payment. Please contact support.', 'error')
            return redirect(url_for('main.index'))

        # Get cart items using the cart session ID from metadata
        current_app.logger.debug(f"Accessing metadata from checkout session")
        
        # Safely extract cart_session_id
        cart_session_id = None
        
        # Debug the metadata
        current_app.logger.debug(f"Checkout session metadata type: {type(getattr(checkout_session, 'metadata', None))}")
        
        if hasattr(checkout_session, 'metadata'):
            metadata = checkout_session.metadata
            current_app.logger.debug(f"Metadata direct access: {metadata}")
            
            if isinstance(metadata, dict):
                cart_session_id = metadata.get('cart_session_id')
                current_app.logger.debug(f"Retrieved cart_session_id from metadata dict: {cart_session_id}")
            elif hasattr(metadata, 'cart_session_id'):
                cart_session_id = metadata.cart_session_id
                current_app.logger.debug(f"Retrieved cart_session_id from metadata object: {cart_session_id}")
            elif isinstance(metadata, str):
                # Handle case where metadata might be a string
                current_app.logger.debug(f"Metadata is a string: {metadata}")
                # Try to parse it as JSON if it looks like JSON
                if metadata.startswith('{') and metadata.endswith('}'):
                    try:
                        import json
                        metadata_dict = json.loads(metadata)
                        cart_session_id = metadata_dict.get('cart_session_id')
                        current_app.logger.debug(f"Parsed metadata string as JSON, got cart_session_id: {cart_session_id}")
                    except json.JSONDecodeError:
                        current_app.logger.error(f"Failed to parse metadata string as JSON: {metadata}")
        else:
            # Try dictionary access
            current_app.logger.debug(f"No metadata attribute, trying dictionary access")
            try:
                metadata = checkout_session.get('metadata')
                current_app.logger.debug(f"Metadata dict access: {metadata}")
                if metadata and isinstance(metadata, dict):
                    cart_session_id = metadata.get('cart_session_id')
                    current_app.logger.debug(f"Retrieved cart_session_id from metadata dict: {cart_session_id}")
            except (AttributeError, TypeError) as e:
                current_app.logger.error(f"Error accessing metadata as dictionary: {e}")

        # Final fallback - try to use the Flask session ID
        if not cart_session_id and 'session_id' in session:
            current_app.logger.debug("Using session['session_id'] as fallback")
            cart_session_id = session['session_id']
        
        current_app.logger.info(f"Using cart session ID: {cart_session_id}")
        
        if not cart_session_id:
            flash('Could not identify your cart. Please try again.', 'error')
            return redirect(url_for('main.index'))
        
        cart_items = CartItem.query.filter_by(session_id=cart_session_id).all()
        current_app.logger.info(f"Found {len(cart_items)} cart items")
        
        if not cart_items:
            flash('No items found in cart.', 'error')
            return redirect(url_for('main.index'))

        # Calculate total
        total = sum(item.price * item.quantity for item in cart_items)
        current_app.logger.info(f"Order total: {total}")

        # Initialize default values
        shipping_name = ''
        customer_email = ''
        customer_phone = '0000000000'
        address_line1 = ''
        address_line2 = ''
        city = ''
        state = ''
        postal_code = ''
        country = ''

        current_app.logger.debug("Processing shipping and customer details")
        
        # First try direct attribute access safely
        try:
            # Log each step to identify where the error might be
            current_app.logger.debug("Attempting to access shipping_details as attribute")
            if hasattr(checkout_session, 'shipping_details'):
                shipping_details = checkout_session.shipping_details
                current_app.logger.debug(f"shipping_details type: {type(shipping_details)}")
                
                if shipping_details:
                    # Get shipping name
                    if hasattr(shipping_details, 'name'):
                        shipping_name = shipping_details.name
                        current_app.logger.debug(f"Got shipping_name: {shipping_name}")
                    
                    # Get shipping address
                    if hasattr(shipping_details, 'address'):
                        shipping_address = shipping_details.address
                        current_app.logger.debug(f"shipping_address type: {type(shipping_address)}")
                        
                        if hasattr(shipping_address, 'line1'):
                            address_line1 = shipping_address.line1
                        if hasattr(shipping_address, 'line2'):
                            address_line2 = shipping_address.line2
                        if hasattr(shipping_address, 'city'):
                            city = shipping_address.city
                        if hasattr(shipping_address, 'state'):
                            state = shipping_address.state
                        if hasattr(shipping_address, 'postal_code'):
                            postal_code = shipping_address.postal_code
                        if hasattr(shipping_address, 'country'):
                            country = shipping_address.country
            
            current_app.logger.debug("Attempting to access customer_details as attribute")
            if hasattr(checkout_session, 'customer_details'):
                customer_details = checkout_session.customer_details
                current_app.logger.debug(f"customer_details type: {type(customer_details)}")
                
                if customer_details:
                    if hasattr(customer_details, 'email'):
                        customer_email = customer_details.email
                        current_app.logger.debug(f"Got customer_email: {customer_email}")
                    if hasattr(customer_details, 'phone'):
                        customer_phone = customer_details.phone
                        current_app.logger.debug(f"Got customer_phone: {customer_phone}")
        
        except Exception as e:
            current_app.logger.error(f"Error accessing attributes: {str(e)}")
        
        # Try dictionary access as fallback
        if not shipping_name or not address_line1:
            current_app.logger.debug("Trying dictionary access for shipping details")
            try:
                shipping_dict = checkout_session.get('shipping_details', {})
                if shipping_dict:
                    shipping_name = shipping_dict.get('name', shipping_name)
                    address_dict = shipping_dict.get('address', {})
                    address_line1 = address_dict.get('line1', address_line1)
                    address_line2 = address_dict.get('line2', address_line2)
                    city = address_dict.get('city', city)
                    state = address_dict.get('state', state)
                    postal_code = address_dict.get('postal_code', postal_code)
                    country = address_dict.get('country', country)
            except Exception as e:
                current_app.logger.error(f"Error accessing shipping details as dict: {str(e)}")
        
        if not customer_email:
            current_app.logger.debug("Trying dictionary access for customer details")
            try:
                customer_dict = checkout_session.get('customer_details', {})
                if customer_dict:
                    customer_email = customer_dict.get('email', '')
                    customer_phone = customer_dict.get('phone', customer_phone)
            except Exception as e:
                current_app.logger.error(f"Error accessing customer details as dict: {str(e)}")

        # Ensure we have required values with fallbacks
        if not customer_email:
            current_app.logger.warning("Missing customer email, using fallback")
            customer_email = "customer@example.com"  # Fallback email
            
        if not shipping_name:
            current_app.logger.warning("Missing shipping name, using fallback")
            shipping_name = "Customer"  # Fallback name

        current_app.logger.info(f"Shipping to: {shipping_name}, {address_line1}, {city}, {state}, {postal_code}, {country}")
        current_app.logger.info(f"Customer contact: {customer_email}, {customer_phone}")

        # Create a simulated order number instead of using Winit API
        current_app.logger.debug("Creating simulated order number (Winit integration disabled)")
        order_number = f"STRIPE_{session_id}"
        current_app.logger.info(f"Order created with number: {order_number}")

        # Prepare email data
        current_app.logger.debug("Preparing email data")
        email_data = {
            'email': customer_email,
            'items': cart_items,
            'total': total,
            'shipping_details': {
                'name': shipping_name,
                'address': {
                    'line1': address_line1,
                    'line2': address_line2 or '',
                    'city': city,
                    'state': state,
                    'postal_code': postal_code,
                    'country': country
                }
            },
            'order_number': order_number
        }
        
        # Send confirmation email
        current_app.logger.debug("Sending confirmation email")
        email_service = EmailService(current_app)
        email_sent = email_service.send_order_confirmation(email_data)
        current_app.logger.info(f"Email sent: {email_sent}")

        # Clear cart
        current_app.logger.debug("Clearing cart items")
        for item in cart_items:
            db.session.delete(item)
        db.session.commit()
        current_app.logger.info("Cart cleared successfully")

        # Render confirmation page
        current_app.logger.debug("Rendering confirmation page")
        return render_template('checkout/confirmation.html',
                            items=cart_items,
                            total=total,
                            shipping_details=email_data['shipping_details'],
                            order_number=order_number,
                            order_date=datetime.now().strftime('%B %d, %Y'))

    except Exception as e:
        current_app.logger.error(f"Error processing order completion: {str(e)}")
        current_app.logger.exception("Detailed traceback:")
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
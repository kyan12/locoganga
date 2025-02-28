from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from datetime import datetime
import stripe
import time
import requests
from requests.exceptions import RequestException
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

    # Get publishable key for rendering
    stripe_publishable_key = current_app.config.get('STRIPE_PUBLISHABLE_KEY', '')
    if not stripe_publishable_key:
        current_app.logger.warning("STRIPE_PUBLISHABLE_KEY is not set")

    return render_template('checkout/checkout.html', 
                           cart_items=cart_items, 
                           delivery_methods=delivery_methods,
                           stripe_key=stripe_publishable_key)

@bp.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    if 'session_id' not in session:
        return jsonify({'error': 'No cart session found'}), 400

    cart_items = CartItem.query.filter_by(session_id=session['session_id']).all()
    if not cart_items:
        return jsonify({'error': 'Cart is empty'}), 400

    try:
        # Load API key and validate it
        stripe_secret_key = current_app.config.get('STRIPE_SECRET_KEY')
        if not stripe_secret_key:
            current_app.logger.error("STRIPE_SECRET_KEY is not set")
            return jsonify({'error': 'Payment service is not configured'}), 500

        # Set Stripe API key
        stripe.api_key = stripe_secret_key
        
        # Log the API key length (don't log the actual key for security)
        current_app.logger.info(f"Using Stripe API key (length: {len(stripe_secret_key)})")

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
        # Fix URL construction to ensure valid URLs
        server_name = current_app.config.get('SERVER_NAME')
        scheme = current_app.config.get('PREFERRED_URL_SCHEME', 'https')
        
        # Log server configuration for debugging
        current_app.logger.info(f"Server name config: {server_name}")
        current_app.logger.info(f"URL scheme: {scheme}")
        
        if server_name:
            # Use configured server name
            base_url = f"{scheme}://{server_name}"
            current_app.logger.info(f"Using configured base URL: {base_url}")
        else:
            # Fallback to request.host_url (but ensure it doesn't end with a slash)
            base_url = request.host_url.rstrip('/')
            current_app.logger.info(f"Using request host URL: {base_url}")
        
        # Generate absolute URLs with proper formatting for Stripe
        success_path = url_for('checkout.success')
        cancel_path = url_for('checkout.cancel')
        
        # Ensure paths start with slash
        if not success_path.startswith('/'):
            success_path = '/' + success_path
        if not cancel_path.startswith('/'):
            cancel_path = '/' + cancel_path
            
        success_url = f"{base_url}{success_path}?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{base_url}{cancel_path}"
        
        # Log the generated URLs
        current_app.logger.info(f"Success URL template: {success_url}")
        current_app.logger.info(f"Cancel URL: {cancel_url}")
        
        # Prepare checkout session parameters
        checkout_params = {
            'payment_method_types': ['card'],
            'line_items': line_items,
            'mode': 'payment',
            'success_url': success_url,
            'cancel_url': cancel_url,
            'shipping_address_collection': {
                'allowed_countries': ['US', 'GB', 'AU'],
            },
            'metadata': {
                'cart_session_id': session['session_id']
            }
        }
        
        # Log attempt to create session
        current_app.logger.info(f"Attempting to create Stripe checkout session")
        
        # Create checkout session with retry mechanism
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                checkout_session = stripe.checkout.Session.create(**checkout_params)
                current_app.logger.info(f"Stripe checkout session created successfully: {checkout_session.id}")
                return jsonify({'id': checkout_session.id})
            except (stripe.error.APIConnectionError, requests.exceptions.RequestException) as e:
                # Network-related errors - may be worth retrying
                current_app.logger.warning(f"Network error on attempt {attempt+1}/{max_retries}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    current_app.logger.error(f"Failed to connect to Stripe API after {max_retries} attempts")
                    return jsonify({'error': 'Cannot connect to payment service. Please try again later.'}), 503
            except stripe.error.StripeError as e:
                # Other Stripe errors - log details and don't retry
                current_app.logger.error(f"Stripe error: {str(e)}")
                error_msg = 'Payment processing error. Please try again later.'
                # Provide more specific messages for common errors
                if isinstance(e, stripe.error.CardError):
                    error_msg = 'Your card was declined. Please try another payment method.'
                elif isinstance(e, stripe.error.InvalidRequestError):
                    error_msg = 'Invalid request to payment processor. Please contact support.'
                return jsonify({'error': error_msg}), 503
                
    except ValueError as e:
        current_app.logger.error(f'Validation error in checkout: {str(e)}')
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f'Unexpected error in checkout: {str(e)}')
        current_app.logger.exception("Detailed traceback:")
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
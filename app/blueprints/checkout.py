from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from datetime import datetime
import stripe
from ..models import CartItem, db
from ..services.email_service import EmailService

bp = Blueprint('checkout', __name__)

FREE_SHIPPING_MIN = 35.00
STANDARD_SHIPPING = 5.99


def cart_items():
    if 'session_id' not in session:
        return []
    return CartItem.query.filter_by(session_id=session['session_id']).all()


def totals(items):
    subtotal = round(sum((i.price or 0) * (i.quantity or 0) for i in items), 2)
    shipping = 0.0 if subtotal >= FREE_SHIPPING_MIN or not items else STANDARD_SHIPPING
    return subtotal, shipping, round(subtotal + shipping, 2)


def _get(obj, key, default=None):
    """Read a field from a Stripe object or dict without raising."""
    if obj is None:
        return default
    try:
        val = obj.get(key) if hasattr(obj, 'get') else getattr(obj, key, None)
    except Exception:
        val = getattr(obj, key, None)
    return default if val is None else val


def order_number_for(session_id):
    return 'LG-' + session_id[-10:].upper()


@bp.route('/', methods=['GET'])
def checkout_page():
    items = cart_items()
    if not items:
        flash('Your cart is empty.', 'info')
        return redirect(url_for('main.index'))
    subtotal, shipping, total = totals(items)
    return render_template('checkout/checkout.html', cart_items=items, subtotal=subtotal,
                           shipping=shipping, total=total, free_shipping_min=FREE_SHIPPING_MIN)


@bp.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    wants_json = request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def fail(msg, code):
        if wants_json:
            return jsonify({'error': msg}), code
        flash(msg, 'error')
        return redirect(url_for('cart.view_cart'))

    items = cart_items()
    if not items:
        return fail('Your cart is empty.', 400)

    secret = current_app.config.get('STRIPE_SECRET_KEY')
    if not secret:
        current_app.logger.error('STRIPE_SECRET_KEY is not set')
        return fail('Payment service is temporarily unavailable. Please try again shortly.', 503)
    stripe.api_key = secret

    line_items = []
    for item in items:
        if not item.price or item.price <= 0:
            return fail(f'{item.title} is currently unavailable.', 400)
        line_items.append({
            'price_data': {
                'currency': 'usd',
                'product_data': {'name': item.title[:250],
                                 'images': [item.thumbnail] if item.thumbnail else []},
                'unit_amount': int(round(item.price * 100)),
            },
            'quantity': item.quantity,
        })

    _, shipping, _ = totals(items)
    shipping_option = {
        'shipping_rate_data': {
            'type': 'fixed_amount',
            'fixed_amount': {'amount': int(round(shipping * 100)), 'currency': 'usd'},
            'display_name': 'Free standard shipping' if shipping == 0 else 'Standard shipping',
            'delivery_estimate': {'minimum': {'unit': 'business_day', 'value': 5},
                                  'maximum': {'unit': 'business_day', 'value': 10}},
        }
    }

    base_url = request.host_url.rstrip('/')
    try:
        checkout_session = stripe.checkout.Session.create(
            mode='payment',
            line_items=line_items,
            success_url=f"{base_url}{url_for('checkout.success')}?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base_url}{url_for('checkout.cancel')}",
            shipping_address_collection={'allowed_countries': ['US']},
            shipping_options=[shipping_option],
            phone_number_collection={'enabled': True},
            metadata={'cart_session_id': session['session_id']},
        )
    except stripe.error.StripeError as e:
        current_app.logger.error(f'Stripe error creating checkout session: {e}')
        return fail('We could not start checkout. Please try again in a moment.', 502)

    if wants_json:
        return jsonify({'id': checkout_session.id, 'url': checkout_session.url})
    return redirect(checkout_session.url, code=303)


@bp.route('/success')
def success():
    session_id = request.args.get('session_id', '')
    if not session_id.startswith('cs_'):
        return redirect(url_for('main.index'))
    stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')

    try:
        cs = stripe.checkout.Session.retrieve(session_id)
        if _get(cs, 'payment_status') not in ('paid', 'no_payment_required'):
            flash('Your payment was not completed. Your cart has been saved.', 'error')
            return redirect(url_for('cart.view_cart'))
        lines = stripe.checkout.Session.list_line_items(session_id, limit=100)
    except stripe.error.StripeError as e:
        current_app.logger.error(f'Could not verify checkout session {session_id}: {e}')
        flash('We could not confirm your payment yet. If you were charged, contact support and we will help right away.', 'error')
        return redirect(url_for('cart.view_cart'))

    # Order lines come from Stripe so the confirmation stays accurate on reload
    cart_session_id = _get(_get(cs, 'metadata', {}), 'cart_session_id')
    cart = CartItem.query.filter_by(session_id=cart_session_id).all() if cart_session_id else []
    thumbs = {c.title[:250]: c.thumbnail for c in cart}
    items = []
    for li in _get(lines, 'data', []):
        qty = _get(li, 'quantity', 1) or 1
        items.append({
            'title': _get(li, 'description', 'Item'),
            'quantity': qty,
            'price': _get(li, 'amount_subtotal', 0) / 100 / qty,
            'thumbnail': thumbs.get(_get(li, 'description')),
        })

    total = _get(cs, 'amount_total', 0) / 100
    shipping_cost = _get(_get(cs, 'total_details', {}), 'amount_shipping', 0) / 100
    customer = _get(cs, 'customer_details', {})
    ship = _get(cs, 'shipping_details') or _get(_get(cs, 'collected_information', {}), 'shipping_details') or {}
    addr = _get(ship, 'address') or _get(customer, 'address', {})
    shipping_details = {
        'name': _get(ship, 'name') or _get(customer, 'name', ''),
        'address': {k: _get(addr, k, '') for k in ('line1', 'line2', 'city', 'state', 'postal_code', 'country')},
    }
    order_number = order_number_for(session_id)

    # First visit after payment: send the confirmation once and clear the cart
    if cart:
        email = _get(customer, 'email')
        if email:
            try:
                EmailService(current_app).send_order_confirmation({
                    'email': email, 'items': items, 'total': total,
                    'shipping_details': shipping_details, 'order_number': order_number,
                })
            except Exception as e:
                current_app.logger.error(f'Order email failed for {order_number}: {e}')
        for c in cart:
            db.session.delete(c)
        db.session.commit()

    created = _get(cs, 'created')
    return render_template('checkout/confirmation.html', items=items, total=total,
                           shipping_cost=shipping_cost, shipping_details=shipping_details,
                           email=_get(customer, 'email', ''), order_number=order_number,
                           order_date=(datetime.fromtimestamp(created) if created else datetime.now()).strftime('%B %d, %Y'))


@bp.route('/cancel')
def cancel():
    flash('Checkout was cancelled. Your cart is saved.', 'info')
    return redirect(url_for('cart.view_cart'))


@bp.route('/webhook', methods=['POST'])
def webhook():
    stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
    try:
        event = stripe.Webhook.construct_event(
            payload=request.data,
            sig_header=request.headers.get('Stripe-Signature'),
            secret=current_app.config.get('STRIPE_WEBHOOK_SECRET'),
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 400

    if event['type'] == 'checkout.session.completed':
        obj = event['data']['object']
        current_app.logger.info(f"Payment completed for {order_number_for(obj['id'])} ({obj['id']})")
    return jsonify({'status': 'success'})

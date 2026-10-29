from flask import Blueprint, jsonify, session, request, render_template, current_app
from ..services.product_service import Catalog
from ..models import CartItem, db
import hashlib
from datetime import datetime

bp = Blueprint('cart', __name__)

@bp.route('/add', methods=['POST'])
def add_to_cart():
    if 'session_id' not in session:
        session['session_id'] = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()
    
    data = request.get_json(silent=True) or {}
    sku = data.get('sku')
    qty = max(1, min(int(data.get('quantity') or 1), 20))

    if not sku:
        return jsonify({'error': 'SKU is required'}), 400

    # Title, image and price always come from the catalog, never from the client
    product, variant = Catalog.by_sku(sku)
    if not product or product.get('totalInventory', 0) <= 0:
        return jsonify({'error': 'This item is unavailable'}), 404
    retail = current_app.jinja_env.filters['retail'](variant['supplyPrice'])
    title = product['title'] + (f" ({variant['option']})" if variant.get('option') else '')

    cart_item = CartItem.query.filter_by(
        sku=sku,
        session_id=session['session_id']
    ).first()

    if cart_item:
        cart_item.quantity = min(cart_item.quantity + qty, 20)
        cart_item.price = retail
    else:
        cart_item = CartItem(
            sku=sku,
            session_id=session['session_id'],
            title=title[:200],
            price=retail,
            quantity=qty,
            thumbnail=variant.get('image') or product['thumbnail'],
            spu=product['SPU']
        )
        db.session.add(cart_item)
    
    db.session.commit()
    count = sum(i.quantity or 0 for i in CartItem.query.filter_by(session_id=session['session_id']).all())
    return jsonify({'message': 'Added to cart', 'cart_count': count})

@bp.route('/', methods=['GET'])
def view_cart():
    from .checkout import cart_items, totals, FREE_SHIPPING_MIN
    items = cart_items()
    subtotal, shipping, total = totals(items)
    return render_template('cart/cart.html', cart_items=items, subtotal=subtotal, shipping=shipping,
                           total=total, free_shipping_min=FREE_SHIPPING_MIN)

@bp.route('/update', methods=['POST'])
def update_cart():
    if 'session_id' not in session:
        return jsonify({'error': 'No session found'}), 400
    
    data = request.get_json(silent=True) or {}
    sku = data.get('sku')
    change = int(data.get('change') or 0)
    
    if not sku:
        return jsonify({'error': 'SKU is required'}), 400
    
    cart_item = CartItem.query.filter_by(
        sku=sku,
        session_id=session['session_id']
    ).first()
    
    if cart_item:
        cart_item.quantity = max(0, min(cart_item.quantity + change, 20))
        if cart_item.quantity == 0:
            db.session.delete(cart_item)
        db.session.commit()
        
    return jsonify({'message': 'Cart updated'})
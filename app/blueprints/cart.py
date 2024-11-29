from flask import Blueprint, jsonify, session, request, render_template
from ..models import CartItem, db
import hashlib
from datetime import datetime

bp = Blueprint('cart', __name__)

@bp.route('/add', methods=['POST'])
def add_to_cart():
    if 'session_id' not in session:
        session['session_id'] = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()
    
    data = request.json
    sku = data.get('sku')
    
    if not sku:
        return jsonify({'error': 'SKU is required'}), 400
    
    cart_item = CartItem.query.filter_by(
        sku=sku,
        session_id=session['session_id']
    ).first()
    
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItem(
            sku=sku,
            session_id=session['session_id'],
            title=data.get('title'),
            price=data.get('price'),
            thumbnail=data.get('thumbnail'),
            spu=data.get('spu')
        )
        db.session.add(cart_item)
    
    db.session.commit()
    return jsonify({'message': 'Added to cart'})

@bp.route('/', methods=['GET'])
def view_cart():
    if 'session_id' not in session:
        return render_template('cart/cart.html', cart_items=[], total=0)
    
    cart_items = CartItem.query.filter_by(session_id=session['session_id']).all()
    total = sum(item.price * item.quantity for item in cart_items) if cart_items else 0
    
    return render_template('cart/cart.html', cart_items=cart_items, total=total)

@bp.route('/update', methods=['POST'])
def update_cart():
    if 'session_id' not in session:
        return jsonify({'error': 'No session found'}), 400
    
    data = request.json
    sku = data.get('sku')
    change = data.get('change', 0)
    
    if not sku:
        return jsonify({'error': 'SKU is required'}), 400
    
    cart_item = CartItem.query.filter_by(
        sku=sku,
        session_id=session['session_id']
    ).first()
    
    if cart_item:
        cart_item.quantity = max(0, cart_item.quantity + change)
        if cart_item.quantity == 0:
            db.session.delete(cart_item)
        db.session.commit()
        
    return jsonify({'message': 'Cart updated'})
from flask import Blueprint, jsonify, session, request
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
            session_id=session['session_id']
        )
        db.session.add(cart_item)
    
    db.session.commit()
    return jsonify({'message': 'Added to cart'})

@bp.route('/', methods=['GET'])
def view_cart():
    if 'session_id' not in session:
        return jsonify({'items': []})
    
    cart_items = CartItem.query.filter_by(session_id=session['session_id']).all()
    return jsonify({'items': [{'sku': item.sku, 'quantity': item.quantity} for item in cart_items]})
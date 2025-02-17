from flask import Blueprint, jsonify, session, request, render_template
from ..models import CartItem, db
import hashlib
from datetime import datetime
from ..services.cart_service import CartService

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

@bp.route('/api/cart', methods=['GET'])
def get_cart():
    """Get cart contents"""
    cart_service = CartService()
    cart_items = cart_service.get_cart(session.id)
    
    return jsonify({
        'items': [{
            'sku': item.sku,
            'quantity': item.quantity,
            'title': item.title,
            'price': item.price,
            'thumbnail': item.thumbnail,
            'total': item.price * item.quantity
        } for item in cart_items],
        'total': cart_service.get_cart_total(session.id)
    })

@bp.route('/api/cart/add', methods=['POST'])
def add_to_cart_api():
    """Add item to cart"""
    data = request.json
    if not data or 'sku' not in data:
        return jsonify({'error': 'SKU is required'}), 400

    quantity = data.get('quantity', 1)
    
    try:
        cart_service = CartService()
        cart_item = cart_service.add_item(session.id, data['sku'], quantity)
        
        return jsonify({
            'message': 'Item added to cart',
            'item': {
                'sku': cart_item.sku,
                'quantity': cart_item.quantity,
                'title': cart_item.title,
                'price': cart_item.price,
                'thumbnail': cart_item.thumbnail,
                'total': cart_item.price * cart_item.quantity
            }
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Failed to add item to cart'}), 500

@bp.route('/api/cart/update', methods=['PUT'])
def update_cart_api():
    """Update cart item quantity"""
    data = request.json
    if not data or 'sku' not in data or 'quantity' not in data:
        return jsonify({'error': 'SKU and quantity are required'}), 400

    try:
        cart_service = CartService()
        cart_item = cart_service.update_quantity(session.id, data['sku'], data['quantity'])
        
        if not cart_item and data['quantity'] > 0:
            return jsonify({'error': 'Item not found in cart'}), 404

        return jsonify({
            'message': 'Cart updated',
            'item': {
                'sku': cart_item.sku,
                'quantity': cart_item.quantity,
                'title': cart_item.title,
                'price': cart_item.price,
                'thumbnail': cart_item.thumbnail,
                'total': cart_item.price * cart_item.quantity
            } if cart_item else None
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Failed to update cart'}), 500

@bp.route('/api/cart/remove', methods=['DELETE'])
def remove_from_cart_api():
    """Remove item from cart"""
    sku = request.args.get('sku')
    if not sku:
        return jsonify({'error': 'SKU is required'}), 400

    try:
        cart_service = CartService()
        success = cart_service.remove_item(session.id, sku)
        
        if not success:
            return jsonify({'error': 'Item not found in cart'}), 404

        return jsonify({'message': 'Item removed from cart'})
    except Exception as e:
        return jsonify({'error': 'Failed to remove item from cart'}), 500

@bp.route('/api/cart/clear', methods=['POST'])
def clear_cart_api():
    """Clear all items from cart"""
    try:
        cart_service = CartService()
        cart_service.clear_cart(session.id)
        return jsonify({'message': 'Cart cleared'})
    except Exception as e:
        return jsonify({'error': 'Failed to clear cart'}), 500

@bp.route('/api/cart/validate', methods=['GET'])
def validate_cart_api():
    """Validate cart items against current inventory"""
    cart_service = CartService()
    issues = cart_service.validate_cart(session.id)
    
    return jsonify({
        'valid': len(issues) == 0,
        'issues': issues
    })
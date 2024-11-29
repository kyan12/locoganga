# app.py
from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
import requests
import hashlib
from datetime import datetime
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecommerce.db'
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this in production
db = SQLAlchemy(app)

# API Configuration
API_CONFIG = {
    'base_url': 'https://openapi.wanyilian.com/cedpopenapi/service',
    'app_key': 'your_app_key',
    'token': 'your_token',  # Get this from Wanyi Chain system settings
    'platform': 'SELLERERP'
}

# Database Models
class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    session_id = db.Column(db.String(100), nullable=False)

def generate_sign(params):
    """Generate API signature based on provided documentation"""
    # Sort parameters alphabetically
    sorted_params = dict(sorted(params.items()))
    
    # Create signature string
    sign_string = API_CONFIG['token']
    for key, value in sorted_params.items():
        if isinstance(value, dict):
            value = json.dumps(value)
        sign_string += key + str(value)
    sign_string += API_CONFIG['token']
    
    # Generate MD5 hash and convert to uppercase
    return hashlib.md5(sign_string.encode()).hexdigest().upper()

def fetch_products(page=1, page_size=10):
    """Fetch products from the Wanyilian API"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    data = {
        "SPU": "",
        "SKU": ""
    }
    
    params = {
        'action': 'wanyilian.supplier.spu.querySPUList',
        'app_key': API_CONFIG['app_key'],
        'data': data,
        'format': 'json',
        'language': 'zh_CN',
        'platform': API_CONFIG['platform'],
        'sign_method': 'md5',
        'timestamp': timestamp,
        'version': '1.0'
    }
    
    params['sign'] = generate_sign(params)
    
    try:
        response = requests.post(API_CONFIG['base_url'], json=params)
        return response.json()
    except Exception as e:
        print(f"Error fetching products: {e}")
        return None

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    products = fetch_products(page=page)
    
    if not products or products.get('code') != '0':
        return render_template('index.html', products=[], error="Failed to fetch products")
    
    return render_template('index.html', 
                         products=products['data']['SPUList'],
                         page=page,
                         total_pages=(products['data']['pageParams']['totalCount'] // 10) + 1)

@app.route('/cart/add', methods=['POST'])
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

@app.route('/cart')
def view_cart():
    if 'session_id' not in session:
        return jsonify({'items': []})
    
    cart_items = CartItem.query.filter_by(session_id=session['session_id']).all()
    return jsonify({'items': [{'sku': item.sku, 'quantity': item.quantity} for item in cart_items]})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
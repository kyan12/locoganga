from flask import Blueprint, render_template, current_app, request
import requests
import hashlib
from datetime import datetime
import json

bp = Blueprint('main', __name__)

def generate_sign(params):
    """Generate API signature based on provided documentation"""
    sorted_params = dict(sorted(params.items()))
    
    sign_string = current_app.config['API_CONFIG']['token']
    for key, value in sorted_params.items():
        if isinstance(value, dict):
            value = json.dumps(value)
        sign_string += key + str(value)
    sign_string += current_app.config['API_CONFIG']['token']
    
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
        'app_key': current_app.config['API_CONFIG']['app_key'],
        'data': data,
        'format': 'json',
        'language': 'zh_CN',
        'platform': current_app.config['API_CONFIG']['platform'],
        'sign_method': 'md5',
        'timestamp': timestamp,
        'version': '1.0'
    }
    
    params['sign'] = generate_sign(params)
    
    try:
        response = requests.post(current_app.config['API_CONFIG']['base_url'], json=params)
        return response.json()
    except Exception as e:
        current_app.logger.error(f"Error fetching products: {e}")
        return None

@bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)

    params = {
        'action': 'wanyilian.supplier.spu.querySPUList',
        'app_key': current_app.config['API_CONFIG']['app_key'],
        'data': {"SPU": "", "SKU": ""},
        'format': 'json',
        'language': 'zh_CN',
        'platform': current_app.config['API_CONFIG']['platform'],
        'sign_method': 'md5',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': '1.0'
    }
    sign_string = current_app.config['API_CONFIG']['token']
    for key, value in sorted(params.items()):
        if isinstance(value, dict):
            value = json.dumps(value)
        sign_string += key + str(value)
    sign_string += current_app.config['API_CONFIG']['token']
    
    current_app.logger.debug(f"Sign string: {sign_string}")
    current_app.logger.debug(f"Generated sign: {generate_sign(params)}")
    
    params['sign'] = generate_sign(params)
    
    try:
        response = requests.post(current_app.config['API_CONFIG']['base_url'], json=params)
        current_app.logger.debug(f"API Response: {response.text}")
        return render_template('main/index.html', 
                             products=response.json().get('data', {}).get('SPUList', []),
                             pagination={'page': page, 'total_pages': 1})
    except Exception as e:
        current_app.logger.error(f"Error fetching products: {e}")
        return render_template('main/index.html', 
                             products=[], 
                             error=str(e),
                             pagination={'page': page, 'total_pages': 1})
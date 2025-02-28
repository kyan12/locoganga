import hashlib
import json
from datetime import datetime
import requests
from flask import current_app
import socket
from urllib.parse import urlparse

class WinitAPI:
    """Service class for interacting with the Winit API"""
    
    def __init__(self, base_url, app_key, token, platform='OWNERERP'):
        self.base_url = base_url
        self.app_key = app_key
        self.token = token
        self.platform = platform

    @classmethod
    def from_app(cls, app):
        """Create an instance from Flask app config"""
        return cls(
            base_url=app.config['WINIT_API_URL'],
            app_key=app.config['WINIT_APP_KEY'],
            token=app.config['WINIT_TOKEN']
        )

    def _generate_sign(self, params):
        """Generate API signature matching the API requirements"""
        # Create clean params copy
        param_copy = {k: v for k, v in params.items() if k not in ['sign', 'language']}
        
        # Build signature string starting with token
        sign_string = self.token
        
        # Sort and concatenate parameters
        for key in sorted(param_copy.keys()):
            value = param_copy[key]
            if key == 'data':
                # Ensure consistent JSON serialization
                sign_string += key + json.dumps(value, separators=(',', ':'))
            else:
                sign_string += key + str(value)
                
        # Add token at end
        sign_string += self.token
        
        # Generate MD5 hash and convert to uppercase
        return hashlib.md5(sign_string.encode('utf-8')).hexdigest().upper()

    def _make_request(self, action, data=None, timeout=30):
        """Make a request to the Winit API
        
        Args:
            action: The API action to call
            data: The data to send with the request
            timeout: Request timeout in seconds (default: 30)
            
        Returns:
            The JSON response from the API
            
        Raises:
            ConnectionError: If the connection fails
            Timeout: If the request times out
            HTTPError: If the API returns an error status code
        """
        params = {
            'action': action,
            'app_key': self.app_key,
            'data': data or {},
            'format': 'json',
            'language': 'zh_CN',
            'platform': self.platform,
            'sign_method': 'md5',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'version': '1.0'
        }
        
        params['sign'] = self._generate_sign(params)
        
        try:
            current_app.logger.info(f"Making Winit API request to {self.base_url} for action {action}")
            response = requests.post(self.base_url, json=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            current_app.logger.error(f"Timeout connecting to Winit API for action {action}")
            raise
        except requests.exceptions.ConnectionError as e:
            current_app.logger.error(f"Connection error to Winit API for action {action}: {e}")
            raise
        except requests.exceptions.HTTPError as e:
            current_app.logger.error(f"HTTP error from Winit API for action {action}: {e}")
            raise
        except Exception as e:
            current_app.logger.error(f"Error making Winit API request for action {action}: {e}")
            raise

    def get_product_base_list(self, warehouse_code=None, page_no=1, page_size=50):
        """Get list of products with basic information"""
        data = {
            'pageParams': {
                'pageNo': page_no,
                'pageSize': page_size,
                'totalCount': 0
            }
        }
        
        if warehouse_code:
            data['warehouseCode'] = warehouse_code

        return self._make_request('wanyilian.supplier.spu.getProductBaseList', data)

    def get_product_details(self, spu, sku=None):
        """Get detailed product information including descriptions and images"""
        data = {'SPU': spu}
        if sku:
            data['SKU'] = sku
        return self._make_request('wanyilian.supplier.spu.querySPUList', data)

    def get_warehouses(self):
        """Get list of available warehouses"""
        return self._make_request('wanyilian.platform.queryWarehouse')

    def get_delivery_methods(self, warehouse_code):
        """Get available delivery methods for a warehouse"""
        data = {'warehouseCode': warehouse_code}
        return self._make_request('wanyilian.platform.queryDeliveryWay', data)

    def create_outbound_order(self, order_data):
        """Create an outbound order for shipping"""
        return self._make_request('wanyilian.distributor.order.create', order_data)

    def cancel_order(self, order_numbers):
        """Cancel one or more orders"""
        data = {'orderNums': order_numbers}
        return self._make_request('wanyilian.distributor.order.void', data)

    def confirm_order(self, order_numbers):
        """Confirm one or more orders for shipping"""
        data = {'orderNums': order_numbers}
        return self._make_request('wanyilian.distributor.order.confirm', data)

    def get_order_list(self, filters=None, page_no=1, page_size=100):
        """Get list of orders with optional filters"""
        data = {
            'pageParams': {
                'pageNo': page_no,
                'pageSize': page_size
            }
        }
        if filters:
            data.update(filters)
        return self._make_request('wanyilian.distributor.order.queryOrderList', data)

    def get_order_details(self, order_number):
        """Get detailed information about a specific order"""
        data = {'orderNum': order_number}
        return self._make_request('wanyilian.distributor.order.queryOrder', data)

    def get_categories(self):
        """Get product categories"""
        return self._make_request('wanyilian.supplier.spu.getCategoryList')

    def get_sale_types(self):
        """Get product sale types"""
        return self._make_request('wanyilian.supplier.spu.getSaleTypeList')

    def test_connectivity(self, timeout=5):
        """Test connectivity to the Winit API server
        
        Args:
            timeout: Connection timeout in seconds (default: 5)
            
        Returns:
            dict: A dictionary with connectivity test results
        """
        results = {
            'success': False,
            'url': self.base_url,
            'errors': []
        }
        
        # Parse the URL to get the hostname
        parsed_url = urlparse(self.base_url)
        hostname = parsed_url.netloc
        
        # Test DNS resolution
        try:
            ip_address = socket.gethostbyname(hostname)
            results['ip_address'] = ip_address
            results['dns_resolution'] = True
        except socket.gaierror as e:
            results['dns_resolution'] = False
            results['errors'].append(f"DNS resolution failed: {e}")
            return results
        
        # Test TCP connection
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        
        try:
            port = 443 if parsed_url.scheme == 'https' else 80
            s.connect((hostname, port))
            results['tcp_connection'] = True
        except socket.timeout:
            results['tcp_connection'] = False
            results['errors'].append(f"TCP connection timed out after {timeout} seconds")
        except socket.error as e:
            results['tcp_connection'] = False
            results['errors'].append(f"TCP connection failed: {e}")
        finally:
            s.close()
        
        # Test HTTP connection
        if results.get('tcp_connection', False):
            try:
                response = requests.get(
                    f"{parsed_url.scheme}://{hostname}", 
                    timeout=timeout
                )
                results['http_status'] = response.status_code
                results['http_connection'] = True
            except requests.exceptions.RequestException as e:
                results['http_connection'] = False
                results['errors'].append(f"HTTP connection failed: {e}")
        
        results['success'] = (
            results.get('dns_resolution', False) and 
            results.get('tcp_connection', False) and 
            results.get('http_connection', False)
        )
        
        return results 
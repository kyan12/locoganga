import hashlib
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
import requests
from flask import current_app

class WinitAPI:
    def __init__(self, app_key: str, token: str, platform: str, base_url: str):
        self.app_key = app_key
        self.token = token
        self.platform = platform
        self.base_url = base_url

    def _generate_sign(self, params: Dict) -> str:
        """Generate signature for API request"""
        # Sort parameters by key
        sorted_params = dict(sorted(params.items()))
        
        # Create signature string
        sign_str = self.token
        for key, value in sorted_params.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            sign_str += key + str(value)
        sign_str += self.token

        # Generate MD5 hash
        return hashlib.md5(sign_str.encode()).hexdigest().upper()

    def _make_request(self, action: str, data: Dict = None) -> Dict:
        """Make API request to Winit"""
        if data is None:
            data = {}

        params = {
            'action': action,
            'app_key': self.app_key,
            'platform': 'cavendish',
            'format': 'json',
            'sign_method': 'md5',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'version': '1.0',
            'data': data
        }

        params['sign'] = self._generate_sign(params)
        print(params)

        try:
            response = requests.post(self.base_url, json=params)
            response.raise_for_status()
            result = response.json()
            
            if result.get('code') != '0':
                raise Exception(f"API Error: {result.get('msg')}")
                
            return result.get('data', {})
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")

    def get_product_list(self, warehouse_code: Optional[str] = None, page: int = 1, page_size: int = 200) -> Dict:
        """Get list of products from Winit"""
        data = {
            'isHavingInventory': 'Y',
            'pageParams': {
                'pageNo': page,
                'pageSize': page_size
            }
        }
        if warehouse_code:
            data['warehouseCode'] = warehouse_code

        return self._make_request('wanyilian.supplier.spu.getProductBaseList', data)

    def get_product_detail(self, spu: str) -> Dict:
        """Get detailed product information"""
        data = {'SPU': spu}
        return self._make_request('wanyilian.supplier.spu.querySPUList', data)

    def get_warehouses(self) -> List[Dict]:
        """Get list of warehouses"""
        return self._make_request('wanyilian.platform.queryWarehouse')

    def get_delivery_methods(self, warehouse_code: str) -> List[Dict]:
        """Get delivery methods for a warehouse"""
        data = {'warehouseCode': warehouse_code}
        return self._make_request('wanyilian.platform.queryDeliveryWay', data)

    def create_order(self, order_data: Dict) -> Dict:
        """Create an outbound order"""
        return self._make_request('wanyilian.distributor.order.create', order_data)

    def get_order_detail(self, order_num: str) -> Dict:
        """Get order details"""
        data = {'orderNum': order_num}
        return self._make_request('wanyilian.distributor.order.queryOrder', data)

    def get_order_list(self, params: Dict) -> Dict:
        """Get list of orders"""
        return self._make_request('wanyilian.distributor.order.queryOrderList', params)

    def cancel_order(self, order_nums: List[str]) -> Dict:
        """Cancel an order"""
        data = {'orderNums': order_nums}
        return self._make_request('wanyilian.distributor.order.void', data)

    @classmethod
    def from_app(cls, app):
        """Create WinitAPI instance from Flask app config"""
        return cls(
            app_key=app.config['WINIT_APP_KEY'],
            token=app.config['WINIT_TOKEN'],
            platform='OWNERERP',  # This is fixed as per your config
            base_url=app.config['WINIT_API_URL']
        ) 
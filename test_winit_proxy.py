#!/usr/bin/env python
"""
Script to test the Winit API through a proxy
"""
import os
import sys
import json
import logging
import argparse
import requests
from dotenv import load_dotenv

# Add the current directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('winit_proxy_test')

def main():
    parser = argparse.ArgumentParser(description='Test the Winit API through a proxy')
    parser.add_argument('--timeout', type=int, default=60, help='API request timeout in seconds')
    parser.add_argument('--proxy', type=str, required=True, 
                        help='Proxy URL (e.g., http://user:pass@host:port)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show verbose output')
    args = parser.parse_args()
    
    # Get API credentials from environment variables
    api_url = os.environ.get('WINIT_API_URL', 'https://openapi.wanyilian.com/cedpopenapi/service')
    app_key = os.environ.get('WINIT_APP_KEY')
    token = os.environ.get('WINIT_TOKEN')
    
    if not app_key or not token:
        print("Error: WINIT_APP_KEY and WINIT_TOKEN environment variables must be set")
        sys.exit(1)
    
    # Import the WinitAPI class
    from app.services.winit_api import WinitAPI
    
    # Create a custom session with the proxy
    session = requests.Session()
    session.proxies = {
        'http': args.proxy,
        'https': args.proxy
    }
    
    # Create a WinitAPI instance
    api = WinitAPI(api_url, app_key, token)
    
    print(f"Testing API call to {api_url} through proxy {args.proxy}...")
    print(f"Using timeout of {args.timeout} seconds")
    
    # Prepare data for the API call
    data = {
        'pageParams': {
            'pageNo': 1,
            'pageSize': 10,
            'totalCount': 0
        }
    }
    
    # Prepare the request parameters
    params = {
        'action': 'wanyilian.supplier.spu.getProductBaseList',
        'app_key': app_key,
        'data': data,
        'format': 'json',
        'language': 'zh_CN',
        'platform': 'OWNERERP',
        'sign_method': 'md5',
        'timestamp': api._make_request.__globals__['datetime'].now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': '1.0'
    }
    
    # Generate the signature
    params['sign'] = api._generate_sign(params)
    
    try:
        # Make the API call with the specified timeout using the proxy session
        response = session.post(api_url, json=params, timeout=args.timeout)
        response.raise_for_status()
        result = response.json()
        
        if args.verbose:
            print(json.dumps(result, indent=2))
        
        print("✅ API call successful!")
        print(f"Response contains {len(result.get('data', {}).get('list', []))} items")
        return 0
    except Exception as e:
        print(f"❌ API call failed: {e}")
        
        # Provide troubleshooting advice
        print("\nTroubleshooting suggestions:")
        print("  - Check if the proxy is working correctly")
        print("  - Try a different proxy")
        print("  - Verify your API credentials")
        print("  - Try increasing the timeout value")
        
        return 1

if __name__ == '__main__':
    sys.exit(main()) 
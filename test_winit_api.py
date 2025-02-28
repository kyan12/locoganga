#!/usr/bin/env python
"""
Script to test the Winit API with a longer timeout
"""
import os
import sys
import json
import logging
import argparse
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
logger = logging.getLogger('winit_api_test')

def main():
    parser = argparse.ArgumentParser(description='Test the Winit API with a longer timeout')
    parser.add_argument('--timeout', type=int, default=60, help='API request timeout in seconds')
    parser.add_argument('--action', type=str, default='wanyilian.supplier.spu.getProductBaseList', 
                        help='API action to test')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show verbose output')
    args = parser.parse_args()
    
    # Import Flask and create a test app
    from flask import Flask
    test_app = Flask('test_app')
    
    # Configure the test app
    test_app.config['WINIT_API_URL'] = os.environ.get('WINIT_API_URL', 'https://openapi.wanyilian.com/cedpopenapi/service')
    test_app.config['WINIT_APP_KEY'] = os.environ.get('WINIT_APP_KEY')
    test_app.config['WINIT_TOKEN'] = os.environ.get('WINIT_TOKEN')
    
    # Import the WinitAPI class
    from app.services.winit_api import WinitAPI
    
    # Get API credentials from environment variables
    api_url = os.environ.get('WINIT_API_URL', 'https://openapi.wanyilian.com/cedpopenapi/service')
    app_key = os.environ.get('WINIT_APP_KEY')
    token = os.environ.get('WINIT_TOKEN')
    
    if not app_key or not token:
        print("Error: WINIT_APP_KEY and WINIT_TOKEN environment variables must be set")
        sys.exit(1)
    
    # Create a WinitAPI instance
    api = WinitAPI(api_url, app_key, token)
    
    print(f"Testing API call to {api_url} with action {args.action}...")
    print(f"Using timeout of {args.timeout} seconds")
    
    # Prepare data for the API call
    data = {
        'pageParams': {
            'pageNo': 1,
            'pageSize': 10,
            'totalCount': 0
        }
    }
    
    # Use the Flask app context
    with test_app.app_context():
        try:
            # Make the API call with the specified timeout
            response = api._make_request(args.action, data, timeout=args.timeout)
            
            if args.verbose:
                print(json.dumps(response, indent=2))
            
            print("✅ API call successful!")
            print(f"Response contains {len(response.get('data', {}).get('list', []))} items")
            return 0
        except Exception as e:
            print(f"❌ API call failed: {e}")
            
            # Provide troubleshooting advice
            print("\nTroubleshooting suggestions:")
            print("  - Try increasing the timeout value")
            print("  - Check your network connectivity")
            print("  - Verify your API credentials")
            print("  - Check if the API server is down")
            print("  - Try using a VPN or different network")
            
            return 1

if __name__ == '__main__':
    sys.exit(main()) 
#!/usr/bin/env python
"""
Script to test connectivity to the Winit API server
"""
import os
import sys
import json
import argparse
from dotenv import load_dotenv

# Add the current directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Load environment variables
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description='Test connectivity to the Winit API server')
    parser.add_argument('--timeout', type=int, default=10, help='Connection timeout in seconds')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show verbose output')
    args = parser.parse_args()
    
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
    
    print(f"Testing connectivity to {api_url}...")
    
    # Test connectivity
    results = api.test_connectivity(timeout=args.timeout)
    
    if args.verbose:
        print(json.dumps(results, indent=2))
    
    if results['success']:
        print("✅ Connection successful!")
        return 0
    else:
        print("❌ Connection failed!")
        print("Errors:")
        for error in results['errors']:
            print(f"  - {error}")
        
        # Provide troubleshooting advice
        print("\nTroubleshooting suggestions:")
        
        if not results.get('dns_resolution', False):
            print("  - Check your DNS settings")
            print("  - Verify that the hostname is correct")
        
        if not results.get('tcp_connection', False):
            print("  - Check if a firewall is blocking outbound connections")
            print("  - Try increasing the timeout value")
            print("  - Check if the API server is down")
        
        if not results.get('http_connection', False):
            print("  - Check if the API server is accepting HTTP connections")
            print("  - Verify your TLS/SSL settings")
        
        return 1

if __name__ == '__main__':
    sys.exit(main()) 
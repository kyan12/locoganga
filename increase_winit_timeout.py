#!/usr/bin/env python
"""
Script to modify the application to use a longer timeout for the Winit API
"""
import os
import sys
import argparse
from dotenv import load_dotenv

# Add the current directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Load environment variables
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description='Modify the application to use a longer timeout for the Winit API')
    parser.add_argument('--timeout', type=int, default=120, help='API request timeout in seconds')
    args = parser.parse_args()
    
    # Import the Flask app
    try:
        from app import create_app
        app = create_app()
    except ImportError:
        print("Error: Could not import the Flask app. Make sure you're in the correct directory.")
        sys.exit(1)
    
    # Create a configuration file for the Winit API timeout
    config_path = os.path.join(os.path.dirname(__file__), 'app', 'config')
    os.makedirs(config_path, exist_ok=True)
    
    config_file = os.path.join(config_path, 'winit_config.py')
    
    with open(config_file, 'w') as f:
        f.write(f"""\"\"\"
Configuration for the Winit API
\"\"\"

# Timeout for Winit API requests in seconds
WINIT_API_TIMEOUT = {args.timeout}
""")
    
    print(f"✅ Created configuration file with timeout of {args.timeout} seconds: {config_file}")
    
    # Create a patch for the WinitAPI class
    patch_file = os.path.join(os.path.dirname(__file__), 'app', 'services', 'winit_api_patch.py')
    
    with open(patch_file, 'w') as f:
        f.write("""\"\"\"
Patch for the WinitAPI class to use a longer timeout
\"\"\"
from functools import wraps
import time
import requests
from flask import current_app

def patch_winit_api():
    \"\"\"Patch the WinitAPI class to use a longer timeout\"\"\"
    from app.services.winit_api import WinitAPI
    
    # Store the original _make_request method
    original_make_request = WinitAPI._make_request
    
    @wraps(original_make_request)
    def patched_make_request(self, action, data=None, timeout=None):
        \"\"\"Patched version of _make_request with retry logic\"\"\"
        # Get the timeout from config or use the provided value
        if timeout is None:
            try:
                from app.config.winit_config import WINIT_API_TIMEOUT
                timeout = WINIT_API_TIMEOUT
            except ImportError:
                timeout = 120  # Default to 120 seconds if config not found
        
        # Log the timeout being used
        if hasattr(current_app, 'logger'):
            current_app.logger.info(f"Using timeout of {timeout} seconds for Winit API request")
        
        # Try the request with retries
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                return original_make_request(self, action, data, timeout=timeout)
            except requests.exceptions.ConnectionError as e:
                if hasattr(current_app, 'logger'):
                    current_app.logger.warning(
                        f"Connection error on attempt {attempt + 1}/{max_retries}: {e}"
                    )
                
                # If this is the last attempt, re-raise the exception
                if attempt == max_retries - 1:
                    raise
                
                # Wait before retrying
                time.sleep(retry_delay)
    
    # Replace the original method with the patched one
    WinitAPI._make_request = patched_make_request
    
    return WinitAPI

# Apply the patch when this module is imported
patched_WinitAPI = patch_winit_api()
""")
    
    print(f"✅ Created patch file for the WinitAPI class: {patch_file}")
    
    # Create an initialization file to apply the patch
    init_file = os.path.join(os.path.dirname(__file__), 'app', 'services', '__init__.py')
    
    # Check if the file exists and read its contents
    init_content = ""
    if os.path.exists(init_file):
        with open(init_file, 'r') as f:
            init_content = f.read()
    
    # Add the import for the patch if it's not already there
    if "import winit_api_patch" not in init_content:
        with open(init_file, 'w') as f:
            f.write(init_content)
            if init_content and not init_content.endswith('\n'):
                f.write('\n')
            f.write('\n# Import the patch for the WinitAPI class\ntry:\n    from . import winit_api_patch\nexcept ImportError:\n    pass\n')
    
    print(f"✅ Updated initialization file to apply the patch: {init_file}")
    
    print("\n🎉 Done! The application will now use a longer timeout for Winit API requests.")
    print(f"   The timeout is set to {args.timeout} seconds.")
    print("   The patch also includes retry logic for connection errors.")
    print("\n   To apply these changes, restart your application.")

if __name__ == '__main__':
    main() 
#!/usr/bin/env python
"""
Script to check if the Winit API server is reachable using various methods
"""
import os
import sys
import socket
import subprocess
import platform
import requests
from urllib.parse import urlparse

def check_dns(hostname):
    """Check if the hostname can be resolved"""
    print(f"\n🔍 Checking DNS resolution for {hostname}...")
    try:
        ip_address = socket.gethostbyname(hostname)
        print(f"✅ DNS resolution successful: {hostname} -> {ip_address}")
        return True, ip_address
    except socket.gaierror as e:
        print(f"❌ DNS resolution failed: {e}")
        return False, None

def check_ping(hostname, count=4):
    """Check if the host responds to ping"""
    print(f"\n🔍 Pinging {hostname}...")
    
    # Determine the ping command based on the platform
    if platform.system().lower() == "windows":
        ping_cmd = ["ping", "-n", str(count), hostname]
    else:
        ping_cmd = ["ping", "-c", str(count), hostname]
    
    try:
        result = subprocess.run(ping_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Ping successful")
            return True
        else:
            print(f"❌ Ping failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Ping failed: {e}")
        return False

def check_tcp_connection(hostname, port, timeout=5):
    """Check if a TCP connection can be established"""
    print(f"\n🔍 Testing TCP connection to {hostname}:{port}...")
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    
    try:
        s.connect((hostname, port))
        print(f"✅ TCP connection successful")
        return True
    except socket.timeout:
        print(f"❌ TCP connection timed out after {timeout} seconds")
        return False
    except socket.error as e:
        print(f"❌ TCP connection failed: {e}")
        return False
    finally:
        s.close()

def check_http_connection(url, timeout=5):
    """Check if an HTTP connection can be established"""
    print(f"\n🔍 Testing HTTP connection to {url}...")
    
    try:
        response = requests.get(url, timeout=timeout)
        print(f"✅ HTTP connection successful (status code: {response.status_code})")
        return True, response.status_code
    except requests.exceptions.RequestException as e:
        print(f"❌ HTTP connection failed: {e}")
        return False, None

def check_traceroute(hostname):
    """Run a traceroute to the hostname"""
    print(f"\n🔍 Running traceroute to {hostname}...")
    
    # Determine the traceroute command based on the platform
    if platform.system().lower() == "windows":
        tracert_cmd = ["tracert", "-h", "15", hostname]
    else:
        tracert_cmd = ["traceroute", "-m", "15", hostname]
    
    try:
        result = subprocess.run(tracert_cmd, capture_output=True, text=True)
        print(result.stdout)
        return True
    except Exception as e:
        print(f"❌ Traceroute failed: {e}")
        return False

def main():
    # Get the Winit API URL from environment variables or use the default
    api_url = os.environ.get('WINIT_API_URL', 'https://openapi.wanyilian.com/cedpopenapi/service')
    
    # Parse the URL to get the hostname
    parsed_url = urlparse(api_url)
    hostname = parsed_url.netloc
    
    print(f"Checking connectivity to Winit API server: {hostname}")
    
    # Check DNS resolution
    dns_success, ip_address = check_dns(hostname)
    
    if dns_success:
        # Check ping
        ping_success = check_ping(hostname)
        
        # Check TCP connection
        port = 443 if parsed_url.scheme == 'https' else 80
        tcp_success = check_tcp_connection(hostname, port)
        
        # Check HTTP connection
        http_success, status_code = check_http_connection(f"{parsed_url.scheme}://{hostname}")
        
        # Run traceroute if any of the checks failed
        if not ping_success or not tcp_success or not http_success:
            check_traceroute(hostname)
    
    print("\n📋 Summary:")
    print(f"  DNS Resolution: {'✅' if dns_success else '❌'}")
    if dns_success:
        print(f"  Ping: {'✅' if ping_success else '❌'}")
        print(f"  TCP Connection: {'✅' if tcp_success else '❌'}")
        print(f"  HTTP Connection: {'✅' if http_success else '❌'}")
    
    print("\n💡 Troubleshooting suggestions:")
    if not dns_success:
        print("  - Check your DNS settings")
        print("  - Verify that the hostname is correct")
        print("  - Try using a different DNS server")
    elif not ping_success or not tcp_success:
        print("  - Check if a firewall is blocking outbound connections")
        print("  - Check if the API server is down")
        print("  - Try using a VPN or different network")
    elif not http_success:
        print("  - Check if the API server is accepting HTTP connections")
        print("  - Verify your TLS/SSL settings")
        print("  - Try using a different browser or client")

if __name__ == '__main__':
    main() 
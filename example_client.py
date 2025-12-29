#!/usr/bin/env python3
"""
Example client demonstrating how to use the MCP Odoo server with authentication
"""

import json
import requests
import sys

# Configuration
SERVER_URL = "http://localhost:8000/mcp"
BEARER_TOKEN = "YOUR_TOKEN_HERE"  # Replace with your actual token


def make_authenticated_request(method, params=None):
    """
    Make an authenticated request to the MCP server
    
    Args:
        method: MCP method to call
        params: Parameters for the method
    
    Returns:
        Response from server
    """
    headers = {
        "Authorization": f"Bearer {BEARER_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": 1
    }
    
    response = requests.post(SERVER_URL, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def example_list_tools():
    """Example: List all available tools"""
    print("\n" + "="*60)
    print("Example 1: List Available Tools")
    print("="*60)
    
    try:
        result = make_authenticated_request("tools/list")
        print(f"Available tools: {len(result.get('result', {}).get('tools', []))}")
        for tool in result.get('result', {}).get('tools', []):
            print(f"  - {tool.get('name')}: {tool.get('description', '')[:60]}...")
    except Exception as e:
        print(f"Error: {e}")


def example_list_resources():
    """Example: List all available resources"""
    print("\n" + "="*60)
    print("Example 2: List Available Resources")
    print("="*60)
    
    try:
        result = make_authenticated_request("resources/list")
        print(f"Available resources: {len(result.get('result', {}).get('resources', []))}")
        for resource in result.get('result', {}).get('resources', []):
            print(f"  - {resource.get('uri')}: {resource.get('description', '')[:60]}...")
    except Exception as e:
        print(f"Error: {e}")


def example_execute_tool():
    """Example: Execute a tool (search_employee)"""
    print("\n" + "="*60)
    print("Example 3: Search for Employees")
    print("="*60)
    
    try:
        result = make_authenticated_request("tools/call", {
            "name": "search_employee",
            "arguments": {
                "name": "John",
                "limit": 5
            }
        })
        
        if result.get('result', {}).get('content'):
            content = json.loads(result['result']['content'][0]['text'])
            if content.get('success'):
                print(f"Found employees:")
                for emp in content.get('result', []):
                    print(f"  - {emp.get('name')} (ID: {emp.get('id')})")
            else:
                print(f"Error: {content.get('error')}")
    except Exception as e:
        print(f"Error: {e}")


def example_read_resource():
    """Example: Read a resource (list all models)"""
    print("\n" + "="*60)
    print("Example 4: List Odoo Models")
    print("="*60)
    
    try:
        result = make_authenticated_request("resources/read", {
            "uri": "odoo://models"
        })
        
        if result.get('result', {}).get('contents'):
            content = json.loads(result['result']['contents'][0]['text'])
            models = content.get('model_names', [])
            print(f"Total models: {len(models)}")
            print("First 10 models:")
            for model in models[:10]:
                print(f"  - {model}")
    except Exception as e:
        print(f"Error: {e}")


def example_custom_method():
    """Example: Execute a custom Odoo method"""
    print("\n" + "="*60)
    print("Example 5: Execute Custom Method (search partners)")
    print("="*60)
    
    try:
        result = make_authenticated_request("tools/call", {
            "name": "execute_method",
            "arguments": {
                "model": "res.partner",
                "method": "search_read",
                "args": [
                    [["is_company", "=", True]]  # Domain: only companies
                ],
                "kwargs": {
                    "fields": ["name", "email", "phone"],
                    "limit": 5
                }
            }
        })
        
        if result.get('result', {}).get('content'):
            content = json.loads(result['result']['content'][0]['text'])
            if content.get('success'):
                print(f"Found companies:")
                for partner in content.get('result', []):
                    print(f"  - {partner.get('name')}")
                    print(f"    Email: {partner.get('email', 'N/A')}")
                    print(f"    Phone: {partner.get('phone', 'N/A')}")
            else:
                print(f"Error: {content.get('error')}")
    except Exception as e:
        print(f"Error: {e}")


def main():
    """Run all examples"""
    
    # Check if token is configured
    if BEARER_TOKEN == "YOUR_TOKEN_HERE":
        print("="*60)
        print("ERROR: Please configure your bearer token first!")
        print("="*60)
        print("\nSteps:")
        print("1. Create a client:")
        print("   docker-compose exec mcp-odoo python manage_auth.py create my-client")
        print("\n2. Copy the token from the output")
        print("\n3. Edit this file and replace 'YOUR_TOKEN_HERE' with your token")
        print("\n4. Run this script again")
        return 1
    
    # Check server health
    try:
        response = requests.get("http://localhost:8000/health")
        health = response.json()
        print("="*60)
        print("Server Health Check")
        print("="*60)
        print(f"Status: {health.get('status')}")
        print(f"Authentication: {'Enabled' if health.get('authentication') else 'Disabled'}")
    except Exception as e:
        print(f"Error connecting to server: {e}")
        print("\nMake sure the server is running:")
        print("  docker-compose up -d")
        return 1
    
    # Run examples
    example_list_tools()
    example_list_resources()
    example_execute_tool()
    example_read_resource()
    example_custom_method()
    
    print("\n" + "="*60)
    print("✅ All examples completed!")
    print("="*60)
    print("\nNext steps:")
    print("- Modify these examples for your use case")
    print("- Check AUTHENTICATION.md for more details")
    print("- Read ARCHITECTURE.md to understand the system")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Test script to verify authentication setup
"""

import sys
import os
import tempfile

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from odoo_mcp.auth import AuthDatabase, validate_bearer_token

def test_authentication():
    """Test the complete authentication flow"""
    
    print("=" * 60)
    print("MCP Odoo Authentication System Test")
    print("=" * 60)
    
    # Use a temporary database
    db_path = os.path.join(tempfile.gettempdir(), 'test_auth_system.db')
    
    try:
        # Test 1: Create database and client
        print("\n1. Testing database initialization...")
        auth_db = AuthDatabase(db_path)
        print("   ✓ Database initialized")
        
        # Test 2: Create client
        print("\n2. Testing client creation...")
        client_id, token = auth_db.create_client('test-app', 'Test application')
        print(f"   ✓ Client created (ID: {client_id})")
        print(f"   ✓ Token generated: {token[:20]}...")
        
        # Test 3: Validate token
        print("\n3. Testing token validation...")
        
        # Set AUTH_ENABLED to test the validation function
        os.environ['AUTH_ENABLED'] = 'true'
        os.environ['AUTH_DB_PATH'] = db_path
        
        # Valid token with proper header format
        auth_header = f"Bearer {token}"
        is_valid = validate_bearer_token(auth_header)
        print(f"   ✓ Valid token accepted: {is_valid}")
        assert is_valid, "Valid token should be accepted"
        
        # Invalid token
        is_valid = validate_bearer_token("Bearer invalid-token-123")
        print(f"   ✓ Invalid token rejected: {not is_valid}")
        assert not is_valid, "Invalid token should be rejected"
        
        # Missing header
        is_valid = validate_bearer_token(None)
        print(f"   ✓ Missing header rejected: {not is_valid}")
        assert not is_valid, "Missing header should be rejected"
        
        # Wrong format
        is_valid = validate_bearer_token("Token abc123")
        print(f"   ✓ Wrong format rejected: {not is_valid}")
        assert not is_valid, "Wrong format should be rejected"
        
        # Test 4: Deactivation
        print("\n4. Testing client deactivation...")
        auth_db.deactivate_client('test-app')
        is_valid = validate_bearer_token(auth_header)
        print(f"   ✓ Deactivated client rejected: {not is_valid}")
        assert not is_valid, "Deactivated client should be rejected"
        
        # Test 5: Reactivation
        print("\n5. Testing client reactivation...")
        auth_db.activate_client('test-app')
        is_valid = validate_bearer_token(auth_header)
        print(f"   ✓ Reactivated client accepted: {is_valid}")
        assert is_valid, "Reactivated client should be accepted"
        
        # Test 6: Test with authentication disabled
        print("\n6. Testing with authentication disabled...")
        os.environ['AUTH_ENABLED'] = 'false'
        is_valid = validate_bearer_token(None)
        print(f"   ✓ No auth required when disabled: {is_valid}")
        assert is_valid, "Should accept all when auth disabled"
        
        # Test 7: List clients
        print("\n7. Testing client listing...")
        clients = auth_db.list_clients()
        print(f"   ✓ Found {len(clients)} client(s)")
        assert len(clients) == 1, "Should have one client"
        
        # Test 8: Multiple clients
        print("\n8. Testing multiple clients...")
        _, token2 = auth_db.create_client('test-app-2', 'Second test app')
        clients = auth_db.list_clients()
        print(f"   ✓ Created second client, total: {len(clients)}")
        assert len(clients) == 2, "Should have two clients"
        
        # Test 9: Delete client
        print("\n9. Testing client deletion...")
        auth_db.delete_client('test-app-2')
        clients = auth_db.list_clients()
        print(f"   ✓ Deleted client, remaining: {len(clients)}")
        assert len(clients) == 1, "Should have one client after deletion"
        
        print("\n" + "=" * 60)
        print("✅ All authentication tests passed!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)
        # Reset environment
        os.environ.pop('AUTH_ENABLED', None)
        os.environ.pop('AUTH_DB_PATH', None)


if __name__ == '__main__':
    success = test_authentication()
    sys.exit(0 if success else 1)

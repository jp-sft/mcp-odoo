"""
Odoo MCP Server - MCP Server for Odoo Integration
"""

# Try to import server, but don't fail if dependencies are missing
# This allows the auth module to be used standalone
try:
    from .server import mcp
    __all__ = ["mcp"]
except ImportError:
    # MCP dependencies not available, auth module can still be used
    __all__ = []


#!/usr/bin/env python
"""
HTTP proxy wrapper for MCP Odoo server with bearer token authentication
This wrapper provides an HTTP/SSE interface to the MCP server with authentication
"""

import asyncio
import json
import logging
import os
import sys
from typing import Optional

from aiohttp import web
import aiohttp

from odoo_mcp.auth import validate_bearer_token

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MCPProxyServer:
    """HTTP proxy server that wraps MCP stdio server with authentication"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        self.host = host
        self.port = port
        self.app = web.Application()
        self._setup_routes()
        self.mcp_process: Optional[asyncio.subprocess.Process] = None

    def _setup_routes(self):
        """Setup HTTP routes"""
        self.app.router.add_get("/health", self.health_check)
        self.app.router.add_post("/mcp", self.handle_mcp_request)
        self.app.router.add_get("/", self.index)

    async def index(self, request: web.Request) -> web.Response:
        """Index page with server information"""
        auth_enabled = os.environ.get("AUTH_ENABLED", "false").lower() in ["true", "1", "yes"]
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>MCP Odoo Server</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    background: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                h1 {{ color: #333; }}
                .status {{ 
                    padding: 10px;
                    border-radius: 4px;
                    margin: 20px 0;
                }}
                .enabled {{ background-color: #d4edda; color: #155724; }}
                .disabled {{ background-color: #fff3cd; color: #856404; }}
                code {{
                    background-color: #f4f4f4;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-family: monospace;
                }}
                pre {{
                    background-color: #f4f4f4;
                    padding: 15px;
                    border-radius: 4px;
                    overflow-x: auto;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔒 MCP Odoo Server</h1>
                <div class="status {'enabled' if auth_enabled else 'disabled'}">
                    <strong>Authentication:</strong> {'✓ Enabled' if auth_enabled else '✗ Disabled'}
                </div>
                
                <h2>Endpoints</h2>
                <ul>
                    <li><code>GET /</code> - This page</li>
                    <li><code>GET /health</code> - Health check endpoint</li>
                    <li><code>POST /mcp</code> - MCP protocol endpoint</li>
                </ul>

                <h2>Authentication</h2>
                {'<p>Authentication is required. Include your bearer token in the Authorization header:</p>' if auth_enabled else '<p>Authentication is currently disabled.</p>'}
                
                {'''<pre>Authorization: Bearer &lt;your-token&gt;</pre>
                
                <h3>Managing Clients</h3>
                <p>Use the <code>manage_auth.py</code> script to manage authentication clients:</p>
                <pre>
# Create a new client
python manage_auth.py create my-client -d "Description"

# List all clients
python manage_auth.py list

# Deactivate a client
python manage_auth.py deactivate my-client

# Delete a client
python manage_auth.py delete my-client
                </pre>''' if auth_enabled else ''}
                
                <h2>Using with MCP Client</h2>
                <p>Configure your MCP client to use this HTTP endpoint:</p>
                <pre>
{{
  "mcpServers": {{
    "odoo": {{
      "url": "http://localhost:{self.port}/mcp",
      "headers": {{
        "Authorization": "Bearer &lt;your-token&gt;"
      }}
    }}
  }}
}}
                </pre>
            </div>
        </body>
        </html>
        """
        return web.Response(text=html, content_type="text/html")

    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "authentication": os.environ.get("AUTH_ENABLED", "false").lower() in ["true", "1", "yes"]
        })

    async def handle_mcp_request(self, request: web.Request) -> web.Response:
        """Handle MCP protocol requests with authentication"""
        
        # Check authentication if enabled
        auth_header = request.headers.get("Authorization")
        if not validate_bearer_token(auth_header):
            logger.warning("Unauthorized MCP request attempt")
            return web.json_response(
                {"error": "Unauthorized", "message": "Invalid or missing bearer token"},
                status=401
            )

        try:
            # Read request body
            body = await request.json()
            logger.info(f"Received MCP request: {body.get('method', 'unknown')}")

            # Start MCP process if not running
            if self.mcp_process is None or self.mcp_process.returncode is not None:
                await self._start_mcp_process()

            # Send request to MCP server via stdin
            request_str = json.dumps(body) + "\n"
            self.mcp_process.stdin.write(request_str.encode())
            await self.mcp_process.stdin.drain()

            # Read response from MCP server via stdout
            response_line = await self.mcp_process.stdout.readline()
            if not response_line:
                raise Exception("MCP server closed connection")

            response = json.loads(response_line.decode())
            logger.info(f"MCP response received")

            return web.json_response(response)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in request: {e}")
            return web.json_response(
                {"error": "Invalid JSON", "message": str(e)},
                status=400
            )
        except Exception as e:
            logger.error(f"Error handling MCP request: {e}", exc_info=True)
            return web.json_response(
                {"error": "Internal server error", "message": str(e)},
                status=500
            )

    async def _start_mcp_process(self):
        """Start the MCP server subprocess"""
        logger.info("Starting MCP server process...")
        
        # Start the MCP server as a subprocess
        self.mcp_process = await asyncio.create_subprocess_exec(
            sys.executable,
            "run_server.py",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        logger.info(f"MCP server process started with PID {self.mcp_process.pid}")

    async def start(self):
        """Start the HTTP server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        logger.info(f"MCP Proxy Server started on http://{self.host}:{self.port}")
        
        # Keep the server running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            if self.mcp_process:
                self.mcp_process.terminate()
                await self.mcp_process.wait()

    async def stop(self):
        """Stop the server and cleanup"""
        if self.mcp_process:
            self.mcp_process.terminate()
            await self.mcp_process.wait()


def main():
    """Main entry point"""
    host = os.environ.get("HTTP_HOST", "0.0.0.0")
    port = int(os.environ.get("HTTP_PORT", "8000"))
    
    auth_enabled = os.environ.get("AUTH_ENABLED", "false").lower() in ["true", "1", "yes"]
    logger.info(f"Authentication: {'enabled' if auth_enabled else 'disabled'}")
    
    server = MCPProxyServer(host=host, port=port)
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

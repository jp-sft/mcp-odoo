# MCP Odoo Server - Authentication Guide

## Overview

The MCP Odoo Server now supports bearer token authentication using a SQLite database to manage client credentials. This provides a secure way to control access to your Odoo MCP server.

## Architecture

The authentication system consists of:

1. **SQLite Database**: Stores client credentials with hashed bearer tokens
2. **HTTP Proxy Server**: Wraps the MCP server and validates bearer tokens
3. **Management CLI**: Command-line tool to manage authentication clients

## Configuration

### Environment Variables

- `AUTH_ENABLED`: Enable/disable authentication (default: `false`)
  - Set to `true`, `1`, or `yes` to enable
- `AUTH_DB_PATH`: Path to SQLite database (default: `/app/data/auth.db`)
- `HTTP_HOST`: HTTP server bind address (default: `0.0.0.0`)
- `HTTP_PORT`: HTTP server port (default: `8000`)

### Using Docker Compose

1. Create a `.env` file in the same directory as `compose.yml`:

```bash
# Odoo Configuration
ODOO_URL=https://your-odoo-instance.com
ODOO_DB=your-database-name
ODOO_USERNAME=your-username
ODOO_PASSWORD=your-password

# Enable Authentication
AUTH_ENABLED=true

# Optional: Debug mode
DEBUG=0
```

2. Start the services:

```bash
docker-compose up -d
```

3. Check the logs:

```bash
docker-compose logs -f
```

## Managing Authentication Clients

### Create a New Client

```bash
# Using Docker Compose
docker-compose exec mcp-odoo python manage_auth.py create my-client -d "My MCP Client"

# Output:
# ✓ Client created successfully!
#   Client ID: 1
#   Client Name: my-client
#   Bearer Token: <generated-token>
#
# ⚠️  IMPORTANT: Save this token securely. It will not be shown again!
```

**Important**: Save the bearer token immediately. It cannot be retrieved later.

### List All Clients

```bash
docker-compose exec mcp-odoo python manage_auth.py list

# Output:
# ID    Name                 Active   Created              Last Used            Description
# ------------------------------------------------------------------------------------------------------------------------
# 1     my-client            ✓        2024-01-15 10:30:00  2024-01-15 11:45:00  My MCP Client
# 2     backup-client        ✗        2024-01-14 09:00:00  Never                Backup system
```

### Deactivate a Client

Temporarily disable a client without deleting it:

```bash
docker-compose exec mcp-odoo python manage_auth.py deactivate my-client
```

### Activate a Client

Re-enable a previously deactivated client:

```bash
docker-compose exec mcp-odoo python manage_auth.py activate my-client
```

### Delete a Client

Permanently remove a client:

```bash
docker-compose exec mcp-odoo python manage_auth.py delete my-client

# You will be asked to confirm:
# Are you sure you want to delete client 'my-client'? This cannot be undone. (yes/no):
```

## Using the Authenticated Server

### Health Check

Check if the server is running:

```bash
curl http://localhost:8000/health

# Response:
# {"status": "healthy", "authentication": true}
```

### Making Authenticated Requests

Include the bearer token in the `Authorization` header:

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/list", "params": {}}'
```

### Web Interface

Open http://localhost:8000 in your browser to see the server information page, which includes:
- Authentication status
- Available endpoints
- Client management instructions
- Usage examples

## Client Configuration

### MCP Client Configuration

If your MCP client supports HTTP transport, configure it like this:

```json
{
  "mcpServers": {
    "odoo": {
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer <your-token>"
      }
    }
  }
}
```

### Using with Claude Desktop (via HTTP)

**Note**: Claude Desktop uses stdio transport by default. To use HTTP authentication, you'll need to configure it differently or use a custom transport adapter.

For stdio mode without authentication:

```json
{
  "mcpServers": {
    "odoo": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e", "ODOO_URL",
        "-e", "ODOO_DB",
        "-e", "ODOO_USERNAME",
        "-e", "ODOO_PASSWORD",
        "-e", "AUTH_ENABLED=false",
        "mcp/odoo"
      ],
      "env": {
        "ODOO_URL": "https://your-odoo-instance.com",
        "ODOO_DB": "your-database-name",
        "ODOO_USERNAME": "your-username",
        "ODOO_PASSWORD": "your-password"
      }
    }
  }
}
```

## Security Best Practices

1. **Enable Authentication in Production**: Always enable authentication when exposing the server
2. **Use HTTPS**: In production, use a reverse proxy (nginx, Caddy) with HTTPS
3. **Rotate Tokens**: Regularly create new clients and deactivate old ones
4. **Backup Database**: The authentication database is stored in a Docker volume - back it up regularly
5. **Monitor Access**: Check the `last_used` timestamp to identify inactive clients

## Database Backup and Restore

### Backup

```bash
# Copy the database from the Docker volume
docker-compose exec mcp-odoo cp /app/data/auth.db /app/logs/auth-backup.db
docker cp mcp-odoo-server:/app/logs/auth-backup.db ./auth-backup.db
```

### Restore

```bash
# Copy backup into the container
docker cp ./auth-backup.db mcp-odoo-server:/app/data/auth.db
docker-compose restart
```

## Troubleshooting

### Authentication Fails

1. Check if authentication is enabled:
```bash
curl http://localhost:8000/health
```

2. Verify the token format in the Authorization header:
```
Authorization: Bearer <token>
```

3. Check if the client is active:
```bash
docker-compose exec mcp-odoo python manage_auth.py list
```

### Database Issues

If the database is corrupted or inaccessible:

1. Stop the container:
```bash
docker-compose down
```

2. Remove the database volume (WARNING: This deletes all clients):
```bash
docker volume rm mcp-odoo_auth-data
```

3. Restart and create new clients:
```bash
docker-compose up -d
docker-compose exec mcp-odoo python manage_auth.py create new-client
```

### Server Not Starting

Check the logs:
```bash
docker-compose logs mcp-odoo
```

Common issues:
- Missing environment variables (ODOO_URL, ODOO_DB, etc.)
- Network connectivity to Odoo instance
- Port 8000 already in use

## Running Without Authentication

To run the server without authentication (not recommended for production):

1. Set `AUTH_ENABLED=false` in your `.env` file
2. Restart the container:
```bash
docker-compose restart
```

Requests will no longer require the Authorization header.

## Production Deployment

For production, use a reverse proxy with HTTPS:

### Example Nginx Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name mcp-odoo.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Then update your docker-compose.yml to only bind to localhost:

```yaml
ports:
  - "127.0.0.1:8000:8000"
```

## Additional Resources

- [MCP Protocol Documentation](https://modelcontextprotocol.io/)
- [Odoo XML-RPC API](https://www.odoo.com/documentation/master/developer/reference/external_api.html)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

# Quick Start Guide - MCP Odoo Server with Authentication

This guide will help you get the MCP Odoo Server running with bearer token authentication in under 5 minutes.

## Prerequisites

- Docker and Docker Compose installed
- An Odoo instance with API access
- Your Odoo credentials (URL, database name, username, password)

## Setup Steps

### 1. Clone and Configure

```bash
# Clone the repository (if you haven't already)
git clone https://github.com/jp-sft/mcp-odoo.git
cd mcp-odoo

# Copy the environment template
cp .env.example .env
```

### 2. Edit Configuration

Edit `.env` file with your Odoo instance details:

```bash
# Odoo Connection
ODOO_URL=https://your-odoo-instance.com
ODOO_DB=your-database-name
ODOO_USERNAME=your-username
ODOO_PASSWORD=your-password-or-api-key

# Enable Authentication (set to false if you don't want auth)
AUTH_ENABLED=true
```

### 3. Start the Server

```bash
# Start the server in detached mode
docker-compose up -d

# Check logs to ensure it's running
docker-compose logs -f
```

You should see output indicating the server started successfully.

### 4. Create an Authentication Client

```bash
# Create your first client
docker-compose exec mcp-odoo python manage_auth.py create my-app -d "My Application"
```

**IMPORTANT**: Save the generated bearer token! It will look like:
```
Bearer Token: abc123xyz...
```

You cannot retrieve this token later. If you lose it, you'll need to create a new client.

### 5. Test the Server

```bash
# Health check (no authentication needed)
curl http://localhost:8000/health

# Test authenticated request (replace <TOKEN> with your actual token)
curl -X POST http://localhost:8000/mcp \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

### 6. Access the Web Interface

Open http://localhost:8000 in your browser to see:
- Server status
- Authentication information
- Usage examples
- Management instructions

## Common Operations

### List All Clients

```bash
docker-compose exec mcp-odoo python manage_auth.py list
```

### Create Additional Clients

```bash
docker-compose exec mcp-odoo python manage_auth.py create client-name -d "Description"
```

### Deactivate a Client (Temporary)

```bash
docker-compose exec mcp-odoo python manage_auth.py deactivate client-name
```

### Reactivate a Client

```bash
docker-compose exec mcp-odoo python manage_auth.py activate client-name
```

### Delete a Client (Permanent)

```bash
docker-compose exec mcp-odoo python manage_auth.py delete client-name
```

## Troubleshooting

### Server won't start

Check the logs:
```bash
docker-compose logs mcp-odoo
```

Common issues:
- Missing or incorrect Odoo credentials
- Odoo instance is not accessible
- Port 8000 is already in use (change in docker-compose.yml)

### Authentication fails

1. Ensure `AUTH_ENABLED=true` in your `.env` file
2. Check that the token is included in the `Authorization: Bearer <token>` header
3. Verify the client is active: `docker-compose exec mcp-odoo python manage_auth.py list`
4. Look for the ✓ symbol in the Active column

### Can't connect to Odoo

1. Verify ODOO_URL is correct and accessible
2. Check ODOO_DB, ODOO_USERNAME, and ODOO_PASSWORD are correct
3. Try accessing the Odoo instance directly in a browser
4. Check if your network/firewall allows the connection

## Running Without Authentication

If you want to disable authentication:

1. Edit `.env` and set:
   ```
   AUTH_ENABLED=false
   ```

2. Restart the server:
   ```bash
   docker-compose restart
   ```

Requests will no longer require the Authorization header.

## Using with MCP Clients

### HTTP-based MCP Client

Configure your MCP client to use:
- URL: `http://localhost:8000/mcp`
- Headers: `Authorization: Bearer <your-token>`

### Claude Desktop (stdio mode)

For stdio mode without HTTP:

```json
{
  "mcpServers": {
    "odoo": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
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

## Production Deployment

For production use:

1. **Use HTTPS**: Put a reverse proxy (nginx, Caddy) with SSL in front
2. **Change the port binding**: In `compose.yml`, change to `127.0.0.1:8000:8000`
3. **Enable authentication**: Always set `AUTH_ENABLED=true`
4. **Backup the database**: Regularly backup the `/app/data` volume
5. **Rotate tokens**: Periodically create new clients and deactivate old ones

## Next Steps

- Read [AUTHENTICATION.md](AUTHENTICATION.md) for detailed authentication documentation
- Check [README.md](README.md) for complete API reference
- Review available MCP tools and resources

## Support

- GitHub Issues: https://github.com/jp-sft/mcp-odoo/issues
- Documentation: See README.md and AUTHENTICATION.md

---

**Need help?** Open an issue on GitHub with:
- Your setup (Docker version, OS)
- Log output (`docker-compose logs`)
- What you've tried
- Expected vs actual behavior

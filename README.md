# Odoo MCP Server

An MCP server implementation that integrates with Odoo ERP systems, enabling AI assistants to interact with Odoo data and functionality through the Model Context Protocol.

## 📚 Documentation

- **[Quick Start Guide](QUICKSTART.md)** - Get up and running in 5 minutes
- **[Authentication Guide](AUTHENTICATION.md)** - Complete authentication documentation
- **[Architecture Overview](ARCHITECTURE.md)** - System design and technical details
- **[Example Client](example_client.py)** - Python client demonstrating usage

## Features

* **Comprehensive Odoo Integration**: Full access to Odoo models, records, and methods
* **XML-RPC Communication**: Secure connection to Odoo instances via XML-RPC
* **Bearer Token Authentication**: Secure your MCP server with client database authentication
* **Flexible Configuration**: Support for config files and environment variables
* **Resource Pattern System**: URI-based access to Odoo data structures
* **Error Handling**: Clear error messages for common Odoo API issues
* **Stateless Operations**: Clean request/response cycle for reliable integration
* **Docker Support**: Ready-to-use Docker and Docker Compose configuration

## Tools

* **execute_method**
  * Execute a custom method on an Odoo model
  * Inputs:
    * `model` (string): The model name (e.g., 'res.partner')
    * `method` (string): Method name to execute
    * `args` (optional array): Positional arguments
    * `kwargs` (optional object): Keyword arguments
  * Returns: Dictionary with the method result and success indicator

* **search_employee**
  * Search for employees by name
  * Inputs:
    * `name` (string): The name (or part of the name) to search for
    * `limit` (optional number): The maximum number of results to return (default 20)
  * Returns: Object containing success indicator, list of matching employee names and IDs, and any error message

* **search_holidays**
  * Searches for holidays within a specified date range
  * Inputs:
    * `start_date` (string): Start date in YYYY-MM-DD format
    * `end_date` (string): End date in YYYY-MM-DD format
    * `employee_id` (optional number): Optional employee ID to filter holidays
  * Returns: Object containing success indicator, list of holidays found, and any error message

## Resources

* **odoo://models**
  * Lists all available models in the Odoo system
  * Returns: JSON array of model information

* **odoo://model/{model_name}**
  * Get information about a specific model including fields
  * Example: `odoo://model/res.partner`
  * Returns: JSON object with model metadata and field definitions

* **odoo://record/{model_name}/{record_id}**
  * Get a specific record by ID
  * Example: `odoo://record/res.partner/1`
  * Returns: JSON object with record data

* **odoo://search/{model_name}/{domain}**
  * Search for records that match a domain
  * Example: `odoo://search/res.partner/[["is_company","=",true]]`
  * Returns: JSON array of matching records (limited to 10 by default)

## Configuration

### Odoo Connection Setup

1. Create a configuration file named `odoo_config.json`:

```json
{
  "url": "https://your-odoo-instance.com",
  "db": "your-database-name",
  "username": "your-username",
  "password": "your-password-or-api-key"
}
```

2. Alternatively, use environment variables:
   * `ODOO_URL`: Your Odoo server URL
   * `ODOO_DB`: Database name
   * `ODOO_USERNAME`: Login username
   * `ODOO_PASSWORD`: Password or API key
   * `ODOO_TIMEOUT`: Connection timeout in seconds (default: 30)
   * `ODOO_VERIFY_SSL`: Whether to verify SSL certificates (default: true)
   * `HTTP_PROXY`: Force the ODOO connection to use an HTTP proxy

### Usage with Claude Desktop

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "odoo": {
      "command": "python",
      "args": [
        "-m",
        "odoo_mcp"
      ],
      "env": {
        "ODOO_URL": "https://your-odoo-instance.com",
        "ODOO_DB": "your-database-name",
        "ODOO_USERNAME": "your-username",
        "ODOO_PASSWORD": "your-password-or-api-key"
      }
    }
  }
}
```

### Docker Compose (Recommended)

The easiest way to deploy with authentication support:

1. Copy the environment template:
```bash
cp .env.example .env
```

2. Edit `.env` with your Odoo credentials and enable authentication:
```bash
# .env
ODOO_URL=https://your-odoo-instance.com
ODOO_DB=your-database-name
ODOO_USERNAME=your-username
ODOO_PASSWORD=your-password-or-api-key
AUTH_ENABLED=true
```

3. Start the server:
```bash
docker-compose up -d
```

4. Create an authentication client:
```bash
docker-compose exec mcp-odoo python manage_auth.py create my-client
# Save the generated bearer token!
```

5. Access the server at http://localhost:8000

For detailed authentication setup, see [AUTHENTICATION.md](AUTHENTICATION.md).

### Docker (Standalone)

```json
{
  "mcpServers": {
    "odoo": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "ODOO_URL",
        "-e",
        "ODOO_DB",
        "-e",
        "ODOO_USERNAME",
        "-e",
        "ODOO_PASSWORD",
        "mcp/odoo"
      ],
      "env": {
        "ODOO_URL": "https://your-odoo-instance.com",
        "ODOO_DB": "your-database-name",
        "ODOO_USERNAME": "your-username",
        "ODOO_PASSWORD": "your-password-or-api-key"
      }
    }
  }
}
```

## Installation

### Python Package

```bash
pip install odoo-mcp
```

### Running the Server

```bash
# Using the installed package
odoo-mcp

# Using the MCP development tools
mcp dev odoo_mcp/server.py

# With additional dependencies
mcp dev odoo_mcp/server.py --with pandas --with numpy

# Mount local code for development
mcp dev odoo_mcp/server.py --with-editable .
```

## Build

Docker build:

```bash
docker build -t mcp/odoo:latest -f Dockerfile .
```

## Parameter Formatting Guidelines

When using the MCP tools for Odoo, pay attention to these parameter formatting guidelines:

1. **Domain Parameter**:
   * The following domain formats are supported:
     * List format: `[["field", "operator", value], ...]`
     * Object format: `{"conditions": [{"field": "...", "operator": "...", "value": "..."}]}`
     * JSON string of either format
   * Examples:
     * List format: `[["is_company", "=", true]]`
     * Object format: `{"conditions": [{"field": "date_order", "operator": ">=", "value": "2025-03-01"}]}`
     * Multiple conditions: `[["date_order", ">=", "2025-03-01"], ["date_order", "<=", "2025-03-31"]]`

2. **Fields Parameter**:
   * Should be an array of field names: `["name", "email", "phone"]`
   * The server will try to parse string inputs as JSON

## Example Usage

See [example_client.py](example_client.py) for a complete example of using the authenticated server:

```python
import requests

# Configure authentication
headers = {
    "Authorization": "Bearer YOUR_TOKEN_HERE",
    "Content-Type": "application/json"
}

# List all tools
response = requests.post("http://localhost:8000/mcp", 
    headers=headers,
    json={"jsonrpc": "2.0", "method": "tools/list", "id": 1}
)

# Execute a tool
response = requests.post("http://localhost:8000/mcp",
    headers=headers,
    json={
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "search_employee",
            "arguments": {"name": "John", "limit": 5}
        },
        "id": 1
    }
)
```

Run the example:
```bash
# 1. Get your token
docker-compose exec mcp-odoo python manage_auth.py create my-client

# 2. Edit example_client.py and add your token

# 3. Install requests (if needed)
pip install requests

# 4. Run the example
python example_client.py
```

## License

This MCP server is licensed under the MIT License.

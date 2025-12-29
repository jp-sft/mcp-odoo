# Architecture Overview - MCP Odoo Server with Bearer Authentication

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         MCP Client                               │
│                  (Claude Desktop, Custom App)                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ HTTP Request
                         │ Authorization: Bearer <token>
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    HTTP Proxy Server                             │
│                    (http_server.py)                              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  1. Validate Bearer Token                                  │ │
│  │  2. Check Auth Database                                    │ │
│  │  3. Forward to MCP Server (stdio)                          │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────┬───────────────────────────┬────────────────────────┘
             │                           │
             │                           │ Query
             │                           ▼
             │                  ┌─────────────────────┐
             │                  │   SQLite Database   │
             │                  │   (auth.db)         │
             │                  │                     │
             │                  │  - Client Name      │
             │                  │  - Token Hash       │
             │                  │  - Active Status    │
             │                  │  - Last Used        │
             │                  └─────────────────────┘
             │
             │ stdio (JSON-RPC)
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     MCP Server Core                              │
│                    (run_server.py)                               │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  MCP Protocol Handler                                      │ │
│  │  - Tools (execute_method, search_employee, etc.)           │ │
│  │  - Resources (odoo://models, odoo://model/*, etc.)         │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ XML-RPC
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Odoo ERP System                             │
│                   (your-odoo-instance.com)                       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  XML-RPC API                                               │ │
│  │  - Authentication                                          │ │
│  │  - Model Operations                                        │ │
│  │  - Business Logic                                          │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. HTTP Proxy Server (`http_server.py`)

**Purpose**: Provides HTTP/REST interface with bearer token authentication

**Key Features**:
- Bearer token validation
- Request forwarding to MCP server
- Web interface for server status
- Health check endpoint

**Endpoints**:
- `GET /` - Web interface with documentation
- `GET /health` - Health check (no auth required)
- `POST /mcp` - MCP protocol endpoint (auth required if enabled)

**Authentication Flow**:
```python
1. Extract Authorization header
2. Parse Bearer token
3. Hash token with SHA-256
4. Query SQLite database
5. Check if client is active
6. Update last_used timestamp
7. Allow/Deny request
```

### 2. Authentication Database (`auth.py`)

**Purpose**: Secure storage and validation of client credentials

**Schema**:
```sql
CREATE TABLE clients (
    id INTEGER PRIMARY KEY,
    client_name TEXT UNIQUE NOT NULL,
    token_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    description TEXT
);
```

**Security Features**:
- Tokens hashed with SHA-256 (never stored in plaintext)
- 32-byte random tokens (256-bit security)
- URL-safe token encoding
- Active/Inactive status for temporary suspension
- Audit trail with last_used timestamp

**Key Operations**:
- `create_client()` - Generate new client with secure token
- `validate_token()` - Check if token is valid and active
- `deactivate_client()` - Temporarily disable access
- `activate_client()` - Re-enable access
- `delete_client()` - Permanently remove client

### 3. MCP Server Core (`run_server.py`, `server.py`)

**Purpose**: Implement Model Context Protocol for Odoo integration

**MCP Tools**:
- `execute_method` - Execute any Odoo model method
- `search_employee` - Search for employees by name
- `search_holidays` - Find holidays within date range

**MCP Resources**:
- `odoo://models` - List all available models
- `odoo://model/{name}` - Get model information and fields
- `odoo://record/{model}/{id}` - Get specific record
- `odoo://search/{model}/{domain}` - Search records

**Communication**:
- Input: stdio (standard input/output)
- Output: JSON-RPC responses
- Protocol: MCP (Model Context Protocol)

### 4. Odoo Client (`odoo_client.py`)

**Purpose**: XML-RPC communication with Odoo

**Features**:
- Connection pooling
- Timeout handling
- SSL verification (configurable)
- Redirect following
- Proxy support
- Error handling and retry logic

**Methods**:
- `execute_method()` - Execute any model method
- `search_read()` - Search and read records
- `read_records()` - Read specific records
- `get_models()` - List all models
- `get_model_fields()` - Get field definitions

### 5. Management CLI (`manage_auth.py`)

**Purpose**: Command-line tool for client management

**Commands**:
```bash
# Create client
python manage_auth.py create <name> [-d description]

# List all clients
python manage_auth.py list

# Deactivate client (temporary)
python manage_auth.py deactivate <name>

# Activate client
python manage_auth.py activate <name>

# Delete client (permanent)
python manage_auth.py delete <name>
```

## Data Flow

### Authenticated Request Flow

```
1. Client sends HTTP request with Bearer token
   ↓
2. HTTP Proxy validates token against database
   ↓
3. If valid, forward to MCP Server via stdio
   ↓
4. MCP Server processes request
   ↓
5. MCP Server calls Odoo via XML-RPC
   ↓
6. Odoo processes and returns data
   ↓
7. MCP Server formats response
   ↓
8. HTTP Proxy returns response to client
```

### Token Creation Flow

```
1. Admin runs manage_auth.py create
   ↓
2. System generates 32-byte random token
   ↓
3. Token is hashed with SHA-256
   ↓
4. Hash stored in database
   ↓
5. Plain token returned to admin (only time it's shown)
   ↓
6. Admin configures client with token
```

### Token Validation Flow

```
1. Extract Authorization header
   ↓
2. Parse "Bearer <token>"
   ↓
3. Hash token with SHA-256
   ↓
4. Query database for matching hash
   ↓
5. Check is_active = 1
   ↓
6. Update last_used timestamp
   ↓
7. Return valid/invalid
```

## Deployment Modes

### Mode 1: HTTP with Authentication (Recommended)

```yaml
# docker-compose.yml
services:
  mcp-odoo:
    command: ["python", "http_server.py"]
    environment:
      AUTH_ENABLED: "true"
    ports:
      - "8000:8000"
```

**Use Case**: Production deployments, multiple clients, web access

**Pros**:
- Bearer token security
- Client management
- Web interface
- Health monitoring
- Easy to integrate

**Cons**:
- Extra HTTP layer
- Slightly more complex

### Mode 2: Direct MCP (stdio)

```yaml
# docker-compose.yml
services:
  mcp-odoo:
    command: ["python", "run_server.py"]
    environment:
      AUTH_ENABLED: "false"
```

**Use Case**: Single client, Claude Desktop, local development

**Pros**:
- Direct MCP protocol
- No HTTP overhead
- Simple setup

**Cons**:
- No authentication
- Single client only
- No web interface

### Mode 3: HTTP without Authentication

```yaml
# docker-compose.yml
services:
  mcp-odoo:
    command: ["python", "http_server.py"]
    environment:
      AUTH_ENABLED: "false"
    ports:
      - "127.0.0.1:8000:8000"  # Localhost only
```

**Use Case**: Development, testing, trusted networks

**Pros**:
- HTTP interface
- No token management
- Easy testing

**Cons**:
- No security
- Should only bind to localhost

## Security Considerations

### Token Security

1. **Generation**: 32-byte cryptographically secure random tokens
2. **Storage**: SHA-256 hashed, never stored in plaintext
3. **Transmission**: HTTPS recommended in production
4. **Lifetime**: No expiration, but can be deactivated/deleted
5. **Scope**: Full access (no per-token permissions yet)

### Best Practices

1. **Use HTTPS**: Deploy behind reverse proxy with SSL
2. **Rotate Tokens**: Periodically create new clients, delete old
3. **Monitor Access**: Check last_used timestamps
4. **Backup Database**: Regular backups of auth.db
5. **Bind to Localhost**: Use `127.0.0.1:8000:8000` if proxied
6. **Enable Authentication**: Always use `AUTH_ENABLED=true` in production

### Network Security

```
Internet → [Firewall] → [Reverse Proxy (HTTPS)] → [MCP Server (HTTP)]
                         (nginx/Caddy)              (localhost:8000)
```

**Recommended nginx configuration**:
```nginx
server {
    listen 443 ssl http2;
    server_name mcp.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Scalability

### Current Limitations

- SQLite database (single file)
- Single process HTTP server
- In-memory token validation

### Scaling Considerations

For high-traffic deployments:

1. **Database**: Migrate to PostgreSQL/MySQL
2. **Load Balancing**: Multiple instances behind load balancer
3. **Caching**: Redis for token validation
4. **Rate Limiting**: Add per-client rate limits
5. **Monitoring**: Prometheus metrics, logging

### Example High-Availability Setup

```
                    ┌──────────────┐
                    │Load Balancer │
                    └──────┬───────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
      ┌────▼────┐     ┌────▼────┐     ┌───▼─────┐
      │ Instance│     │ Instance│     │ Instance│
      │    1    │     │    2    │     │    3    │
      └────┬────┘     └────┬────┘     └────┬────┘
           │               │               │
           └───────────────┼───────────────┘
                           │
                    ┌──────▼───────┐
                    │  PostgreSQL  │
                    │   (auth.db)  │
                    └──────────────┘
```

## Troubleshooting

### Common Issues

1. **Authentication fails**: Check client is active, token is correct
2. **Database locked**: SQLite doesn't support high concurrency
3. **Token not found**: Ensure AUTH_DB_PATH is correct
4. **Import errors**: Check Python path includes src/

### Debug Mode

Enable debug logging:
```bash
DEBUG=1 docker-compose up
```

### Database Inspection

```bash
# Connect to database
sqlite3 /path/to/auth.db

# List all clients
SELECT * FROM clients;

# Check specific client
SELECT * FROM clients WHERE client_name = 'my-client';
```

## Future Enhancements

Potential improvements:

1. **Token Expiration**: Add expiration dates to tokens
2. **Scoped Permissions**: Per-client access control
3. **Rate Limiting**: Prevent abuse
4. **Audit Logging**: Detailed request logging
5. **Web UI**: Browser-based client management
6. **API Keys**: Alternative to bearer tokens
7. **OAuth2**: Standard OAuth2 flow
8. **Multi-tenancy**: Separate Odoo instances per client

## References

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Odoo XML-RPC API](https://www.odoo.com/documentation/master/developer/reference/external_api.html)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    procps \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy source code
COPY . /app/

# Create logs and data directories
RUN mkdir -p /app/logs && chmod 777 /app/logs && \
    mkdir -p /app/data && chmod 777 /app/data

# Install Python dependencies and the package
RUN pip install --no-cache-dir fastmcp aiohttp && \
    pip install --no-cache-dir -e .

# Set environment variables (can be overridden at runtime)
ENV ODOO_URL=""
ENV ODOO_DB=""
ENV ODOO_USERNAME=""
ENV ODOO_PASSWORD=""
ENV ODOO_TIMEOUT="30"
ENV ODOO_VERIFY_SSL="1"
ENV DEBUG="0"

# Authentication environment variables
ENV AUTH_ENABLED="false"
ENV AUTH_DB_PATH="/app/data/auth.db"

# HTTP Server environment variables
ENV HTTP_HOST="0.0.0.0"
ENV HTTP_PORT="8000"

# Make scripts executable
RUN chmod +x run_server.py http_server.py manage_auth.py

# Set stdout/stderr to unbuffered mode
ENV PYTHONUNBUFFERED=1

# Run the HTTP server for Docker (stdio doesn't work in non-interactive containers)
ENTRYPOINT ["python", "http_server.py"] 
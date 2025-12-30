"""
Authentication module for MCP Odoo server
Provides bearer token authentication with PostgreSQL database support
"""

import hashlib
import os
import secrets
from datetime import datetime
from typing import Optional, Tuple

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


class AuthDatabase:
    """Manages client credentials in PostgreSQL database"""

    def __init__(self, db_config: dict = None):
        """
        Initialize authentication database

        Args:
            db_config: Database configuration dict. If None, uses environment variables.
                      For PostgreSQL: {host, port, dbname, user, password}
        """
        if db_config is None:
            db_config = {
                'host': os.environ.get('AUTH_DB_HOST', 'localhost'),
                'port': os.environ.get('AUTH_DB_PORT', '5432'),
                'dbname': os.environ.get('AUTH_DB_NAME', 'mcp_auth'),
                'user': os.environ.get('AUTH_DB_USER', 'mcp_user'),
                'password': os.environ.get('AUTH_DB_PASSWORD', 'mcp_password'),
            }

        if not POSTGRES_AVAILABLE:
            raise ImportError("psycopg2 is required for PostgreSQL support")

        self.db_config = db_config
        self._init_database()

    def _get_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)

    def _init_database(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS clients (
                        id SERIAL PRIMARY KEY,
                        client_name VARCHAR(255) NOT NULL UNIQUE,
                        token_hash VARCHAR(64) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_used TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE,
                        description TEXT
                    )
                """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_token_hash ON clients(token_hash)
                """
                )
            conn.commit()

    @staticmethod
    def _hash_token(token: str) -> str:
        """
        Hash a bearer token using SHA-256

        Args:
            token: Bearer token to hash

        Returns:
            Hexadecimal hash of the token
        """
        return hashlib.sha256(token.encode()).hexdigest()

    def create_client(
        self, client_name: str, description: str = None
    ) -> Tuple[int, str]:
        """
        Create a new client with a generated bearer token

        Args:
            client_name: Unique name for the client
            description: Optional description of the client

        Returns:
            Tuple of (client_id, bearer_token)

        Raises:
            ValueError: If client_name already exists
        """
        # Generate a secure random token (32 bytes = 64 hex characters)
        token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(token)

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO clients (client_name, token_hash, description)
                        VALUES (%s, %s, %s)
                        RETURNING id
                    """,
                        (client_name, token_hash, description),
                    )
                    client_id = cursor.fetchone()[0]
                conn.commit()

            return client_id, token

        except psycopg2.IntegrityError:
            raise ValueError(f"Client '{client_name}' already exists")

    def validate_token(self, token: str) -> bool:
        """
        Validate a bearer token

        Args:
            token: Bearer token to validate

        Returns:
            True if token is valid and active, False otherwise
        """
        token_hash = self._hash_token(token)

        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id FROM clients
                    WHERE token_hash = %s AND is_active = TRUE
                """,
                    (token_hash,),
                )
                result = cursor.fetchone()

                if result:
                    # Update last_used timestamp
                    cursor.execute(
                        """
                        UPDATE clients
                        SET last_used = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """,
                        (result[0],),
                    )
                    conn.commit()
                    return True

        return False

    def list_clients(self):
        """
        List all clients

        Returns:
            List of client dictionaries
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT id, client_name, created_at, last_used, is_active, description
                    FROM clients
                    ORDER BY created_at DESC
                """
                )
                return [dict(row) for row in cursor.fetchall()]

    def deactivate_client(self, client_name: str) -> bool:
        """
        Deactivate a client

        Args:
            client_name: Name of the client to deactivate

        Returns:
            True if client was deactivated, False if not found
        """
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE clients
                    SET is_active = FALSE
                    WHERE client_name = %s
                """,
                    (client_name,),
                )
                conn.commit()
                return cursor.rowcount > 0

    def activate_client(self, client_name: str) -> bool:
        """
        Activate a client

        Args:
            client_name: Name of the client to activate

        Returns:
            True if client was activated, False if not found
        """
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE clients
                    SET is_active = TRUE
                    WHERE client_name = %s
                """,
                    (client_name,),
                )
                conn.commit()
                return cursor.rowcount > 0

    def delete_client(self, client_name: str) -> bool:
        """
        Delete a client permanently

        Args:
            client_name: Name of the client to delete

        Returns:
            True if client was deleted, False if not found
        """
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM clients
                    WHERE client_name = %s
                """,
                    (client_name,),
                )
                conn.commit()
                return cursor.rowcount > 0


def get_auth_database() -> Optional[AuthDatabase]:
    """
    Get authentication database instance if authentication is enabled

    Returns:
        AuthDatabase instance if AUTH_ENABLED is true, None otherwise
    """
    auth_enabled = os.environ.get("AUTH_ENABLED", "false").lower() in [
        "true",
        "1",
        "yes",
    ]

    if not auth_enabled:
        return None

    return AuthDatabase()


def validate_bearer_token(authorization_header: Optional[str]) -> bool:
    """
    Validate bearer token from Authorization header

    Args:
        authorization_header: Value of Authorization header (e.g., "Bearer <token>")

    Returns:
        True if token is valid, False otherwise
    """
    auth_db = get_auth_database()

    # If authentication is disabled, allow all requests
    if auth_db is None:
        return True

    # Check if Authorization header is provided
    if not authorization_header:
        return False

    # Parse Bearer token
    parts = authorization_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return False

    token = parts[1]
    return auth_db.validate_token(token)

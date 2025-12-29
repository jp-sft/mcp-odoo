"""
Authentication module for MCP Odoo server
Provides bearer token authentication with client database support
"""

import hashlib
import os
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


class AuthDatabase:
    """Manages client credentials in SQLite database"""

    def __init__(self, db_path: str = None):
        """
        Initialize authentication database

        Args:
            db_path: Path to SQLite database file. If None, uses default path.
        """
        if db_path is None:
            db_path = os.environ.get(
                "AUTH_DB_PATH", "/app/data/auth.db"
            )

        # Create directory if it doesn't exist
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_name TEXT NOT NULL UNIQUE,
                    token_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
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
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO clients (client_name, token_hash, description)
                    VALUES (?, ?, ?)
                """,
                    (client_name, token_hash, description),
                )
                conn.commit()
                client_id = cursor.lastrowid

            return client_id, token

        except sqlite3.IntegrityError:
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

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id FROM clients
                WHERE token_hash = ? AND is_active = 1
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
                    WHERE id = ?
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
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
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
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE clients
                SET is_active = 0
                WHERE client_name = ?
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
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE clients
                SET is_active = 1
                WHERE client_name = ?
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
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM clients
                WHERE client_name = ?
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

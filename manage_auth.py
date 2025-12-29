#!/usr/bin/env python
"""
Command-line tool to manage authentication clients
"""

import argparse
import sys
from pathlib import Path

# Import auth module directly without loading the full package
# This avoids loading server.py and its MCP dependencies
import importlib.util
spec = importlib.util.spec_from_file_location(
    "auth", 
    Path(__file__).parent / "src" / "odoo_mcp" / "auth.py"
)
auth_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auth_module)
AuthDatabase = auth_module.AuthDatabase


def main():
    """Main entry point for auth management CLI"""
    parser = argparse.ArgumentParser(
        description="Manage MCP Odoo server authentication clients"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Create client command
    create_parser = subparsers.add_parser("create", help="Create a new client")
    create_parser.add_argument("client_name", help="Unique name for the client")
    create_parser.add_argument(
        "-d", "--description", help="Description of the client", default=None
    )

    # List clients command
    subparsers.add_parser("list", help="List all clients")

    # Deactivate client command
    deactivate_parser = subparsers.add_parser("deactivate", help="Deactivate a client")
    deactivate_parser.add_argument("client_name", help="Name of the client")

    # Activate client command
    activate_parser = subparsers.add_parser("activate", help="Activate a client")
    activate_parser.add_argument("client_name", help="Name of the client")

    # Delete client command
    delete_parser = subparsers.add_parser("delete", help="Delete a client permanently")
    delete_parser.add_argument("client_name", help="Name of the client")

    # Database path argument (optional, for all commands)
    parser.add_argument(
        "--db-path",
        help="Path to authentication database (default: /app/data/auth.db)",
        default=None,
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Initialize database
    auth_db = AuthDatabase(db_path=args.db_path)

    if args.command == "create":
        try:
            client_id, token = auth_db.create_client(
                args.client_name, args.description
            )
            print(f"✓ Client created successfully!")
            print(f"  Client ID: {client_id}")
            print(f"  Client Name: {args.client_name}")
            print(f"  Bearer Token: {token}")
            print()
            print("⚠️  IMPORTANT: Save this token securely. It will not be shown again!")
            print()
            print("To use this token, include it in the Authorization header:")
            print(f'  Authorization: Bearer {token}')
            return 0
        except ValueError as e:
            print(f"✗ Error: {e}")
            return 1

    elif args.command == "list":
        clients = auth_db.list_clients()
        if not clients:
            print("No clients found.")
            return 0

        print(f"{'ID':<5} {'Name':<20} {'Active':<8} {'Created':<20} {'Last Used':<20} {'Description':<30}")
        print("-" * 120)
        for client in clients:
            active = "✓" if client["is_active"] else "✗"
            last_used = client["last_used"] or "Never"
            description = client["description"] or ""
            print(
                f"{client['id']:<5} {client['client_name']:<20} {active:<8} "
                f"{client['created_at']:<20} {last_used:<20} {description:<30}"
            )
        return 0

    elif args.command == "deactivate":
        if auth_db.deactivate_client(args.client_name):
            print(f"✓ Client '{args.client_name}' deactivated successfully")
            return 0
        else:
            print(f"✗ Client '{args.client_name}' not found")
            return 1

    elif args.command == "activate":
        if auth_db.activate_client(args.client_name):
            print(f"✓ Client '{args.client_name}' activated successfully")
            return 0
        else:
            print(f"✗ Client '{args.client_name}' not found")
            return 1

    elif args.command == "delete":
        confirm = input(
            f"Are you sure you want to delete client '{args.client_name}'? This cannot be undone. (yes/no): "
        )
        if confirm.lower() == "yes":
            if auth_db.delete_client(args.client_name):
                print(f"✓ Client '{args.client_name}' deleted successfully")
                return 0
            else:
                print(f"✗ Client '{args.client_name}' not found")
                return 1
        else:
            print("Deletion cancelled")
            return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())

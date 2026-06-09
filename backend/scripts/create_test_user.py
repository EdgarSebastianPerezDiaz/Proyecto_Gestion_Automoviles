#!/usr/bin/env python3
"""
Create a test user in the development database.

Usage:
  python create_test_user.py --email user@example.com --password Secret123! --full-name "Frontend Tester" [--role operator]

This script loads .env (development), connects to MongoDB, and calls AuthService.register.
"""

import argparse
from dotenv import load_dotenv
from src.infrastructure.database import MongoDBConnection
from src.services.auth_service import AuthService, UserAlreadyExistsError, AuthError
import json


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Create test user for frontend development")
    parser.add_argument('--email', required=True, help='User email')
    parser.add_argument('--password', required=True, help='User password (min 8 chars)')
    parser.add_argument('--full-name', required=True, help='Full name for the user')
    parser.add_argument('--role', default='operator', choices=['operator', 'admin'], help='User role')

    args = parser.parse_args()

    conn = MongoDBConnection.get_instance()
    try:
        conn.connect()
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        return

    try:
        svc = AuthService(conn)
        user = svc.register(email=args.email, password=args.password, full_name=args.full_name, role=args.role)
        print("User created successfully:")
        print(json.dumps(user, default=str, indent=2))
    except UserAlreadyExistsError:
        print("User already exists with that email.")
    except AuthError as e:
        print(f"Auth error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Obtener token de acceso usando AuthService.login_with_refresh

Usage:
  python get_token.py --email admin@test.local --password Admin1234!
"""
import argparse
import json
from dotenv import load_dotenv
from src.infrastructure.database import MongoDBConnection
from src.services.auth_service import AuthService, AuthError, InvalidCredentialsError


def main():
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument('--email', required=True)
    parser.add_argument('--password', required=True)
    args = parser.parse_args()

    conn = MongoDBConnection.get_instance()
    try:
        conn.connect()
    except Exception as e:
        print(f"DB connect error: {e}")
        return

    try:
        svc = AuthService(conn)
        res = svc.login_with_refresh(email=args.email, password=args.password)
        print(json.dumps(res, default=str, indent=2))
    except InvalidCredentialsError:
        print("Invalid credentials")
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

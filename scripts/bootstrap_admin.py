#!/usr/bin/env python
"""
One-time administrator bootstrap script.
Usage:
    $env:ADMIN_USERNAME="admin"
    $env:ADMIN_PASSWORD="supersecurepassword"
    python scripts/bootstrap_admin.py
"""
import os
import sys
from pathlib import Path
from sqlalchemy import inspect

# Add project root to sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.database import SessionLocal, engine, now_iso
from backend.models import Base, User
from backend.auth import get_password_hash

def main():
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")
    full_name = os.getenv("ADMIN_FULL_NAME", "System Administrator")

    if not username or not password:
        print("ERROR: Both ADMIN_USERNAME and ADMIN_PASSWORD environment variables must be set.", file=sys.stderr)
        print("Example (PowerShell):", file=sys.stderr)
        print('  $env:ADMIN_USERNAME="admin"', file=sys.stderr)
        print('  $env:ADMIN_PASSWORD="securepassword"', file=sys.stderr)
        sys.exit(1)

    if not inspect(engine).has_table("users"):
        print("ERROR: Database schema has not been initialized.", file=sys.stderr)
        print("Run this command first:", file=sys.stderr)
        print("  python -m alembic upgrade head", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        # Check if a platform administrator already exists to prevent accidental overwrites
        existing_admin = db.query(User).filter(User.role == "PLATFORM_ADMIN").first()
        if existing_admin:
            print(f"ERROR: An administrator user '{existing_admin.username}' already exists. Bootstrap aborted.", file=sys.stderr)
            sys.exit(1)

        # Check if the username is taken
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"ERROR: Username '{username}' is already taken.", file=sys.stderr)
            sys.exit(1)

        # Create the admin user
        admin_user = User(
            username=username,
            password_hash=get_password_hash(password),
            full_name=full_name,
            role="PLATFORM_ADMIN",
            organization_id=None,
            is_active=1,
            created_at=now_iso()
        )
        db.add(admin_user)
        db.commit()
        print(f"SUCCESS: Created administrator user '{username}'.")
    except Exception as e:
        db.rollback()
        print(f"ERROR: Failed to bootstrap administrator user: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()

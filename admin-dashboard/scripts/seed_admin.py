"""
seed_admin.py
-------------
Promote an existing user to role='admin' (or demote with --demote).

Usage:
    python admin-dashboard/scripts/seed_admin.py --email user@example.com
    python admin-dashboard/scripts/seed_admin.py --email user@example.com --demote
    python admin-dashboard/scripts/seed_admin.py --list

The user must already exist (sign up first via the normal flow).
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Make `src` importable when run from repo root or anywhere
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from src.database import async_session_factory  # noqa: E402
from src.models.user import User  # noqa: E402


async def list_admins() -> None:
    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.role == "admin"))
        admins = result.scalars().all()
        if not admins:
            print("No admin users found.")
            return
        print(f"Admins ({len(admins)}):")
        for u in admins:
            print(f"  - {u.email}  ({u.full_name})")


async def set_role(email: str, role: str) -> int:
    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            print(f"ERROR: user with email '{email}' not found.", file=sys.stderr)
            return 1
        prev = user.role
        user.role = role
        await db.commit()
        print(f"OK: {email}  role: {prev} -> {role}")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote/demote a user to admin role.")
    parser.add_argument("--email", help="Email of the user to update")
    parser.add_argument("--demote", action="store_true", help="Demote admin -> user")
    parser.add_argument("--list", action="store_true", help="List current admins")
    args = parser.parse_args()

    if args.list:
        asyncio.run(list_admins())
        return 0

    if not args.email:
        parser.error("--email is required (or use --list)")

    role = "user" if args.demote else "admin"
    return asyncio.run(set_role(args.email, role))


if __name__ == "__main__":
    raise SystemExit(main())

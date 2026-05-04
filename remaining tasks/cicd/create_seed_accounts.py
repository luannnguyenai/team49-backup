from __future__ import annotations

import asyncio
import csv
from pathlib import Path

from sqlalchemy import select

from src.database import async_session
from src.models.user import User
from src.services.auth_service import hash_password


OUTPUT_CSV = Path("remaining tasks/cicd/admin_test_accounts.csv")
SHARED_PASSWORD = "AdminTest123!"

ACCOUNTS = [
    {
        "email": "admin1@vinuni.edu.vn",
        "full_name": "admin1",
        "role": "admin",
        "is_onboarded": True,
        "account_type": "admin",
    },
    {
        "email": "admin2@vinuni.edu.vn",
        "full_name": "admin2",
        "role": "admin",
        "is_onboarded": True,
        "account_type": "admin",
    },
    {
        "email": "admin3@vinuni.edu.vn",
        "full_name": "admin3",
        "role": "admin",
        "is_onboarded": True,
        "account_type": "admin",
    },
    {
        "email": "demo1@vinuni.edu.vn",
        "full_name": "demo1",
        "role": "user",
        "is_onboarded": True,
        "account_type": "demo",
    },
    {
        "email": "demo2@vinuni.edu.vn",
        "full_name": "demo2",
        "role": "user",
        "is_onboarded": True,
        "account_type": "demo",
    },
]


async def upsert_accounts() -> list[dict[str, str]]:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.email.in_([row["email"] for row in ACCOUNTS]))
        )
        existing_by_email = {user.email.lower(): user for user in result.scalars().all()}

        for row in ACCOUNTS:
            user = existing_by_email.get(row["email"].lower())
            if user is None:
                user = User(
                    email=row["email"],
                    full_name=row["full_name"],
                    hashed_password=hash_password(SHARED_PASSWORD),
                    role=row["role"],
                    is_onboarded=row["is_onboarded"],
                )
                session.add(user)
            else:
                user.full_name = row["full_name"]
                user.hashed_password = hash_password(SHARED_PASSWORD)
                user.role = row["role"]
                user.is_onboarded = row["is_onboarded"]

        await session.commit()

    export_rows: list[dict[str, str]] = []
    for row in ACCOUNTS:
        export_rows.append(
            {
                "account_type": row["account_type"],
                "email": row["email"],
                "full_name": row["full_name"],
                "role": row["role"],
                "password": SHARED_PASSWORD,
                "admin_dashboard_access": "yes" if row["role"] == "admin" else "no",
            }
        )
    return export_rows


def write_csv(rows: list[dict[str, str]]) -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "account_type",
                "email",
                "full_name",
                "role",
                "password",
                "admin_dashboard_access",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = asyncio.run(upsert_accounts())
    write_csv(rows)
    print(f"Wrote {len(rows)} accounts to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()

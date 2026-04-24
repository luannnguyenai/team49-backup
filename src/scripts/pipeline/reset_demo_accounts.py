"""Reset only the 9 login-ready demo accounts."""

from __future__ import annotations

import asyncio
import json

from src.scripts.pipeline.generate_synthetic_demo_users import _json_safe, generate_from_db


def main() -> None:
    result = asyncio.run(generate_from_db(dataset="demo", import_db=True))
    print(json.dumps(_json_safe(result), ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()


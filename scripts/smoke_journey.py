"""End-to-end dialogue smoke: first text -> pick -> amount -> quote -> yes. No network."""
import asyncio
import os
import sys

sys.path.insert(0, ".")

from app.agent import reply
from app.db import init_db

DB = "/tmp/pool_smoke.db"


async def main() -> None:
    if os.path.exists(DB):
        os.remove(DB)
    init_db(DB)
    phone = "+10000000001"
    script = ["hey", "pelosi one", "twenty bucks", "YES", "how's my portfolio?", "cash out"]
    for u in script:
        print(f"YOU: {u}")
        for m in await reply(DB, phone, u):
            print(f"POOL: {m}")
        print()


asyncio.run(main())

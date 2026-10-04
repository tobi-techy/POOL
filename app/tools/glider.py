"""Glider B2B client. Tonight: whoami only. Strategy/enroll/rebalance land Wednesday."""
import httpx

from app.config import settings


def headers() -> dict:
    return {"x-api-key": settings.glider_api_key}


async def whoami() -> dict:
    async with httpx.AsyncClient(timeout=20.0) as c:
        r = await c.get(f"{settings.glider_base_url}/whoami", headers=headers())
        r.raise_for_status()
        return r.json()

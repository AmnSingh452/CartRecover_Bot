import asyncpg
from fastapi import HTTPException

async def get_db_pool(request=None):
    # Use request.app.state.db_pool if available, else fallback to global app
    if request is not None:
        return request.app.state.db_pool
    try:
        from main import app
        return app.state.db_pool
    except ImportError:
        raise RuntimeError("Could not get db_pool. Make sure app is initialized.")

async def get_shop_token(pool, shop_domain):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT access_token FROM shops WHERE shop_domain = $1",
            shop_domain
        )
        if not row:
            raise HTTPException(status_code=404, detail="Shop not found")
        return row["access_token"] 
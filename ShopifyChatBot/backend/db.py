import asyncpg
from fastapi import HTTPException

async def get_db_pool():
    # Always use as a FastAPI dependency
    from main import app
    return app.state.db_pool

async def get_shop_token(pool, shop_domain):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT access_token FROM shops WHERE shop_domain = $1",
            shop_domain
        )
        if not row:
            raise HTTPException(status_code=404, detail="Shop not found")
        return row["access_token"] 
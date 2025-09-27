import os
import asyncpg
from fastapi import HTTPException

async def get_db_pool():
    return await asyncpg.create_pool(os.getenv("DATABASE_URL"))

async def get_shop_token(pool, shop_domain):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT "accessToken" FROM "Session" WHERE "shop" = $1',
            shop_domain
        )
        if not row:
            raise HTTPException(status_code=404, detail="Shop not found")
        return row["accessToken"]

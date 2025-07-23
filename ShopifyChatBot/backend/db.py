import asyncpg
from fastapi import HTTPException

async def get_db_pool():
    # Always use as a FastAPI dependency
    from main import app
    return app.state.db_pool

# This function supports multi-tenant (multi-shop) access by looking up the access token for each shop.
async def get_shop_token(pool, shop_domain):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT "accessToken" FROM "Session" WHERE "shop" = $1',
            shop_domain
        )
        if not row:
            raise HTTPException(status_code=404, detail="Shop not found")
        access_token = row["accessToken"]
        print("Using access token:", access_token)
        return row["accessToken"]

    
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from db import get_db_pool
import os
import httpx
import urllib.parse
import logging
logger = logging.getLogger(__name__)

router = APIRouter()

SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET")
SHOPIFY_SCOPES = os.getenv("SHOPIFY_SCOPES", "read_products")
SHOPIFY_REDIRECT_URI = os.getenv("SHOPIFY_REDIRECT_URI")

# 1. Start OAuth: Redirect merchant to Shopify's install page
@router.get("/shopify/install")
async def shopify_install(shop: str):
    params = {
        "client_id": SHOPIFY_API_KEY,
        "scope": SHOPIFY_SCOPES,
        "redirect_uri": SHOPIFY_REDIRECT_URI,
        "state": "optional-csrf-token",
        "grant_options[]": "per-user"
    }
    url = f"https://{shop}/admin/oauth/authorize?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)

# 2. OAuth Callback: Shopify redirects here after merchant approves
@router.get("/shopify/callback")
async def shopify_oauth_callback(request: Request, pool=Depends(get_db_pool)):
    logger.info("Shopify OAuth callback endpoint HIT")
    params = dict(request.query_params)
    shop = params.get("shop")
    code = params.get("code")
    hmac_received = params.get("hmac")
    logger.info(f"Callback params: shop={shop}, code={code}, hmac={hmac_received}")

    if not shop or not code:
        logger.error("Missing shop or code in callback")
        raise HTTPException(status_code=400, detail="Missing shop or code in callback.")

    # Exchange code for access token
    token_url = f"https://{shop}/admin/oauth/access_token"
    payload = {
        "client_id": SHOPIFY_API_KEY,
        "client_secret": SHOPIFY_API_SECRET,
        "code": code
    }
    logger.info(f"Requesting access token from Shopify for shop: {shop}")
    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, json=payload)
        logger.info(f"Shopify token exchange response: {resp.status_code} {resp.text}")
        if resp.status_code != 200:
            logger.error("Failed to get access token from Shopify")
            raise HTTPException(status_code=500, detail="Failed to get access token from Shopify.")
        data = resp.json()
        access_token = data.get("access_token")
        if not access_token:
            logger.error("No access token in Shopify response")
            raise HTTPException(status_code=500, detail="No access token in Shopify response.")

    # Save shop and access token to DB
    logger.info(f"Saving shop and access token to DB: shop={shop}")
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO shops (shop_domain, access_token)
            VALUES ($1, $2)
            ON CONFLICT (shop_domain) DO UPDATE SET access_token = EXCLUDED.access_token
            """,
            shop, access_token
        )
    logger.info(f"Inserted/updated shop: {shop}")

    # Redirect to your app's main page
    logger.info("Redirecting to app main page")
    return RedirectResponse(url="https://aishopifyapp.onrender.com") 
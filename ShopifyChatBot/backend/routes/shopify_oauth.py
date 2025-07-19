from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from db import get_db_pool
import os
import httpx
import urllib.parse

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
    params = dict(request.query_params)
    shop = params.get("shop")
    code = params.get("code")
    hmac = params.get("hmac")

    if not shop or not code:
        raise HTTPException(status_code=400, detail="Missing shop or code in callback.")

    # Exchange code for access token
    token_url = f"https://{shop}/admin/oauth/access_token"
    payload = {
        "client_id": SHOPIFY_API_KEY,
        "client_secret": SHOPIFY_API_SECRET,
        "code": code
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, json=payload)
        print("Shopify token exchange response:", resp.status_code, resp.text)
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to get access token from Shopify.")
        data = resp.json()
        access_token = data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=500, detail="No access token in Shopify response.")

    # Save shop and access token to DB
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO shops (shop_domain, access_token)
            VALUES ($1, $2)
            ON CONFLICT (shop_domain) DO UPDATE SET access_token = EXCLUDED.access_token
            """,
            shop, access_token
        )

    # Redirect to a success page or your app's dashboard
    return RedirectResponse(url="https://aishopifyapp.onrender.com")  # Change as needed 
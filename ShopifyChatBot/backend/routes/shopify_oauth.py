from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
import os
import urllib.parse
import httpx
from starlette.responses import JSONResponse
from db import get_db_pool

router = APIRouter()

@router.get("/install")
async def install(request: Request):
    shop = request.query_params.get("shop")
    if not shop:
        return JSONResponse({"error": "Missing shop parameter"}, status_code=400)
    client_id = os.getenv("SHOPIFY_API_KEY")
    scopes = os.getenv("SHOPIFY_SCOPES", "read_products,write_orders")
    redirect_uri = os.getenv("SHOPIFY_REDIRECT_URI")
    oauth_url = (
        f"https://{shop}/admin/oauth/authorize"
        f"?client_id={client_id}"
        f"&scope={urllib.parse.quote(scopes)}"
        f"&redirect_uri={urllib.parse.quote(redirect_uri)}"
        f"&state=nonce"
    )
    return RedirectResponse(oauth_url)

@router.get("/callback")
async def callback(request: Request):
    params = request.query_params
    shop = params.get("shop")
    code = params.get("code")
    if not shop or not code:
        return JSONResponse({"error": "Missing shop or code"}, status_code=400)
    client_id = os.getenv("SHOPIFY_API_KEY")
    client_secret = os.getenv("SHOPIFY_API_SECRET")
    token_url = f"https://{shop}/admin/oauth/access_token"
    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, json={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code
        })
        if resp.status_code != 200:
            return JSONResponse({"error": "Failed to get access token"}, status_code=500)
        data = resp.json()
        access_token = data.get("access_token")
        if not access_token:
            return JSONResponse({"error": "No access token in response"}, status_code=500)
        # Save shop and access_token to DB
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO "Shop" (shop, accessToken) VALUES ($1, $2) ON CONFLICT (shop) DO UPDATE SET accessToken = $2',
                shop, access_token
            )
        # Redirect to a success page or your app's frontend
        return RedirectResponse(f"https://cartrecover-bot.onrender.com/success?shop={shop}") 
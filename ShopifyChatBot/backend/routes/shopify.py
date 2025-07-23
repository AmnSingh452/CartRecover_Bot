from fastapi import APIRouter, Request, HTTPException, Depends
import requests
import os, random, string
from datetime import datetime, timedelta
from dependencies import session_manager
from db import get_db_pool, get_shop_token
from fastapi.responses import JSONResponse

router = APIRouter()

@router.post("/recommendations")
async def get_recommendations(request: Request, pool=Depends(get_db_pool)):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid or missing JSON body"})
    product_ids = data.get("product_ids", [])
    customer_id = data.get("customer_id")
    shop_domain = data.get("shop_domain")
    if not shop_domain:
        return JSONResponse(status_code=400, content={"error": "Missing shop_domain"})
    access_token = await get_shop_token(pool, shop_domain)
    recommendations = []

    # 1. Cart-based recommendations
    for pid in product_ids:
        url = f"https://{shop_domain}/recommendations/products.json?product_id={pid}&limit=4"
        resp = requests.get(url)
        if resp.status_code == 200:
            try:
                recs = resp.json().get("products", [])
            except Exception as e:
                print("JSON decode error (cart-based):", e, resp.text)
                recs = []
            recommendations.extend(recs)

    # 2. Customer history-based recommendations
    if customer_id:
        orders_url = f"https://{shop_domain}/admin/api/2023-07/orders.json?customer_id={customer_id}&status=any"
        headers = {"X-Shopify-Access-Token": access_token}
        orders_resp = requests.get(orders_url, headers=headers)
        if orders_resp.status_code == 200:
            try:
                orders = orders_resp.json().get("orders", [])
            except Exception as e:
                print("JSON decode error (orders):", e, orders_resp.text)
                orders = []
            purchased_product_ids = set()
            for order in orders:
                for item in order.get("line_items", []):
                    purchased_product_ids.add(item["product_id"])
            for pid in purchased_product_ids:
                url = f"https://{shop_domain}/recommendations/products.json?product_id={pid}&limit=2"
                rec_resp = requests.get(url)
                if rec_resp.status_code == 200:
                    try:
                        recs = rec_resp.json().get("products", [])
                    except Exception as e:
                        print("JSON decode error (history-based):", e, rec_resp.text)
                        recs = []
                    recommendations.extend(recs)

    # 3. Fallback: Popular products
    if not recommendations:
        popular_url = f"https://{shop_domain}/admin/api/2023-07/products.json?order=best-selling&limit=4"
        headers = {"X-Shopify-Access-Token": access_token}
        pop_resp = requests.get(popular_url, headers=headers)
        if pop_resp.status_code == 200:
            try:
                recommendations = pop_resp.json().get("products", [])
            except Exception as e:
                print("JSON decode error (popular):", e, pop_resp.text)
                recommendations = []

    # Deduplicate recommendations
    seen = set()
    unique_recs = []
    for rec in recommendations:
        if rec["id"] not in seen:
            unique_recs.append(rec)
            seen.add(rec["id"])
    return JSONResponse(content={"recommendations": unique_recs[:4]})
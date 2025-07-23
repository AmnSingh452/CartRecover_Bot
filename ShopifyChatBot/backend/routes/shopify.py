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
        headers = {"X-Shopify-Access-Token": access_token}
        resp = requests.get(url, headers=headers)
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
                headers = {"X-Shopify-Access-Token": access_token}

                rec_resp = requests.get(url,headers=headers)
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


def generate_random_code(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

@router.post("/abandoned-cart-discount")
async def abandoned_cart_discount(request: Request, pool=Depends(get_db_pool)):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid or missing JSON body"})
    session_id = data.get("session_id")
    shop_domain = data.get("shop_domain")
    if not shop_domain:
        return JSONResponse(status_code=400, content={"error": "Missing shop_domain"})
    access_token = await get_shop_token(pool, shop_domain)
    if not session_id:
        return JSONResponse(status_code=400, content={"error": "session_id is required"})
    session = session_manager.get_session(session_id)
    if not session:
        return JSONResponse(status_code=404, content={"error": "Session not found"})
    if not session.can_generate_discount_code():
        return JSONResponse(status_code=429, content={"error": "You can only generate one discount code per hour. Please try again later.", "discount_codes": session.discount_codes})
    discount_percentage = data.get("discount_percentage", 10)
    code = generate_random_code()
    now = datetime.utcnow().isoformat() + "Z"

    # 1. Create price rule
    price_rule_url = f"https://{shop_domain}/admin/api/2023-07/price_rules.json"
    price_rule_payload = {
        "price_rule": {
            "title": f"AbandonedCart-{code}",
            "target_type": "line_item",
            "target_selection": "all",
            "allocation_method": "across",
            "value_type": "percentage",
            "value": f"-{discount_percentage}",
            "customer_selection": "all",
            "starts_at": now,
            "usage_limit": 1
        }
    }
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }
    pr_resp = requests.post(price_rule_url, json=price_rule_payload, headers=headers)
    if pr_resp.status_code != 201:
        return JSONResponse(status_code=500, content={"error": pr_resp.text})
    price_rule_id = pr_resp.json()["price_rule"]["id"]

    # 2. Create discount code
    discount_url = f"https://{shop_domain}/admin/api/2023-07/price_rules/{price_rule_id}/discount_codes.json"
    discount_payload = {"discount_code": {"code": code}}
    dc_resp = requests.post(discount_url, json=discount_payload, headers=headers)
    if dc_resp.status_code != 201:
        return JSONResponse(status_code=500, content={"error": dc_resp.text})

    session.record_discount_code(code)
    return JSONResponse(content={"discount_code": code, "discount_codes": session.discount_codes})
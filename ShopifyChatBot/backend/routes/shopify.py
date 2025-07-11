from fastapi import APIRouter, Request
import requests
import os

router = APIRouter()
SHOPIFY_STORE_DOMAIN = os.getenv("SHOPIFY_STORE_URL")
SHOPIFY_ADMIN_API_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

@router.post("/api/recommendations")
async def get_recommendations(request: Request):
    data = await request.json()
    product_ids = data.get("product_ids", [])
    customer_id = data.get("customer_id")
    recommendations = []

    print("Received product_ids:", product_ids)
    print("Received customer_id:", customer_id)
    print("SHOPIFY_STORE_DOMAIN:", SHOPIFY_STORE_DOMAIN)
    print("SHOPIFY_ADMIN_API_TOKEN:", SHOPIFY_ADMIN_API_TOKEN)

    # 1. Cart-based recommendations
    for pid in product_ids:
        url = f"https://{SHOPIFY_STORE_DOMAIN}/recommendations/products.json?product_id={pid}&limit=4"
        resp = requests.get(url)
        if resp.status_code == 200:
            recs = resp.json().get("products", [])
            recommendations.extend(recs)

    # 2. Customer history-based recommendations
    if customer_id:
        orders_url = f"https://{SHOPIFY_STORE_DOMAIN}/admin/api/2023-07/orders.json?customer_id={customer_id}&status=any"
        headers = {"X-Shopify-Access-Token": SHOPIFY_ADMIN_API_TOKEN}
        orders_resp = requests.get(orders_url, headers=headers)
        if orders_resp.status_code == 200:
            orders = orders_resp.json().get("orders", [])
            purchased_product_ids = set()
            for order in orders:
                for item in order.get("line_items", []):
                    purchased_product_ids.add(item["product_id"])
            for pid in purchased_product_ids:
                url = f"https://{SHOPIFY_STORE_DOMAIN}/recommendations/products.json?product_id={pid}&limit=2"
                rec_resp = requests.get(url)
                if rec_resp.status_code == 200:
                    recs = rec_resp.json().get("products", [])
                    recommendations.extend(recs)

    # 3. Fallback: Popular products
    if not recommendations:
        popular_url = f"https://{SHOPIFY_STORE_DOMAIN}/admin/api/2023-07/products.json?order=best-selling&limit=4"
        headers = {"X-Shopify-Access-Token": SHOPIFY_ADMIN_API_TOKEN}
        pop_resp = requests.get(popular_url, headers=headers)
        if pop_resp.status_code == 200:
            recommendations = pop_resp.json().get("products", [])

    # Deduplicate recommendations
    seen = set()
    unique_recs = []
    for rec in recommendations:
        if rec["id"] not in seen:
            unique_recs.append(rec)
            seen.add(rec["id"])
        print("Returning recommendations:", unique_recs[:4])
    return {"recommendations": unique_recs[:4]}


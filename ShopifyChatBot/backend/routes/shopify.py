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
        try:
            data = await request.json()
        except Exception:
            data = {}
        product_ids = data.get("product_ids", [])
        customer_id = data.get("customer_id")
        shop_domain = data.get("shop_domain")
        # Fallback to default shop domain if not provided
        if not shop_domain:
            shop_domain = "aman-chatbot-test.myshopify.com"  # Default fallback
        print(f"🔍 Recommendations request received: product_ids={product_ids}, customer_id={customer_id}, shop_domain={shop_domain}")
        try:
            access_token = await get_shop_token(pool, shop_domain)
            if not access_token:
                raise Exception("No access token available")
        except Exception as e:
            print(f"⚠️ Could not get shop token: {e}")
            print("🔄 Falling back to mock data")
            return JSONResponse(content={"recommendations": get_mock_recommendations()})
        recommendations = []
        try:
            # 1. Cart-based recommendations
            for pid in product_ids[:4]:  # Limit to 4 products
                try:
                    url = f"https://{shop_domain}/admin/api/2023-07/products/{pid}.json"
                    headers = {"X-Shopify-Access-Token": access_token}
                    resp = requests.get(url, headers=headers, timeout=10)
                    if resp.status_code == 200:
                        try:
                            product = resp.json().get("product")
                        except Exception as e:
                            print("JSON decode error (cart-based):", e, resp.text)
                            product = None
                        if product:
                            recommendations.append(product)
                except Exception as e:
                    print(f"Error fetching product {pid}:", e)
                    continue
            # 2. Customer history-based recommendations
            if customer_id and len(recommendations) < 4:
                try:
                    orders_url = f"https://{shop_domain}/admin/api/2023-07/orders.json?customer_id={customer_id}&status=any&limit=10"
                    headers = {"X-Shopify-Access-Token": access_token}
                    orders_resp = requests.get(orders_url, headers=headers, timeout=10)
                    if orders_resp.status_code == 200:
                        try:
                            orders = orders_resp.json().get("orders", [])
                        except Exception as e:
                            print("JSON decode error (orders):", e, orders_resp.text)
                            orders = []
                        purchased_product_ids = set()
                        for order in orders:
                            for item in order.get("line_items", []):
                                purchased_product_ids.add(item.get("product_id"))
                        for pid in list(purchased_product_ids)[:4]:  # Limit to prevent too many requests
                            if len(recommendations) >= 4:
                                break
                            try:
                                url = f"https://{shop_domain}/admin/api/2023-07/products/{pid}.json"
                                headers = {"X-Shopify-Access-Token": access_token}
                                rec_resp = requests.get(url, headers=headers, timeout=10)
                                if rec_resp.status_code == 200:
                                    try:
                                        product = rec_resp.json().get("product")
                                    except Exception as e:
                                        print("JSON decode error (history-based):", e, rec_resp.text)
                                        product = None
                                    if product:
                                        recommendations.append(product)
                            except Exception as e:
                                print(f"Error fetching customer history product {pid}:", e)
                                continue
                except Exception as e:
                    print("Error fetching customer orders:", e)
            # 3. Fallback: Popular products
            if len(recommendations) < 4:
                try:
                    popular_url = f"https://{shop_domain}/admin/api/2023-07/products.json?limit=4"
                    headers = {"X-Shopify-Access-Token": access_token}
                    pop_resp = requests.get(popular_url, headers=headers, timeout=10)
                    if pop_resp.status_code == 200:
                        try:
                            popular_products = pop_resp.json().get("products", [])
                            recommendations.extend(popular_products)
                        except Exception as e:
                            print("JSON decode error (popular):", e, pop_resp.text)
                except Exception as e:
                    print("Error fetching popular products:", e)
            # Deduplicate recommendations
            seen = set()
            unique_recs = []
            for rec in recommendations:
                if rec and rec.get("id") and rec["id"] not in seen:
                    unique_recs.append(rec)
                    seen.add(rec["id"])
            # If no recommendations found, return mock data
            if not unique_recs:
                print("🔄 No real recommendations found, using mock data")
                unique_recs = get_mock_recommendations()
            return JSONResponse(content={"recommendations": unique_recs[:4]})
        except Exception as shopify_error:
            print(f"❌ Shopify API error: {shopify_error}")
            print("🔄 Falling back to mock data due to Shopify API error")
            return JSONResponse(content={"recommendations": get_mock_recommendations()})
    except Exception as e:
        print(f"❌ General error in recommendations API: {e}")
        print("🔄 Falling back to mock data due to general error")
        return JSONResponse(content={"recommendations": get_mock_recommendations()})

def get_mock_recommendations():
    """Return mock product recommendations when real API fails"""
    return [
        {
            "id": 8001,
            "title": "Classic Cotton T-Shirt",
            "handle": "classic-cotton-t-shirt",
            "description": "Comfortable cotton t-shirt perfect for everyday wear.",
            "vendor": "Fashion Co",
            "images": [{"src": "https://cdn.shopify.com/s/files/1/0001/0001/products/tshirt.jpg"}],
            "variants": [{"price": "24.99", "compare_at_price": "29.99"}]
        },
        {
            "id": 8002,
            "title": "Denim Jeans", 
            "handle": "denim-jeans",
            "description": "Premium denim jeans with perfect fit.",
            "vendor": "Denim Works",
            "images": [{"src": "https://cdn.shopify.com/s/files/1/0001/0001/products/jeans.jpg"}],
            "variants": [{"price": "79.99", "compare_at_price": "99.99"}]
        },
        {
            "id": 8003,
            "title": "Leather Sneakers",
            "handle": "leather-sneakers", 
            "description": "Stylish leather sneakers for casual outings.",
            "vendor": "Shoe Store",
            "images": [{"src": "https://cdn.shopify.com/s/files/1/0001/0001/products/sneakers.jpg"}],
            "variants": [{"price": "120.00"}]
        },
        {
            "id": 8004,
            "title": "Wool Sweater",
            "handle": "wool-sweater",
            "description": "Warm and cozy wool sweater for cold days.", 
            "vendor": "Knit Co",
            "images": [{"src": "https://cdn.shopify.com/s/files/1/0001/0001/products/sweater.jpg"}],
            "variants": [{"price": "89.99", "compare_at_price": "119.99"}]
        }
    ]


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
from fastapi import APIRouter, Request, HTTPException, Depends
import requests
import os, random, string
from datetime import datetime, timedelta
from dependencies import session_manager
from db import get_db_pool, get_shop_token
from fastapi.responses import JSONResponse

router = APIRouter()


@router.post("/recommendations")
async def get_recommendations(request: Request, pool=Depends(get_db_pool)    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Error parsing discount response: {str(e)}"})
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
            # 1. Cart-based recommendations using GraphQL
            if product_ids:
                try:
                    graphql_url = f"https://{shop_domain}/admin/api/2023-07/graphql.json"
                    headers = {
                        "X-Shopify-Access-Token": access_token,
                        "Content-Type": "application/json"
                    }
                    
                    # Build GraphQL query for products by ID
                    ids = ', '.join([f'"gid://shopify/Product/{pid}"' for pid in product_ids[:4]])
                    query = f"""
                    {{
                      nodes(ids: [{ids}]) {{
                        ... on Product {{
                          id
                          title
                          handle
                          description
                          vendor
                          images(first: 1) {{
                            edges {{
                              node {{
                                src: url
                              }}
                            }}
                          }}
                          variants(first: 5) {{
                            edges {{
                              node {{
                                id
                                title
                                price
                                compareAtPrice
                              }}
                            }}
                          }}
                        }}
                      }}
                    }}
                    """
                    
                    resp = requests.post(graphql_url, headers=headers, json={"query": query}, timeout=10)
                    if resp.status_code == 200:
                        try:
                            data = resp.json()
                            if "data" in data and "nodes" in data["data"]:
                                for node in data["data"]["nodes"]:
                                    if node:  # GraphQL returns None for invalid IDs
                                        # Convert GraphQL response to REST-like format for compatibility
                                        product = {
                                            "id": int(node["id"].split("/")[-1]),  # Extract numeric ID
                                            "title": node["title"],
                                            "handle": node["handle"],
                                            "description": node["description"],
                                            "vendor": node["vendor"],
                                            "images": [{"src": edge["node"]["src"]} for edge in node["images"]["edges"]],
                                            "variants": [
                                                {
                                                    "price": edge["node"]["price"],
                                                    "compare_at_price": edge["node"]["compareAtPrice"]
                                                } for edge in node["variants"]["edges"]
                                            ]
                                        }
                                        recommendations.append(product)
                        except Exception as e:
                            print("JSON decode error (cart-based GraphQL):", e, resp.text)
                except Exception as e:
                    print(f"Error fetching products via GraphQL: {e}")
            # 2. Customer history-based recommendations using GraphQL
            if customer_id and len(recommendations) < 4:
                try:
                    graphql_url = f"https://{shop_domain}/admin/api/2023-07/graphql.json"
                    headers = {
                        "X-Shopify-Access-Token": access_token,
                        "Content-Type": "application/json"
                    }
                    
                    # GraphQL query to get customer orders
                    orders_query = f"""
                    {{
                      orders(first: 10, query: "customer_id:{customer_id}") {{
                        edges {{
                          node {{
                            id
                            lineItems(first: 50) {{
                              edges {{
                                node {{
                                  product {{
                                    id
                                    title
                                    handle
                                    description
                                    vendor
                                    images(first: 1) {{
                                      edges {{
                                        node {{
                                          src: url
                                        }}
                                      }}
                                    }}
                                    variants(first: 5) {{
                                      edges {{
                                        node {{
                                          id
                                          title
                                          price
                                          compareAtPrice
                                        }}
                                      }}
                                    }}
                                  }}
                                }}
                              }}
                            }}
                          }}
                        }}
                      }}
                    }}
                    """
                    
                    orders_resp = requests.post(graphql_url, headers=headers, json={"query": orders_query}, timeout=10)
                    if orders_resp.status_code == 200:
                        try:
                            data = orders_resp.json()
                            if "data" in data and "orders" in data["data"]:
                                purchased_products = set()
                                for order_edge in data["data"]["orders"]["edges"]:
                                    for item_edge in order_edge["node"]["lineItems"]["edges"]:
                                        product = item_edge["node"]["product"]
                                        if product:
                                            product_id = int(product["id"].split("/")[-1])
                                            if product_id not in purchased_products and len(recommendations) < 4:
                                                purchased_products.add(product_id)
                                                # Convert to REST-like format
                                                formatted_product = {
                                                    "id": product_id,
                                                    "title": product["title"],
                                                    "handle": product["handle"],
                                                    "description": product["description"],
                                                    "vendor": product["vendor"],
                                                    "images": [{"src": edge["node"]["src"]} for edge in product["images"]["edges"]],
                                                    "variants": [
                                                        {
                                                            "price": edge["node"]["price"],
                                                            "compare_at_price": edge["node"]["compareAtPrice"]
                                                        } for edge in product["variants"]["edges"]
                                                    ]
                                                }
                                                recommendations.append(formatted_product)
                        except Exception as e:
                            print("JSON decode error (orders GraphQL):", e, orders_resp.text)
                except Exception as e:
                    print("Error fetching customer orders via GraphQL:", e)
            # 3. Fallback: Popular products using GraphQL
            if len(recommendations) < 4:
                try:
                    graphql_url = f"https://{shop_domain}/admin/api/2023-07/graphql.json"
                    headers = {
                        "X-Shopify-Access-Token": access_token,
                        "Content-Type": "application/json"
                    }
                    
                    # GraphQL query for popular products (sorted by best selling)
                    popular_query = """
                    {
                      products(first: 4, sortKey: BEST_SELLING) {
                        edges {
                          node {
                            id
                            title
                            handle
                            description
                            vendor
                            images(first: 1) {
                              edges {
                                node {
                                  src: url
                                }
                              }
                            }
                            variants(first: 5) {
                              edges {
                                node {
                                  id
                                  title
                                  price
                                  compareAtPrice
                                }
                              }
                            }
                          }
                        }
                      }
                    }
                    """
                    
                    pop_resp = requests.post(graphql_url, headers=headers, json={"query": popular_query}, timeout=10)
                    if pop_resp.status_code == 200:
                        try:
                            data = pop_resp.json()
                            if "data" in data and "products" in data["data"]:
                                for edge in data["data"]["products"]["edges"]:
                                    product = edge["node"]
                                    # Convert to REST-like format
                                    formatted_product = {
                                        "id": int(product["id"].split("/")[-1]),
                                        "title": product["title"],
                                        "handle": product["handle"],
                                        "description": product["description"],
                                        "vendor": product["vendor"],
                                        "images": [{"src": img_edge["node"]["src"]} for img_edge in product["images"]["edges"]],
                                        "variants": [
                                            {
                                                "price": var_edge["node"]["price"],
                                                "compare_at_price": var_edge["node"]["compareAtPrice"]
                                            } for var_edge in product["variants"]["edges"]
                                        ]
                                    }
                                    recommendations.append(formatted_product)
                        except Exception as e:
                            print("JSON decode error (popular GraphQL):", e, pop_resp.text)
                except Exception as e:
                    print("Error fetching popular products via GraphQL:", e)
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

    # Create discount code using GraphQL
    graphql_url = f"https://{shop_domain}/admin/api/2023-07/graphql.json"
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }
    
    # GraphQL mutation to create discount code
    mutation = f"""
    mutation {{
      discountCodeBasicCreate(basicCodeDiscount: {{
        title: "AbandonedCart-{code}"
        code: "{code}"
        startsAt: "{now}"
        usageLimit: 1
        customerSelection: {{
          all: true
        }}
        customerGets: {{
          value: {{
            percentage: {discount_percentage / 100.0}
          }}
          items: {{
            all: true
          }}
        }}
      }}) {{
        codeDiscountNode {{
          id
          codeDiscount {{
            ... on DiscountCodeBasic {{
              title
              codes(first: 1) {{
                edges {{
                  node {{
                    code
                  }}
                }}
              }}
            }}
          }}
        }}
        userErrors {{
          field
          message
        }}
      }}
    }}
    """
    
    resp = requests.post(graphql_url, headers=headers, json={"query": mutation}, timeout=10)
    
    if resp.status_code != 200:
        return JSONResponse(status_code=500, content={"error": f"GraphQL request failed: {resp.text}"})
    
    try:
        result = resp.json()
        if "errors" in result:
            return JSONResponse(status_code=500, content={"error": f"GraphQL errors: {result['errors']}"})
        
        user_errors = result.get("data", {}).get("discountCodeBasicCreate", {}).get("userErrors", [])
        if user_errors:
            return JSONResponse(status_code=500, content={"error": f"Discount creation failed: {user_errors}"})
        
        # Successfully created discount
        session.record_discount_code(code)
        return JSONResponse(content={"discount_code": code, "discount_codes": session.discount_codes})
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Error parsing discount response: {str(e)}"}
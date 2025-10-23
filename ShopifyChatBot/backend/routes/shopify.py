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
                    
                    print(f"🔍 Fetching popular products from: {shop_domain}")
                    pop_resp = requests.post(graphql_url, headers=headers, json={"query": popular_query}, timeout=10)
                    print(f"📡 Popular products API response: {pop_resp.status_code}")
                    if pop_resp.status_code == 200:
                        try:
                            data = pop_resp.json()
                            print(f"📊 GraphQL response data: {data}")
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
                print(f"🔄 No real recommendations found for shop: {shop_domain}")
                print(f"📊 Attempted: Cart-based ({len(product_ids)} products), Customer-based ({'Yes' if customer_id else 'No'}), Popular products")
                print("🔄 Using mock data as fallback - this suggests Shopify API may not have products or API calls are failing")
                unique_recs = get_mock_recommendations()
            else:
                print(f"✅ Found {len(unique_recs)} real products from Shopify for shop: {shop_domain}")
            return JSONResponse(content={"recommendations": unique_recs[:4]})
        except Exception as shopify_error:
            print(f"❌ Shopify API error: {shopify_error}")
            print(f"🏪 Shop: {shop_domain}, Products: {product_ids}, Customer: {customer_id}")
            print("🔄 Falling back to mock data due to Shopify API error")
            return JSONResponse(content={"recommendations": get_mock_recommendations()})
    except Exception as e:
        print(f"❌ General error in recommendations API: {e}")
        print(f"🏪 Shop: {shop_domain}, Products: {product_ids}, Customer: {customer_id}")
        print("🔄 Falling back to mock data due to general error")
        return JSONResponse(content={"recommendations": get_mock_recommendations()})

def get_mock_recommendations():
    """
    Return fallback product recommendations when Shopify API fails.
    
    ⚠️ WARNING: This is fallback data used when Shopify API calls fail.
    These products may not exist in your actual store.
    
    To fix this issue:
    1. Check if your Shopify access token is valid
    2. Verify your shop domain is correct
    3. Ensure your store has products
    4. Check GraphQL API permissions
    """
    return [
        {
            "id": "fallback-1",
            "title": "🔄 Product recommendations temporarily unavailable",
            "handle": "api-fallback-product-1",
            "description": "We're having trouble connecting to your product catalog right now. Please try again in a moment, or contact support if this issue persists.",
            "vendor": "System Message",
            "images": [{"src": "https://via.placeholder.com/300x300?text=Product+Unavailable"}],
            "variants": [{"price": "N/A", "compare_at_price": None}]
        },
        {
            "id": "fallback-2", 
            "title": "💡 Check your store setup",
            "handle": "api-fallback-product-2",
            "description": "This message appears when we can't fetch real products from your Shopify store. Please verify your store has products and API access is configured correctly.",
            "vendor": "System Message",
            "images": [{"src": "https://via.placeholder.com/300x300?text=API+Issue"}],
            "variants": [{"price": "N/A", "compare_at_price": None}]
        },
        {
            "id": "fallback-3",
            "title": "🛠️ API Connection Issue",
            "handle": "api-fallback-product-3", 
            "description": "The chatbot cannot currently access your product catalog. This could be due to API permissions, network issues, or store configuration problems.",
            "vendor": "System Message",
            "images": [{"src": "https://via.placeholder.com/300x300?text=Connection+Issue"}],
            "variants": [{"price": "N/A", "compare_at_price": None}]
        },
        {
            "id": "fallback-4",
            "title": "📞 Contact Support",
            "handle": "api-fallback-product-4",
            "description": "If you continue seeing this message, please contact technical support to resolve the product catalog connection issue.",
            "vendor": "System Message",
            "images": [{"src": "https://via.placeholder.com/300x300?text=Need+Help"}],
            "variants": [{"price": "N/A", "compare_at_price": None}]
        }
    ]


def generate_random_code(length=6):
    """Generate random string for discount codes"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

async def check_existing_codes_by_customer(shop_domain: str, access_token: str, cart_token: str = None):
    """
    Check for existing active discount codes for this customer/cart
    Uses cart_token or browser fingerprint to identify returning customers
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Check if we have any recent codes for this cart_token
        # Since we don't have persistent storage, we'll query Shopify for recent codes
        graphql_url = f"https://{shop_domain}/admin/api/2024-01/graphql.json"
        headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json"
        }
        
        # Query for recent discount codes created in the last 24 hours
        # that match our abandoned cart pattern - using broader search
        query = """
        query getRecentDiscounts {
            discountNodes(first: 50, query: "title:AbandonedCart*") {
                edges {
                    node {
                        id
                        discount {
                            ... on DiscountCodeBasic {
                                title
                                codes(first: 1) {
                                    edges {
                                        node {
                                            code
                                        }
                                    }
                                }
                                startsAt
                                endsAt
                                usageLimit
                                asyncUsageCount
                                status
                            }
                        }
                    }
                }
            }
        }
        """
        
        logger.info(f"🔍 Checking for existing discount codes in shop: {shop_domain}")
        
        resp = requests.post(graphql_url, headers=headers, json={"query": query}, timeout=15)
        
        if resp.status_code == 200:
            data = resp.json()
            
            if "errors" in data:
                logger.warning(f"⚠️ GraphQL errors checking existing codes: {data['errors']}")
                return None
            
            discount_nodes = data.get("data", {}).get("discountNodes", {}).get("edges", [])
            logger.info(f"🔍 Found {len(discount_nodes)} total discount codes to check")
            
            # Look for unused codes created in the last 2 hours (recent enough to be from same session)
            from datetime import timezone
            now = datetime.now(timezone.utc)
            recent_cutoff = now - timedelta(hours=2)  
            logger.info(f"⏰ Current time: {now.isoformat()}, Checking codes created after: {recent_cutoff.isoformat()}")
            
            for i, edge in enumerate(discount_nodes):
                discount = edge["node"]["discount"]
                if not discount:
                    continue
                
                # Check if code is still active and unused
                try:
                    starts_at = datetime.fromisoformat(discount["startsAt"].replace("Z", "+00:00"))
                    ends_at = datetime.fromisoformat(discount["endsAt"].replace("Z", "+00:00"))
                    usage_count = discount.get("asyncUsageCount", 0)
                    status = discount.get("status", "ACTIVE")
                    title = discount.get("title", "")
                    
                    codes = discount.get("codes", {}).get("edges", [])
                    code_value = codes[0]["node"]["code"] if codes else "NO_CODE"
                    
                    logger.info(f"📋 Code #{i+1}: {code_value} | Title: {title} | Status: {status} | Usage: {usage_count} | Created: {starts_at.isoformat()}")
                    
                    # If code is active, unused, and created recently, return it
                    if (status == "ACTIVE" and 
                        usage_count == 0 and 
                        starts_at >= recent_cutoff and 
                        ends_at > now):
                        
                        if codes:
                            code = codes[0]["node"]["code"]
                            logger.info(f"✅ Found existing unused code: {code} (created {starts_at.isoformat()})")
                            return {
                                "code": code,
                                "created_at": starts_at.isoformat(),
                                "expires_at": ends_at.isoformat()
                            }
                except Exception as datetime_error:
                    logger.error(f"❌ Error processing code #{i+1}: {datetime_error}")
                    continue
            
            logger.info(f"📝 No existing active codes found for recent time period (checked {len(discount_nodes)} codes)")
            return None
            
        else:
            logger.warning(f"⚠️ Failed to check existing codes: {resp.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error checking existing codes: {e}")
        return None

async def check_existing_discount_codes(session_id: str, shop_domain: str, access_token: str):
    """
    Check if the session/customer has any existing active (unused) discount codes.
    Returns the first active code found, or None if no active codes exist.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Get session to check for previously generated codes
    session = session_manager.get_session(session_id)
    if not session or not hasattr(session, 'discount_codes') or not session.discount_codes:
        logger.info(f"📝 No previous discount codes found for session {session_id}")
        return None
    
    # Check each previous code to see if it's still active
    graphql_url = f"https://{shop_domain}/admin/api/2024-01/graphql.json"
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }
    
    logger.info(f"🔍 Checking {len(session.discount_codes)} existing codes for session {session_id}")
    
    for code in session.discount_codes:
        try:
            # Query to get discount code details and usage
            query = f"""
            query {{
              codeDiscountNodes(first: 1, query: "code:{code}") {{
                edges {{
                  node {{
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
                        startsAt
                        endsAt
                        usageLimit
                        asyncUsageCount
                        status
                      }}
                    }}
                  }}
                }}
              }}
            }}
            """
            
            resp = requests.post(graphql_url, headers=headers, json={"query": query}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                
                if "errors" in data:
                    logger.warning(f"⚠️ GraphQL error checking code {code}: {data['errors']}")
                    continue
                
                edges = data.get("data", {}).get("codeDiscountNodes", {}).get("edges", [])
                if edges:
                    discount_node = edges[0]["node"]
                    discount = discount_node.get("codeDiscount", {})
                    
                    # Check if code is still active and unused
                    usage_count = discount.get("asyncUsageCount", 0)
                    usage_limit = discount.get("usageLimit", 1)
                    status = discount.get("status", "").upper()
                    ends_at = discount.get("endsAt")
                    
                    logger.info(f"📊 Code {code}: status={status}, used={usage_count}/{usage_limit}, expires={ends_at}")
                    
                    # Check if code is still valid and unused
                    if (status == "ACTIVE" and 
                        usage_count < usage_limit and 
                        (not ends_at or ends_at > datetime.utcnow().isoformat() + "Z")):
                        
                        logger.info(f"✅ Found active unused code: {code}")
                        return code
                    else:
                        logger.info(f"❌ Code {code} is expired/used: status={status}, used={usage_count}")
                else:
                    logger.info(f"❌ Code {code} not found in Shopify")
            else:
                logger.warning(f"⚠️ HTTP error checking code {code}: {resp.status_code}")
                        
        except Exception as e:
            logger.error(f"❌ Error checking discount code {code}: {e}")
            continue
    
    logger.info(f"🔍 No active unused codes found for session {session_id}")
    return None

@router.post("/abandoned-cart-discount")
async def abandoned_cart_discount(request: Request, pool=Depends(get_db_pool)):
    """
    Create abandoned cart discount codes for Shopify apps.
    
    Expected Request Body:
    {
        "session_id": "string",
        "shop_domain": "aman-chatbot-test.myshopify.com",
        "customer_id": "string",
        "cart_data": {},
        "discount_percentage": 10
    }
    
    Response:
    {
        "discount_code": "SAVE10-ABC123",
        "message": "Discount created successfully"
    }
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Log the incoming request
    logger.info(f"🛒 Abandoned cart discount request received from {request.client.host if request.client else 'unknown'}")
    
    try:
        data = await request.json()
        logger.info(f"📝 Request data: {data}")
    except Exception as e:
        logger.error(f"❌ Invalid JSON body: {e}")
        return JSONResponse(
            status_code=400, 
            content={
                "error": "Invalid or missing JSON body",
                "details": f"Request body must be valid JSON: {str(e)}"
            },
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            }
        )
    
    # Extract required fields
    session_id = data.get("session_id")
    shop_domain = data.get("shop_domain")
    customer_id = data.get("customer_id")
    cart_data = data.get("cart_data", {})
    discount_percentage = data.get("discount_percentage", 10)
    
    # Validate required fields
    if not shop_domain:
        logger.error("❌ Missing shop_domain")
        return JSONResponse(
            status_code=400, 
            content={
                "error": "Missing shop_domain",
                "details": "shop_domain is required in request body"
            },
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            }
        )
    
    if not session_id:
        logger.error("❌ Missing session_id")
        return JSONResponse(
            status_code=400, 
            content={
                "error": "session_id is required",
                "details": "session_id must be provided in request body"
            },
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            }
        )
    
    # Validate discount percentage
    if not isinstance(discount_percentage, (int, float)) or discount_percentage <= 0 or discount_percentage > 100:
        logger.error(f"❌ Invalid discount_percentage: {discount_percentage}")
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid discount_percentage",
                "details": "discount_percentage must be a number between 1 and 100"
            },
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            }
        )
    
    try:
        # Get shop access token
        access_token = await get_shop_token(pool, shop_domain)
        logger.info(f"✅ Retrieved access token for shop: {shop_domain}")
    except Exception as e:
        logger.error(f"❌ Failed to get shop token: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to retrieve shop access token",
                "details": f"Could not authenticate with shop {shop_domain}: {str(e)}"
            },
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            }
        )
    
    # Get or create session
    session = session_manager.get_session(session_id)
    if not session:
        logger.warning(f"⚠️ Session {session_id} not found, creating new session")
        try:
            session_id = session_manager.create_session(shop_domain=shop_domain)
            session = session_manager.get_session(session_id)
            logger.info(f"✅ Created new session: {session_id}")
        except Exception as e:
            logger.error(f"❌ Failed to create session: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Failed to create session",
                    "details": f"Could not create session for discount: {str(e)}"
                },
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization"
                }
            )
    
    # Extract cart_token for customer identification
    cart_token = data.get("cart_token", f"fallback-{session_id}")
    
    # Check for existing active discount codes first
    logger.info(f"🔍 Checking for existing active discount codes...")
    existing_code = await check_existing_codes_by_customer(shop_domain, access_token, cart_token)
    
    if existing_code:
        logger.info(f"✅ Returning existing unused code: {existing_code['code']}")
        return JSONResponse(
            content={
                "discount_code": existing_code['code'],
                "message": "Existing discount code returned (unused)"
            },
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            }
        )
    
    # Check session-based rate limiting as fallback (if session management is enabled)
    if hasattr(session, 'can_generate_discount_code') and not session.can_generate_discount_code():
        logger.warning(f"⚠️ Rate limit exceeded for session {session_id}")
        return JSONResponse(
            status_code=429, 
            content={
                "error": "Rate limit exceeded",
                "details": "You can only generate one discount code per hour. Please try again later.",
                "discount_codes": getattr(session, 'discount_codes', [])
            },
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            }
        )
    
    # Check if session already has an active unused discount code
    logger.info(f"🔍 Checking for existing active discount codes...")
    existing_code = await check_existing_discount_codes(session_id, shop_domain, access_token)
    
    if existing_code:
        logger.info(f"♻️ Returning existing active code: {existing_code}")
        return JSONResponse(
            content={
                "discount_code": existing_code,
                "message": "Discount created successfully"
            },
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS", 
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            }
        )
    
    # No active code found, generate new unique discount code with specified format
    random_string = generate_random_code()
    code = f"SAVE{int(discount_percentage)}-{random_string}"
    logger.info(f"� Creating NEW discount code: {code} (no existing codes found)")
    
    # Set discount expiry (24 hours from now)
    now = datetime.utcnow()
    expires_at = (now + timedelta(hours=24)).isoformat() + "Z"
    now_iso = now.isoformat() + "Z"

    # Create discount code using Shopify GraphQL API
    graphql_url = f"https://{shop_domain}/admin/api/2024-01/graphql.json"
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }
    
    logger.info(f"🔗 Creating discount via GraphQL: {graphql_url}")
    
    # GraphQL mutation to create discount code with 24-hour expiry
    mutation = f"""
    mutation {{
      discountCodeBasicCreate(basicCodeDiscount: {{
        title: "AbandonedCart-{code}"
        code: "{code}"
        startsAt: "{now_iso}"
        endsAt: "{expires_at}"
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
        appliesOncePerCustomer: true
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
              startsAt
              endsAt
              usageLimit
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
    
    try:
        resp = requests.post(graphql_url, headers=headers, json={"query": mutation}, timeout=15)
        logger.info(f"📡 Shopify API response status: {resp.status_code}")
        
        if resp.status_code != 200:
            logger.error(f"❌ GraphQL request failed: {resp.status_code} - {resp.text}")
            return JSONResponse(
                status_code=500, 
                content={
                    "error": "Failed to create discount code",
                    "details": f"Shopify API returned {resp.status_code}: {resp.text}"
                },
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization"
                }
            )
        
        result = resp.json()
        logger.info(f"📋 Shopify API response: {result}")
        
        # Check for GraphQL errors
        if "errors" in result:
            logger.error(f"❌ GraphQL errors: {result['errors']}")
            return JSONResponse(
                status_code=500, 
                content={
                    "error": "GraphQL query failed",
                    "details": f"Shopify GraphQL errors: {result['errors']}"
                },
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization"
                }
            )
        
        # Check for user errors (validation failures)
        discount_data = result.get("data", {}).get("discountCodeBasicCreate", {})
        user_errors = discount_data.get("userErrors", [])
        
        if user_errors:
            logger.error(f"❌ Discount creation validation failed: {user_errors}")
            return JSONResponse(
                status_code=400, 
                content={
                    "error": "Discount validation failed",
                    "details": f"Shopify validation errors: {user_errors}"
                },
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization"
                }
            )
        
        # Successfully created discount
        logger.info(f"✅ Discount code created successfully: {code}")
        
        # Record the discount code in session (if session management is available)
        if hasattr(session, 'record_discount_code'):
            session.record_discount_code(code)
            logger.info(f"📝 Recorded discount code in session")
        
        # Return success response in the specified format
        return JSONResponse(
            content={
                "discount_code": code,
                "message": "Discount created successfully"
            },
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS", 
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            }
        )
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Network error calling Shopify API: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Network error",
                "details": f"Failed to connect to Shopify API: {str(e)}"
            },
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            }
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error creating discount: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "details": f"Unexpected error while creating discount: {str(e)}"
            },
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            }
        )

@router.options("/abandoned-cart-discount") 
async def abandoned_cart_discount_options():
    """Handle CORS preflight requests for abandoned cart discount endpoint"""
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Max-Age": "3600"
        }
    )
# Alternative endpoint paths for compatibility with existing clients
@router.post("/shopify/abandoned-cart-discount")
async def shopify_abandoned_cart_discount(request: Request, pool=Depends(get_db_pool)):
    """
    Alternative endpoint path for /api/shopify/abandoned-cart-discount 
    Redirects to the main abandoned_cart_discount function for compatibility
    """
    return await abandoned_cart_discount(request, pool)

@router.options("/shopify/abandoned-cart-discount") 
async def shopify_abandoned_cart_discount_options():
    """Handle CORS preflight requests for /api/shopify/abandoned-cart-discount"""
    return await abandoned_cart_discount_options()

from typing import Dict, Any, List, Optional
import logging
import os
from dotenv import load_dotenv
import aiohttp
import json
import openai
import re

logger = logging.getLogger(__name__)

# Load and check environment variables
load_dotenv()
logger.info("Environment variables loaded for RecommendationAgent")

class RecommendationAgent:
    """
    Provides product recommendations based on user input.
    """
    
    def __init__(self):
        logger.info("Initializing RecommendationAgent")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set for RecommendationAgent.")
        self.openai_client = openai.AsyncOpenAI(api_key=self.openai_api_key)

    async def _extract_keywords_with_gpt(self, message: str) -> Optional[str]:
        """
        Uses GPT to extract relevant product keywords or categories from the user's message.
        """
        # Simple keyword extraction for common patterns
        message_lower = message.lower()
        
        # Check for common product terms directly first
        product_terms = ['jeans', 'jean', 'shirt', 'shoes', 'shoe', 'dress', 'jacket', 'coat', 
                        'watch', 'bag', 'hat', 'pants', 'skirt', 'jewelry', 'tshirt', 't-shirt']
        
        for term in product_terms:
            if term in message_lower:
                return term
        
        # Check for misspellings
        if 'jens' in message_lower or 'jen' in message_lower:
            return 'jeans'
        if 'shoos' in message_lower or 'shoo' in message_lower:
            return 'shoes'
        if 'tshrt' in message_lower:
            return 't-shirt'
        if 'jacet' in message_lower:
            return 'jacket'
        if 'watsh' in message_lower:
            return 'watch'
        
        # Use GPT as fallback for complex queries
        prompt = f"""What product is the user looking for? Reply with only the product name (like "jeans", "shoes", "shirt") or "none" if unclear.

User says: "{message}"

Product:"""

        try:
            response = await self.openai_client.completions.create(
                model="gpt-3.5-turbo-instruct",
                prompt=prompt,
                max_tokens=5,
                n=1,
                stop=["\n", ".", "User:", "Product:"],
                temperature=0.0
            )
            keywords = response.choices[0].text.strip().lower()
            logger.debug(f"GPT extracted keywords: '{keywords}'")
            
            # Clean and validate
            keywords = re.sub(r'[^\w-]', '', keywords).strip()
            
            if keywords and keywords != 'none' and len(keywords) > 2:
                return keywords
            
            return None
        except Exception as e:
            logger.error(f"Error extracting keywords with GPT: {e}", exc_info=True)
            return None

    async def fetch_products(self, shopify_access_token: str, shopify_store_url: str, query: Optional[str] = None, sort_key: str = "RELEVANCE") -> Dict[str, Any]:
        """
        Fetch product details from Shopify using GraphQL.
        If a query string is provided, it will filter products.
        """
        graphql_url = f"https://{shopify_store_url}/admin/api/2024-01/graphql.json"
        headers = {
            'X-Shopify-Access-Token': shopify_access_token,
            'Content-Type': 'application/json',
        }
        
        # Build GraphQL query with sorting
        if query:
            graphql_query = f"""
            query getProducts($query: String) {{
                products(first: 8, query: $query, sortKey: TITLE) {{
                    edges {{
                        node {{
                            id
                            title
                            description
                            onlineStoreUrl
                            priceRange {{
                                minVariantPrice {{
                                    amount
                                    currencyCode
                                }}
                            }}
                            images(first: 1) {{
                                edges {{
                                    node {{
                                        src
                                    }}
                                }}
                            }}
                        }}
                    }}
                }}
            }}
            """
            variables = {"query": query}
        else:
            # Fetch products when no query (using TITLE sort as it's always valid)
            graphql_query = f"""
            query getProducts {{
                products(first: 8, sortKey: TITLE) {{
                    edges {{
                        node {{
                            id
                            title
                            description
                            onlineStoreUrl
                            priceRange {{
                                minVariantPrice {{
                                    amount
                                    currencyCode
                                }}
                            }}
                            images(first: 1) {{
                                edges {{
                                    node {{
                                        src
                                    }}
                                }}
                            }}
                        }}
                    }}
                }}
            }}
            """
            variables = {}
            
        async with aiohttp.ClientSession() as session:
            async with session.post(
                graphql_url,
                headers=headers,
                json={"query": graphql_query, "variables": variables}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"📡 Shopify GraphQL Response Status: 200")
                    
                    if "errors" in data:
                        logger.error(f"❌ GraphQL Errors: {data['errors']}")
                        return {"errors": data["errors"]}
                    
                    products = data.get("data", {}).get("products", {}).get("edges", [])
                    logger.info(f"✅ Successfully fetched {len(products)} products from Shopify")
                    
                    for i, edge in enumerate(products[:3]):  # Log first 3 products
                        node = edge.get("node", {})
                        title = node.get("title", "No title")
                        price = node.get("priceRange", {}).get("minVariantPrice", {}).get("amount", "No price")
                        logger.info(f"  Product {i+1}: {title} - ${price}")
                    
                    return data
                else:
                    error_text = await response.text()
                    logger.error(f"❌ HTTP Error {response.status}: {error_text}")
                    return {"error": f"Failed to fetch products: HTTP {response.status}"}

    async def get_recommendations(self, message: str, shopify_access_token: str, shopify_store_url: str) -> Dict[str, Any]:
        """
        Generate product recommendations based on the message by fetching from Shopify.
        Includes fuzzy matching and fallback to popular products.
        """
        logger.info(f"🔍 RecommendationAgent.get_recommendations() called with message: '{message}'")
        logger.info(f"🏪 Shop: {shopify_store_url}, Token present: {'Yes' if shopify_access_token else 'No'}")
        
        # Use GPT to extract relevant keywords from the message
        search_query = await self._extract_keywords_with_gpt(message)
        logger.info(f"🔎 Extracted search query for Shopify: '{search_query}'")

        # If no specific product mentioned, get popular products directly
        if not search_query:
            logger.info("📊 No specific product mentioned, fetching popular products")
            shopify_response = await self.fetch_products(shopify_access_token, shopify_store_url, query=None)
            search_query = "popular items"
        else:
            # Try the extracted query first
            logger.info(f"🎯 Fetching products for query: '{search_query}'")
            shopify_response = await self.fetch_products(shopify_access_token, shopify_store_url, query=search_query)
        
        if "errors" in shopify_response:
            error_message = shopify_response['errors'][0]['message'] if shopify_response['errors'] else "Unknown Shopify API error."
            logger.error(f"Shopify API error in recommendations: {error_message}")
            
            # Fallback to popular products on error
            logger.info("Fetching popular products as fallback due to API error")
            shopify_response = await self.fetch_products(shopify_access_token, shopify_store_url, query=None)
            search_query = "popular items"

        products = shopify_response.get("data", {}).get("products", {}).get("edges", [])
        
        # If no products found with specific query, try broader terms or popular products
        if not products and search_query and search_query != "popular items":
            logger.info(f"No products found for '{search_query}', trying broader search")
            
            # Try partial/broader search terms
            broader_terms = self._get_broader_search_terms(search_query)
            for term in broader_terms:
                logger.info(f"Trying broader term: {term}")
                shopify_response = await self.fetch_products(shopify_access_token, shopify_store_url, query=term)
                products = shopify_response.get("data", {}).get("products", {}).get("edges", [])
                if products:
                    search_query = term  # Update for response message
                    break
            
            # If still no products, get popular items
            if not products:
                logger.info("No products found with broader terms, fetching popular products")
                shopify_response = await self.fetch_products(shopify_access_token, shopify_store_url, query=None)
                products = shopify_response.get("data", {}).get("products", {}).get("edges", [])
                search_query = "popular items"
        
        recommendations = []
        logger.info(f"📦 Processing {len(products)} products from Shopify response")
        
        for i, item in enumerate(products):
            node = item.get("node", {})
            if node:
                product_title = node.get("title")
                product_price = node.get("priceRange", {}).get("minVariantPrice", {}).get("amount", "N/A")
                logger.info(f"  Product #{i+1}: '{product_title}' - ${product_price}")
                recommendations.append({
                    "id": node.get("id"),
                    "name": product_title,
                    "price": product_price,
                    "currency": node.get("priceRange", {}).get("minVariantPrice", {}).get("currencyCode", ""),
                    "description": node.get("description"),
                    "url": node.get("onlineStoreUrl"),
                    "image": node.get("images", {}).get("edges", [{}])[0].get("node", {}).get("src")
                })
        
        logger.info(f"✅ Created {len(recommendations)} recommendation objects")
        
        if not recommendations:
            logger.warning("❌ No recommendations found from Shopify even with fallbacks.")
            return {
                "recommendations": [],
                "confidence": 0.3,
                "reason": "I'd love to help you find something great! Could you tell me what type of product you're looking for? For example: jeans, shirts, shoes, or any specific brand?"
            }

        # Determine response message based on what was found
        if search_query == "popular items":
            reason = "Here are some popular items from our store that I think you'll love:"
        elif search_query:
            reason = f"Here are some great {search_query} options I found for you:"
        else:
            reason = "Here are some recommended products:"

        result = {
            "recommendations": recommendations,
            "confidence": 0.9,
            "reason": reason,
            "search_term": search_query
        }
        
        logger.info(f"🎉 RecommendationAgent returning: {len(recommendations)} products, reason: '{reason}'")
        return result

    def _get_broader_search_terms(self, query: str) -> List[str]:
        """
        Generate broader search terms for fuzzy matching.
        """
        if not query:
            return []
            
        broader_terms = []
        query_lower = query.lower()
        
        # Common product category mappings
        category_map = {
            "jean": ["jeans", "denim", "pants"],
            "jeans": ["jean", "denim", "pants"],
            "shirt": ["shirts", "top", "tee"],
            "t-shirt": ["tshirt", "tee", "shirt"],
            "tshirt": ["t-shirt", "tee", "shirt"],
            "shoe": ["shoes", "footwear", "sneaker"],
            "shoes": ["shoe", "footwear", "sneaker"],
            "dress": ["dresses", "clothing"],
            "pant": ["pants", "trousers", "bottoms"],
            "pants": ["pant", "trousers", "bottoms"],
            "jacket": ["jackets", "outerwear", "coat"],
            "sweater": ["sweaters", "jumper", "pullover"],
            "skirt": ["skirts", "bottoms"],
            "bag": ["bags", "handbag", "purse"],
            "hat": ["hats", "cap", "beanie"],
            "watch": ["watches", "timepiece"],
            "ring": ["rings", "jewelry"],
            "necklace": ["necklaces", "jewelry"],
        }
        
        # Add broader terms for the query
        if query_lower in category_map:
            broader_terms.extend(category_map[query_lower])
        
        # Add partial matches (remove common suffixes/prefixes)
        if len(query) > 3:
            broader_terms.append(query[:3])  # First 3 characters
            if query.endswith('s'):
                broader_terms.append(query[:-1])  # Remove plural 's'
            if query.endswith('ing'):
                broader_terms.append(query[:-3])  # Remove 'ing'
        
        # Remove duplicates and return
        return list(set(broader_terms)) 
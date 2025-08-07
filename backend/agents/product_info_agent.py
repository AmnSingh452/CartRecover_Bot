import logging
import os
from dotenv import load_dotenv
import aiohttp
import json
from typing import Dict, Any, Optional, List
import re
import openai

logger = logging.getLogger(__name__)

load_dotenv()
logger.info("Environment variables loaded for ProductInfoAgent")

class ProductInfoAgent:
    """
    Handles queries related to product information like stock, price, and return policy.
    """
    def __init__(self):
        import openai
        from dotenv import load_dotenv
        import os
        load_dotenv()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set for ProductInfoAgent.")
        self.openai_client = openai.AsyncOpenAI(api_key=self.openai_api_key)

    async def _extract_product_name_with_gpt(self, message: str) -> Optional[str]:
        """
        Uses GPT to extract the main product name from the user's message.
        Enhanced to handle variations and partial spellings.
        """
        prompt = f"""Extract the main product keywords or name from the following user query.
        Be flexible with spelling variations and return the most likely product term.
        If asking about a specific product, return the product name/category.
        If no clear product is mentioned, return 'NONE'.

        Examples:
        User: 'How much is the Levi's 501 jeans?'
        Output: Levi's 501 jeans

        User: 'Is the iPhone 15 in stock?'
        Output: iPhone 15

        User: 'Tell me about the Short-sleeve tshirt.'
        Output: Short-sleeve tshirt

        User: 'What about jens prices?'
        Output: jeans

        User: 'Do you have nike shoos?'
        Output: nike shoes

        User: 'tshrt info please'
        Output: t-shirt

        User: 'What is your return policy?'
        Output: NONE

        User: '{message}'
        Output:"""

        try:
            response = await self.openai_client.completions.create(
                model="gpt-3.5-turbo-instruct",
                prompt=prompt,
                max_tokens=20,
                n=1,
                stop=['\n\n'],
                temperature=0.1  # Slightly higher for flexibility
            )
            extracted_name = response.choices[0].text.strip()
            logger.debug(f"GPT extracted product name: {extracted_name}")
            
            # Clean up the extracted name
            extracted_name = re.sub(r'[^\w\s-]', '', extracted_name).strip()
            
            if extracted_name.lower() == 'none' or not extracted_name:
                return None
            return extracted_name
        except Exception as e:
            logger.error(f"Error extracting product name with GPT: {e}", exc_info=True)
            return None

    async def _extract_product_name(self, message: str) -> Optional[str]:
        """
        Extracts a potential product name from the user's message using GPT as primary, with a basic fallback.
        """
        gpt_extracted_name = await self._extract_product_name_with_gpt(message)
        if gpt_extracted_name:
            return gpt_extracted_name
        
        # Fallback to very basic extraction if GPT fails or doesn't find a product
        product_keywords = []
        words = message.split()
        for i, word in enumerate(words):
            if word.istitle() and len(word) > 2:
                name_candidate = word
                for j in range(i + 1, min(i + 3, len(words))):
                    if words[j].istitle() or words[j].islower() and len(words[j]) > 2:
                        name_candidate += f" {words[j]}"
                    else:
                        break
                product_keywords.append(name_candidate)
        return product_keywords[0] if product_keywords else None

    async def fetch_product_details(self, product_query: str, shopify_access_token: str, shopify_store_url: str) -> Dict[str, Any]:
        """
        Fetch product details from Shopify using GraphQL.
        Enhanced to try multiple products if available.
        """
        graphql_url = f"https://{shopify_store_url}/admin/api/2024-01/graphql.json"
        headers = {
            'X-Shopify-Access-Token': shopify_access_token,
            'Content-Type': 'application/json',
        }
        query = """
        query getProductDetails($query: String!) {
            products(first: 5, query: $query) {
                edges {
                    node {
                        id
                        title
                        totalInventory
                        priceRange {
                            minVariantPrice {
                                amount
                                currencyCode
                            }
                        }
                        description
                        onlineStoreUrl
                    }
                }
            }
        }
        """
        variables = {
            "query": product_query
        }
        logger.debug(f"Shopify product details query variables: {variables}")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                graphql_url,
                headers=headers,
                json={"query": query, "variables": variables}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"Raw Shopify product details response: {json.dumps(data, indent=2)}")
                    return data
                else:
                    error_text = await response.text()
                    logger.error(f"Error fetching product details: {error_text}")
                    return {"error": f"Failed to fetch product details: {error_text}"}

    def _get_broader_search_terms(self, query: str) -> List[str]:
        """
        Generate broader search terms for fuzzy matching.
        """
        if not query:
            return []
            
        broader_terms = []
        query_lower = query.lower()
        
        # Common product category mappings for misspellings
        category_map = {
            "jean": ["jeans", "denim", "pants"],
            "jeans": ["jean", "denim", "pants"],
            "jens": ["jeans", "jean", "denim"],
            "shirt": ["shirts", "top", "tee"],
            "t-shirt": ["tshirt", "tee", "shirt"],
            "tshirt": ["t-shirt", "tee", "shirt"],
            "tshrt": ["t-shirt", "tshirt", "shirt"],
            "shoe": ["shoes", "footwear", "sneaker"],
            "shoes": ["shoe", "footwear", "sneaker"],
            "shoos": ["shoes", "shoe", "footwear"],
            "shoo": ["shoe", "shoes", "footwear"],
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
        
        # Check if any word in the query matches our category map
        words = query_lower.split()
        for word in words:
            if word in category_map:
                broader_terms.extend(category_map[word])
        
        # Add partial matches (remove common suffixes/prefixes)
        if len(query) > 3:
            broader_terms.append(query[:3])  # First 3 characters
            if query.endswith('s'):
                broader_terms.append(query[:-1])  # Remove plural 's'
            if query.endswith('ing'):
                broader_terms.append(query[:-3])  # Remove 'ing'
        
        # Remove duplicates and original query
        broader_terms = [term for term in set(broader_terms) if term != query_lower]
        return broader_terms

    async def process_product_info_request(self, message: str, intent: str, shopify_access_token: str, shopify_store_url: str) -> Dict[str, Any]:
        product_name = await self._extract_product_name(message)
        logger.info(f"Product name extracted for ProductInfoAgent: {product_name}")
        
        if not product_name:
            return {
                "response": "I couldn't identify a specific product in your query. Could you please specify the product name?",
                "confidence": 0.5,
                "agent_used": "product_info_agent"
            }

        # Try to find product with exact match first
        product_details_response = await self.fetch_product_details(product_name, shopify_access_token, shopify_store_url)
        
        if "errors" in product_details_response:
            error_message = product_details_response['errors'][0]['message'] if product_details_response['errors'] else "Unknown Shopify API error."
            logger.error(f"Shopify API error in ProductInfoAgent: {error_message}")
            return {
                "response": f"Sorry, I encountered an error while fetching product details: {error_message}",
                "confidence": 0.0,
                "agent_used": "product_info_agent",
                "error": error_message
            }

        products = product_details_response.get("data", {}).get("products", {}).get("edges", [])
        found_product_name = product_name
        
        # If no products found, try broader search terms (fuzzy matching)
        if not products:
            logger.info(f"No exact match found for '{product_name}', trying broader search")
            broader_terms = self._get_broader_search_terms(product_name)
            
            for term in broader_terms:
                logger.info(f"Trying broader term: {term}")
                product_details_response = await self.fetch_product_details(term, shopify_access_token, shopify_store_url)
                products = product_details_response.get("data", {}).get("products", {}).get("edges", [])
                if products:
                    found_product_name = term
                    logger.info(f"Found products using broader term: {term}")
                    break
        
        if not products:
            return {
                "response": f"I couldn't find any product matching '{product_name}'. Could you please check the spelling or try a different product name?",
                "confidence": 0.6,
                "agent_used": "product_info_agent"
            }

        # Use the first (most relevant) product found
        product = products[0]["node"]
        response_message = ""
        
        if intent == "product_price":
            price = product.get("priceRange", {}).get("minVariantPrice", {})
            amount_str = price.get("amount", "N/A")
            currency = price.get("currencyCode", "")
            try:
                amount = float(amount_str)
                formatted_amount = f"{amount/100:.2f}" if amount_str != "N/A" else "N/A"
            except ValueError:
                formatted_amount = "N/A"
            product_title = product.get('title', 'this product').strip().replace('"', '')
            response_message = f"The price of {product_title} is {formatted_amount} {currency}."
            
        elif intent == "product_stock":
            inventory = product.get("totalInventory", "N/A")
            product_title = product.get('title', 'this product').strip().replace('"', '')
            response_message = f"There are {inventory} units of {product_title} currently in stock."
            
        elif intent == "return_policy":
            product_title = product.get('title', 'this product').strip().replace('"', '')
            response_message = f"Our return policy for {product_title} and most items allows returns within 30 days of purchase. For detailed information, please visit our Returns & Exchanges page on our website or contact customer support."

        # Add a note if we used fuzzy matching
        if found_product_name != product_name:
            response_message += f" (I found this by searching for '{found_product_name}' based on your query about '{product_name}')"

        return {
            "response": response_message,
            "confidence": 0.9,
            "agent_used": "product_info_agent",
            "product_details": product,
            "search_term_used": found_product_name
        } 
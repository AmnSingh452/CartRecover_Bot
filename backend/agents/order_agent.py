import asyncio
import logging
import json
import sys
import os
from dotenv import load_dotenv
import aiohttp
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load and check environment variables
load_dotenv()
logger.info("Environment variables loaded")
logger.info(f"SHOPIFY_ACCESS_TOKEN exists: {'Yes' if os.getenv('SHOPIFY_ACCESS_TOKEN') else 'No'}")
logger.info(f"SHOPIFY_STORE_URL exists: {'Yes' if os.getenv('SHOPIFY_STORE_URL') else 'No'}")
logger.info(f"OPENAI_API_KEY exists: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")

class OrderAgent:
    """
    Handles order-related queries and processing.
    """
    
    def __init__(self):
        pass  # No need to load or check credentials here anymore

    def extract_order_number(self, message: str) -> Optional[str]:
        """Extract order number from user message with improved patterns."""
        import re
        
        # Multiple patterns to match different order number formats
        patterns = [
            r'#(\d{3,})',           # #1001, #12345
            r'order\s*#?(\d{3,})',  # order 1001, order #1001
            r'number\s*#?(\d{3,})', # number 1001, number #1001
            r'\b(\d{4,})\b',        # standalone 4+ digit numbers
            r'#?(\d{3,})',          # fallback for any 3+ digit numbers
        ]
        
        logger.debug(f"🔍 Extracting order number from: '{message}'")
        
        for i, pattern in enumerate(patterns, 1):
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                order_number = match.group(1)
                logger.info(f"✅ Found order number '{order_number}' using pattern {i}: {pattern}")
                return order_number
        
        logger.warning(f"❌ No order number found in message: '{message}'")
        return None

    async def fetch_order_details(self, order_number: str, shopify_access_token: str, shopify_store_url: str) -> Dict[str, Any]:
        """Fetch order details from Shopify using GraphQL with multiple query formats."""
        graphql_url = f"https://{shopify_store_url}/admin/api/2024-01/graphql.json"
        headers = {
            'X-Shopify-Access-Token': shopify_access_token,
            'Content-Type': 'application/json',
        }
        
        query = """
        query getOrder($query: String!) {
            orders(first: 1, query: $query) {
                edges {
                    node {
                        id
                        name
                        createdAt
                        displayFulfillmentStatus
                        displayFinancialStatus
                        totalPriceSet {
                            shopMoney {
                                amount
                                currencyCode
                            }
                        }
                        lineItems(first: 10) {
                            edges {
                                node {
                                    title
                                    quantity
                                }
                            }
                        }
                        customer {
                            firstName
                            lastName
                            email
                        }
                        shippingAddress {
                            address1
                            city
                            province
                            zip
                            country
                        }
                    }
                }
            }
        }
        """
        
        # Try multiple query formats to find the order
        query_formats = [
            f"name:#{order_number}",          # #1001
            f"name:\"{order_number}\"",       # "1001"
            f"name:{order_number}",           # 1001
            f"order_number:{order_number}",   # order_number:1001
            f"name:\"#{order_number}\"",      # "#1001"
        ]
        
        logger.info(f"🔍 Searching for order: {order_number}")
        
        for i, query_format in enumerate(query_formats, 1):
            logger.info(f"📝 Attempt {i}/5 - Trying query format: {query_format}")
            
            variables = {"query": query_format}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    graphql_url,
                    headers=headers,
                    json={"query": query, "variables": variables}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Check for GraphQL errors
                        if "errors" in data:
                            logger.warning(f"❌ GraphQL errors with '{query_format}': {data['errors']}")
                            continue
                        
                        # Check if we found orders
                        orders = data.get("data", {}).get("orders", {}).get("edges", [])
                        if orders:
                            logger.info(f"✅ Found order #{order_number} with query format: {query_format}")
                            logger.debug(f"Order details: {json.dumps(data, indent=2)}")
                            return data
                        else:
                            logger.info(f"❌ No orders found with query: {query_format}")
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ HTTP error {response.status} with query '{query_format}': {error_text}")
        
        # If no query format worked, log final failure
        logger.error(f"❌ Order #{order_number} not found with any query format")
        logger.info("💡 Suggestion: Check if the order exists in your Shopify admin and verify the order number")
        
        return {"error": f"Order #{order_number} not found. Please check the order number and try again."}

    async def process_order_request(self, message: str, shopify_access_token: str, shopify_store_url: str) -> Dict[str, Any]:
        """
        Process an order-related request.
        
        Args:
            message: The user's message
            shopify_access_token: Shopify access token
            shopify_store_url: Shopify store URL
            
        Returns:
            Dict containing order processing results
        """
        try:
            logger.info(f"🔍 Processing order request: {message}")
            
            order_number = self.extract_order_number(message)
            if not order_number:
                logger.warning("❌ No order number found in message")
                return {
                    "success": False,
                    "message": "Could not find an order number in your message. Please provide an order number (e.g., #1001, 1001)."
                }
            
            logger.info(f"📝 Extracted order number: {order_number}")
            
            order_details = await self.fetch_order_details(order_number, shopify_access_token, shopify_store_url)
            
            # Check if we got a custom error from our fetch method
            if "error" in order_details and "data" not in order_details:
                logger.error(f"❌ Custom error: {order_details['error']}")
                return {
                    "success": False,
                    "message": order_details["error"]
                }
            
            # Check if we got GraphQL errors in the response
            if "errors" in order_details:
                logger.error(f"❌ GraphQL errors: {order_details['errors']}")
                return {
                    "success": False,
                    "message": f"Error fetching order details: {json.dumps(order_details['errors'])}"
                }
            
            # Check if we found any orders
            orders = order_details.get("data", {}).get("orders", {}).get("edges", [])
            if not orders:
                logger.warning(f"❌ No orders found for number: {order_number}")
                return {
                    "success": False,
                    "message": f"No order found with number #{order_number}. Please check the order number and try again."
                }
            
            order_node = orders[0]["node"]
            logger.info(f"✅ Successfully found order: {order_node.get('name', 'Unknown')}")
            
            return {
                "success": True,
                "order_number": order_number,
                "details": order_node
            }
            
        except Exception as e:
            logger.error(f"❌ Unexpected error processing order request: {str(e)}")
            return {
                "success": False,
                "message": f"An unexpected error occurred while processing your request. Please try again."
            } 
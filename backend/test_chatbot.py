#!/usr/bin/env python3
"""
Comprehensive test script for the enhanced Shopify chatbot system.
Tests fuzzy matching, agent coordination, and various user scenarios.
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, List
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Import our agents
from agents.agent_coordinator import AgentCoordinator
from session_manager import SessionManager

class ChatbotTester:
    """
    Test suite for the enhanced chatbot system.
    """
    
    def __init__(self):
        self.coordinator = AgentCoordinator()
        self.session_manager = SessionManager()
        
        # Test shop configuration (you may need to adjust these)
        self.test_shop_domain = os.getenv("TEST_SHOP_DOMAIN", "4ja0wp-y1.myshopify.com")
        self.test_access_token = os.getenv("SHOPIFY_ACCESS_TOKEN")
        
        # Test customer info
        self.test_customer = {
            "name": "Test Customer",
            "email": "test@example.com",
            "id": "test_123"
        }
        
        self.test_history = []
        
    def print_separator(self, title: str):
        """Print a nice separator for test sections."""
        print("\n" + "="*60)
        print(f"🧪 {title}")
        print("="*60)
    
    def print_test_result(self, query: str, response: Dict[str, Any]):
        """Print formatted test results."""
        print(f"\n📝 Query: '{query}'")
        print(f"🤖 Agent Used: {response.get('agent_used', 'unknown')}")
        print(f"📊 Confidence: {response.get('confidence', 'N/A')}")
        
        if 'search_term_used' in response:
            print(f"🔍 Search Term Used: {response['search_term_used']}")
        
        if 'processing_time' in response:
            print(f"⏱️ Processing Time: {response['processing_time']:.2f}s")
            
        print(f"💬 Response: {response.get('response', 'No response')[:200]}...")
        
        if 'recommendations' in response and response['recommendations']:
            print(f"🛍️ Found {len(response['recommendations'])} recommendations")
            for i, rec in enumerate(response['recommendations'][:3], 1):
                print(f"   {i}. {rec.get('name', 'Unknown')} - {rec.get('price', 'N/A')} {rec.get('currency', '')}")
        
        if 'error' in response:
            print(f"❌ Error: {response['error']}")
        
        print("-" * 40)

    async def test_fuzzy_matching_recommendations(self):
        """Test fuzzy matching in recommendation agent."""
        self.print_separator("FUZZY MATCHING RECOMMENDATIONS")
        
        test_queries = [
            "Show me some jens",  # jens -> jeans
            "I need nike shoos",  # shoos -> shoes
            "Do you have tshrt?",  # tshrt -> t-shirt
            "Looking for denims",  # denims -> jeans/denim
            "Show me some jacets",  # jacets -> jackets
            "I want a watsh",  # watsh -> watch
            "Any good jevelry?",  # jevelry -> jewelry
            "Show me popular items",  # Should show popular products
        ]
        
        for query in test_queries:
            try:
                response = await self.coordinator.process_message(
                    message=query,
                    history=self.test_history,
                    customer_info=self.test_customer,
                    access_token=self.test_access_token,
                    shop_domain=self.test_shop_domain
                )
                self.print_test_result(query, response)
                
                # Add to history for context
                self.test_history.append({
                    "user": query,
                    "assistant": response.get("response", "")
                })
                
            except Exception as e:
                print(f"❌ Error testing query '{query}': {str(e)}")

    async def test_fuzzy_matching_product_info(self):
        """Test fuzzy matching in product info agent."""
        self.print_separator("FUZZY MATCHING PRODUCT INFO")
        
        test_queries = [
            "What's the price of jens?",  # jens -> jeans
            "How much do nike shoos cost?",  # shoos -> shoes  
            "Is the tshrt in stock?",  # tshrt -> t-shirt
            "Tell me about the watsh price",  # watsh -> watch
            "What's the cost of denims?",  # denims -> jeans
            "Are jacets available?",  # jacets -> jackets
        ]
        
        for query in test_queries:
            try:
                response = await self.coordinator.process_message(
                    message=query,
                    history=self.test_history,
                    customer_info=self.test_customer,
                    access_token=self.test_access_token,
                    shop_domain=self.test_shop_domain
                )
                self.print_test_result(query, response)
                
            except Exception as e:
                print(f"❌ Error testing query '{query}': {str(e)}")

    async def test_exact_matching(self):
        """Test that exact matching still works perfectly."""
        self.print_separator("EXACT MATCHING VALIDATION")
        
        test_queries = [
            "Show me some jeans",
            "I need shoes",
            "Do you have t-shirts?",
            "Looking for jackets",
            "What's the price of jeans?",
            "Are shoes in stock?",
        ]
        
        for query in test_queries:
            try:
                response = await self.coordinator.process_message(
                    message=query,
                    history=self.test_history,
                    customer_info=self.test_customer,
                    access_token=self.test_access_token,
                    shop_domain=self.test_shop_domain
                )
                self.print_test_result(query, response)
                
            except Exception as e:
                print(f"❌ Error testing query '{query}': {str(e)}")

    async def test_other_intents(self):
        """Test other intents like orders, size charts, etc."""
        self.print_separator("OTHER INTENT TESTING")
        
        test_queries = [
            "What's your return policy?",
            "Can I see the size chart?",
            "Tell me about order #1001",  # This will likely fail without real order
            "Hello, how are you?",  # General query
            "What can you help me with?",  # General query
        ]
        
        for query in test_queries:
            try:
                response = await self.coordinator.process_message(
                    message=query,
                    history=self.test_history,
                    customer_info=self.test_customer,
                    access_token=self.test_access_token,
                    shop_domain=self.test_shop_domain
                )
                self.print_test_result(query, response)
                
            except Exception as e:
                print(f"❌ Error testing query '{query}': {str(e)}")

    async def test_edge_cases(self):
        """Test edge cases and error scenarios."""
        self.print_separator("EDGE CASES & ERROR HANDLING")
        
        test_queries = [
            "",  # Empty string
            "xyz abc def nonsense",  # Complete nonsense
            "Show me some zzzzzzz",  # Non-existent product
            "What's the price of qwertyuiop?",  # Non-existent product
            "🤖🔥💯",  # Only emojis
        ]
        
        for query in test_queries:
            try:
                response = await self.coordinator.process_message(
                    message=query,
                    history=self.test_history,
                    customer_info=self.test_customer,
                    access_token=self.test_access_token,
                    shop_domain=self.test_shop_domain
                )
                self.print_test_result(query, response)
                
            except Exception as e:
                print(f"❌ Error testing query '{query}': {str(e)}")

    async def test_session_management(self):
        """Test session management and context."""
        self.print_separator("SESSION MANAGEMENT")
        
        try:
            # Create a session
            session_id = self.session_manager.create_session(
                shop_domain=self.test_shop_domain
            )
            
            print(f"✅ Created session: {session_id}")
            
            # Test conversation flow
            queries = [
                "Hello!",
                "Show me some jens",  # Fuzzy match
                "What about the price of those jens?",  # Context reference
            ]
            
            conversation_history = []
            for query in queries:
                response = await self.coordinator.process_message(
                    message=query,
                    history=conversation_history,
                    customer_info=self.test_customer,
                    access_token=self.test_access_token,
                    shop_domain=self.test_shop_domain
                )
                
                self.print_test_result(query, response)
                conversation_history.append({
                    "user": query,
                    "assistant": response.get("response", "")
                })
                
        except Exception as e:
            print(f"❌ Error in session management test: {str(e)}")

    async def run_all_tests(self):
        """Run the complete test suite."""
        print("🚀 Starting Comprehensive Chatbot Test Suite")
        print(f"🏪 Testing with shop: {self.test_shop_domain}")
        print(f"🔑 Access token configured: {'Yes' if self.test_access_token else 'No'}")
        
        if not self.test_access_token:
            print("⚠️ Warning: No Shopify access token found. Some tests may fail.")
            print("   Set SHOPIFY_ACCESS_TOKEN in your .env file for full testing.")
        
        # Run all test suites
        test_suites = [
            self.test_fuzzy_matching_recommendations,
            self.test_fuzzy_matching_product_info,
            self.test_exact_matching,
            self.test_other_intents,
            self.test_edge_cases,
            self.test_session_management,
        ]
        
        for test_suite in test_suites:
            try:
                await test_suite()
                await asyncio.sleep(1)  # Brief pause between test suites
            except Exception as e:
                print(f"❌ Test suite failed: {str(e)}")
        
        print(self.print_separator("TEST SUITE COMPLETE"))
        print("🎉 All tests completed! Check the results above.")
        print("💡 Look for fuzzy matching indicators like 'Search Term Used' in the results.")

async def main():
    """Main function to run the test suite."""
    tester = ChatbotTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())

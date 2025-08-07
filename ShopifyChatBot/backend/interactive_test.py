#!/usr/bin/env python3
"""
Interactive chatbot tester - chat with your enhanced chatbot in real-time!
"""

import asyncio
import os
import logging
from dotenv import load_dotenv
from agents.agent_coordinator import AgentCoordinator

# Configure logging
logging.basicConfig(level=logging.WARNING)  # Reduce noise for interactive use

# Load environment variables
load_dotenv()

class InteractiveChatbot:
    """
    Interactive chatbot for manual testing.
    """
    
    def __init__(self):
        self.coordinator = AgentCoordinator()
        self.shop_domain = os.getenv("TEST_SHOP_DOMAIN", "4ja0wp-y1.myshopify.com")
        self.access_token = os.getenv("SHOPIFY_ACCESS_TOKEN")
        self.customer_info = {
            "name": "Test User",
            "email": "test@example.com",
            "id": "interactive_test"
        }
        self.conversation_history = []
        
    def print_welcome(self):
        """Print welcome message and instructions."""
        print("🤖 Enhanced Shopify Chatbot - Interactive Tester")
        print("=" * 50)
        print(f"🏪 Shop: {self.shop_domain}")
        print(f"🔑 Access Token: {'✅ Configured' if self.access_token else '❌ Missing'}")
        print("\n📝 Try these test queries:")
        print("   • 'Show me some jens' (fuzzy: jens → jeans)")
        print("   • 'I need nike shoos' (fuzzy: shoos → shoes)")
        print("   • 'What's the price of tshrt?' (fuzzy: tshrt → t-shirt)")
        print("   • 'Show me some jackets' (exact match)")
        print("   • 'What's your return policy?'")
        print("   • 'Can I see the size chart?'")
        print("   • 'Hello' (general chat)")
        print("\n💡 Type 'quit' or 'exit' to stop")
        print("💡 Type 'clear' to clear conversation history")
        print("💡 Type 'help' to see this message again")
        print("-" * 50)
        
    def print_response(self, query: str, response: dict):
        """Format and print the chatbot response."""
        print(f"\n🤖 Response:")
        print(f"   Agent: {response.get('agent_used', 'unknown')}")
        print(f"   Confidence: {response.get('confidence', 'N/A')}")
        
        if 'search_term_used' in response:
            print(f"   🔍 Search Term: {response['search_term_used']}")
            
        if 'processing_time' in response:
            print(f"   ⏱️ Time: {response['processing_time']:.2f}s")
            
        print(f"\n💬 {response.get('response', 'No response')}")
        
        if 'recommendations' in response and response['recommendations']:
            print(f"\n🛍️ Found {len(response['recommendations'])} recommendations:")
            for i, rec in enumerate(response['recommendations'][:5], 1):
                print(f"   {i}. {rec.get('name', 'Unknown')} - {rec.get('price', 'N/A')} {rec.get('currency', '')}")
                
        if 'error' in response:
            print(f"\n❌ Error: {response['error']}")
            
        print("-" * 50)
        
    async def chat_loop(self):
        """Main interactive chat loop."""
        self.print_welcome()
        
        while True:
            try:
                # Get user input
                user_input = input("\n👤 You: ").strip()
                
                # Handle special commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                    
                elif user_input.lower() == 'clear':
                    self.conversation_history.clear()
                    print("🧹 Conversation history cleared!")
                    continue
                    
                elif user_input.lower() == 'help':
                    self.print_welcome()
                    continue
                    
                elif not user_input:
                    print("🤔 Please enter a message!")
                    continue
                
                # Process the message
                print("⏳ Processing...")
                response = await self.coordinator.process_message(
                    message=user_input,
                    history=self.conversation_history,
                    customer_info=self.customer_info,
                    access_token=self.access_token,
                    shop_domain=self.shop_domain
                )
                
                # Display the response
                self.print_response(user_input, response)
                
                # Add to conversation history
                self.conversation_history.append({
                    "user": user_input,
                    "assistant": response.get("response", "")
                })
                
                # Keep history manageable
                if len(self.conversation_history) > 10:
                    self.conversation_history = self.conversation_history[-10:]
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
                print("🔄 Try again or type 'quit' to exit")

async def main():
    """Main function."""
    chatbot = InteractiveChatbot()
    await chatbot.chat_loop()

if __name__ == "__main__":
    asyncio.run(main())

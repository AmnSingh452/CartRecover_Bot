import asyncio
from agents.agent_coordinator import AgentCoordinator
import os
import logging

# Set logging to see what's happening
logging.basicConfig(level=logging.INFO)

async def test_enhanced():
    print("🚀 Starting enhanced chatbot test...")
    
    try:
        coordinator = AgentCoordinator()
        print("✅ AgentCoordinator initialized")
        
        test_queries = [
            'Show me some jens',  # Should be recommendation
            'What price of tshrt?',  # Should be product_price
            'Looking for nike shoos',  # Should be recommendation
        ]
        
        for query in test_queries:
            print(f'\n🔍 Testing: {query}')
            try:
                response = await coordinator.process_message(
                    message=query,
                    history=[],
                    customer_info={'name': 'Test', 'email': 'test@test.com'},
                    access_token=os.getenv('SHOPIFY_ACCESS_TOKEN'),
                    shop_domain='4ja0wp-y1.myshopify.com'
                )
                print(f'  Agent: {response.get("agent_used")}')
                print(f'  Confidence: {response.get("confidence")}')
                if 'search_term_used' in response:
                    print(f'  Search term: {response["search_term_used"]}')
                print(f'  Response: {response.get("response")[:80]}...')
            except Exception as e:
                print(f'  Error: {str(e)}')
                import traceback
                traceback.print_exc()
                
    except Exception as e:
        print(f"❌ Error initializing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_enhanced())

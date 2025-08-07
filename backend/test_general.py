import asyncio
from agents.agent_coordinator import AgentCoordinator
import os

async def test_general_recommendation():
    print("🧪 Testing general recommendations...")
    coordinator = AgentCoordinator()
    
    query = "Can you recommend something?"
    print(f"Query: {query}")
    
    try:
        response = await coordinator.process_message(
            message=query,
            history=[],
            customer_info={'name': 'Test', 'email': 'test@test.com'},
            access_token=os.getenv('SHOPIFY_ACCESS_TOKEN'),
            shop_domain='4ja0wp-y1.myshopify.com'
        )
        
        print(f"Agent: {response.get('agent_used')}")
        print(f"Confidence: {response.get('confidence')}")
        
        if 'search_term_used' in response:
            print(f"Search term: {response['search_term_used']}")
            
        if 'recommendations' in response:
            print(f"Found {len(response['recommendations'])} products")
            for i, rec in enumerate(response['recommendations'][:3], 1):
                print(f"  {i}. {rec.get('name', 'Unknown')}")
                
        print(f"Response: {response.get('response')}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_general_recommendation())

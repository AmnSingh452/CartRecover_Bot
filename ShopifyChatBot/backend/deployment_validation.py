#!/usr/bin/env python3
"""
Final deployment validation script for the enhanced Shopify chatbot.
Verifies all critical features are working before deployment.
"""

import asyncio
import logging
from agents.agent_coordinator import AgentCoordinator

# Configure logging
logging.basicConfig(level=logging.WARNING)  # Reduce noise

async def validate_deployment():
    """
    Validate all critical features before deployment.
    """
    print("🚀 SHOPIFY CHATBOT - DEPLOYMENT VALIDATION")
    print("=" * 50)
    
    coordinator = AgentCoordinator()
    test_customer = {"name": "Deployment Test", "email": "test@deploy.com"}
    
    # Test cases with expected behaviors
    test_cases = [
        {
            "query": "Show me some jens", 
            "expected_agent": "recommendation_agent",
            "expected_search_term": "jeans",
            "description": "Fuzzy matching: jens → jeans"
        },
        {
            "query": "What price of tshrt?",
            "expected_agent": "product_info_agent", 
            "expected_search_term": "tee",
            "description": "Fuzzy matching: tshrt → t-shirt → tee"
        },
        {
            "query": "I need nike shoos",
            "expected_agent": "recommendation_agent",
            "expected_search_term": "sho",
            "description": "Fuzzy matching: shoos → shoes → sho"
        },
        {
            "query": "Can you recommend something?",
            "expected_agent": "recommendation_agent",
            "expected_search_term": None,
            "description": "General recommendation (fixed GPT extraction bug)"
        },
        {
            "query": "What's the price of jeans?",
            "expected_agent": "product_info_agent",
            "expected_search_term": "jeans", 
            "description": "Exact matching preservation"
        },
        {
            "query": "Hello!",
            "expected_agent": "general",
            "expected_search_term": None,
            "description": "General conversation handling"
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: {test_case['description']}")
        print(f"   Query: '{test_case['query']}'")
        
        try:
            response = await coordinator.process_message(
                message=test_case['query'],
                history=[],
                customer_info=test_customer,
                access_token="test_token",
                shop_domain="test.myshopify.com"
            )
            
            agent_used = response.get("agent_used")
            search_term = response.get("search_term_used")
            
            # Validate agent
            agent_match = agent_used == test_case["expected_agent"]
            search_match = search_term == test_case["expected_search_term"]
            
            if agent_match and search_match:
                print(f"   ✅ PASS - Agent: {agent_used}, Search: {search_term}")
                passed += 1
            else:
                print(f"   ❌ FAIL - Expected agent: {test_case['expected_agent']}, got: {agent_used}")
                print(f"           Expected search: {test_case['expected_search_term']}, got: {search_term}")
                failed += 1
                
        except Exception as e:
            print(f"   ❌ ERROR - {str(e)}")
            failed += 1
    
    print(f"\n" + "=" * 50)
    print(f"📊 VALIDATION RESULTS")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {(passed/(passed+failed)*100):.1f}%")
    
    if failed == 0:
        print(f"\n🎉 ALL TESTS PASSED! Ready for deployment!")
        print(f"\n🔧 ENHANCEMENTS IMPLEMENTED:")
        print(f"   • Fuzzy matching for product search")
        print(f"   • Enhanced input classification with misspelling examples")  
        print(f"   • Fixed GPT humanizer agent KeyError bug")
        print(f"   • Fixed GPT keyword extraction corruption")
        print(f"   • Robust fallback mechanisms")
        print(f"   • Multi-tier search strategy")
        print(f"   • Comprehensive error handling")
        
        print(f"\n🚀 READY FOR PRODUCTION DEPLOYMENT!")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review before deployment.")
    
    return failed == 0

if __name__ == "__main__":
    asyncio.run(validate_deployment())

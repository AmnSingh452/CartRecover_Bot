"""
Test script for customer feedback system
Tests all feedback endpoints and functionality
"""

import asyncio
import aiohttp
import json
from datetime import datetime
import sys

BASE_URL = "http://localhost:8000"

async def test_feedback_system():
    """Test the complete feedback system workflow"""
    
    print("🧪 Testing Customer Feedback System")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        
        # Test 1: Generate feedback link
        print("\n1️⃣ Testing feedback link generation...")
        try:
            feedback_link_data = {
                "session_id": "test-session-feedback-123",
                "shop_domain": "demo-store.myshopify.com",
                "customer_info": {
                    "name": "Test Customer",
                    "conversation_topic": "Product Info"
                }
            }
            
            async with session.post(
                f"{BASE_URL}/api/feedback/generate-feedback-link",
                json=feedback_link_data
            ) as response:
                result = await response.json()
                
                if response.status == 200 and result.get("success"):
                    feedback_url = result["data"]["feedback_url"] 
                    feedback_token = result["data"]["feedback_token"]
                    print(f"✅ Feedback link generated: {feedback_url}")
                    print(f"📝 Token: {feedback_token}")
                else:
                    print(f"❌ Failed to generate feedback link: {result}")
                    return False
        except Exception as e:
            print(f"❌ Error generating feedback link: {e}")
            return False
        
        # Test 2: Retrieve feedback session by token
        print("\n2️⃣ Testing feedback session retrieval...")
        try:
            async with session.get(
                f"{BASE_URL}/api/feedback/token/{feedback_token}"
            ) as response:
                result = await response.json()
                
                if response.status == 200 and result.get("success"):
                    session_data = result["data"]
                    print(f"✅ Feedback session retrieved for session: {session_data['session_id']}")
                    print(f"🏪 Shop: {session_data['shop_domain']}")
                else:
                    print(f"❌ Failed to retrieve feedback session: {result}")
                    return False
        except Exception as e:
            print(f"❌ Error retrieving feedback session: {e}")
            return False
        
        # Test 3: Submit feedback
        print("\n3️⃣ Testing feedback submission...")
        try:
            feedback_data = {
                "session_id": "test-session-feedback-123",
                "shop_domain": "demo-store.myshopify.com",
                "rating": 5,
                "feedback_text": "Excellent chatbot! Very helpful and responsive. The product recommendations were spot on.",
                "customer_name": "Test Customer",
                "customer_email": "test@example.com",
                "conversation_topic": "Product Info"
            }
            
            async with session.post(
                f"{BASE_URL}/api/feedback/submit",
                json=feedback_data
            ) as response:
                result = await response.json()
                
                if response.status == 200 and result.get("success"):
                    feedback_id = result["data"]["feedback_id"]
                    print(f"✅ Feedback submitted successfully with ID: {feedback_id}")
                    print(f"⭐ Rating: {result['data']['rating']}/5")
                else:
                    print(f"❌ Failed to submit feedback: {result}")
                    return False
        except Exception as e:
            print(f"❌ Error submitting feedback: {e}")
            return False
        
        # Test 4: Submit additional feedback samples
        print("\n4️⃣ Adding more sample feedback...")
        sample_feedback = [
            {
                "session_id": "test-session-2",
                "shop_domain": "demo-store.myshopify.com",
                "rating": 4,
                "feedback_text": "Good experience, found what I was looking for quickly.",
                "customer_name": "Jane Smith",
                "conversation_topic": "General"
            },
            {
                "session_id": "test-session-3",
                "shop_domain": "demo-store.myshopify.com",
                "rating": 3,
                "feedback_text": "Average service, could be more responsive to complex questions.",
                "customer_name": "Bob Johnson",
                "conversation_topic": "Shipping"
            },
            {
                "session_id": "test-session-4", 
                "shop_domain": "demo-store.myshopify.com",
                "rating": 2,
                "feedback_text": "Had trouble getting accurate product information.",
                "conversation_topic": "Product Info"
            }
        ]
        
        for feedback in sample_feedback:
            try:
                async with session.post(
                    f"{BASE_URL}/api/feedback/submit",
                    json=feedback
                ) as response:
                    result = await response.json()
                    if result.get("success"):
                        print(f"✅ Sample feedback {feedback['rating']}⭐ added")
                    else:
                        print(f"⚠️ Sample feedback failed: {result}")
            except Exception as e:
                print(f"⚠️ Error adding sample feedback: {e}")
        
        # Test 5: Get feedback analytics
        print("\n5️⃣ Testing feedback analytics...")
        try:
            async with session.get(
                f"{BASE_URL}/api/feedback/analytics/demo-store.myshopify.com?days=30"
            ) as response:
                result = await response.json()
                
                if response.status == 200 and result.get("success"):
                    analytics = result["data"]
                    summary = analytics["summary"]
                    
                    print(f"✅ Feedback analytics retrieved:")
                    print(f"   📊 Total Feedback: {summary['total_feedback']}")
                    print(f"   ⭐ Average Rating: {summary['average_rating']:.1f}/5")
                    print(f"   👍 Positive Feedback: {summary['positive_feedback']}")
                    print(f"   👎 Negative Feedback: {summary['negative_feedback']}")
                    print(f"   📈 Recent Feedback Count: {len(analytics['recent_feedback'])}")
                    print(f"   📅 Daily Trends Count: {len(analytics['daily_trends'])}")
                    print(f"   🏷️ Topic Breakdown Count: {len(analytics['topic_breakdown'])}")
                    
                    # Show recent feedback
                    print(f"\n   📝 Recent Feedback:")
                    for feedback in analytics["recent_feedback"][:3]:
                        print(f"      • {feedback['rating']}⭐ - {feedback['customer_name']} ({feedback['topic']})")
                        if feedback['feedback_text']:
                            print(f"        \"{feedback['feedback_text'][:50]}{'...' if len(feedback['feedback_text']) > 50 else ''}\"")
                    
                else:
                    print(f"❌ Failed to get feedback analytics: {result}")
                    return False
        except Exception as e:
            print(f"❌ Error getting feedback analytics: {e}")
            return False
        
        # Test 6: Test invalid scenarios
        print("\n6️⃣ Testing error handling...")
        
        # Test invalid rating
        try:
            invalid_feedback = {
                "session_id": "test-invalid",
                "shop_domain": "demo-store.myshopify.com",
                "rating": 6,  # Invalid rating > 5
                "feedback_text": "This should fail"
            }
            
            async with session.post(
                f"{BASE_URL}/api/feedback/submit",
                json=invalid_feedback
            ) as response:
                result = await response.json()
                if response.status == 400:
                    print("✅ Invalid rating properly rejected")
                else:
                    print(f"⚠️ Invalid rating not properly handled: {result}")
        except Exception as e:
            print(f"⚠️ Error testing invalid rating: {e}")
        
        # Test expired/invalid token
        try:
            async with session.get(
                f"{BASE_URL}/api/feedback/token/invalid-token-123"
            ) as response:
                if response.status == 404:
                    print("✅ Invalid token properly rejected")
                else:
                    result = await response.json()
                    print(f"⚠️ Invalid token not properly handled: {result}")
        except Exception as e:
            print(f"⚠️ Error testing invalid token: {e}")
    
    print(f"\n" + "=" * 50)
    print("🎉 Feedback system testing completed!")
    print("\n🔧 System Ready For:")
    print("   • Generating feedback links after chat sessions")
    print("   • Collecting customer ratings and feedback")
    print("   • Analytics dashboard integration")
    print("   • Feedback-driven bot improvements")
    
    return True

async def test_chat_with_feedback():
    """Test chatbot integration with feedback link generation"""
    
    print("\n🤖 Testing Chat + Feedback Integration")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        
        # Test chat with goodbye message (should trigger feedback link)
        print("\n💬 Testing chat with goodbye message...")
        try:
            chat_data = {
                "message": "Thanks for your help! Goodbye!",
                "session_id": "feedback-test-session",
                "shop_domain": "demo-store.myshopify.com"
            }
            
            async with session.post(
                f"{BASE_URL}/api/chat",
                json=chat_data
            ) as response:
                result = await response.json()
                
                if response.status == 200 and result.get("success"):
                    response_data = result["data"]
                    bot_response = response_data["response"]
                    
                    print(f"✅ Chat response received")
                    print(f"🤖 Bot: {bot_response[:100]}...")
                    
                    # Check if feedback link was included
                    if "feedback_link" in response_data:
                        feedback_link = response_data["feedback_link"]
                        print(f"✅ Feedback link generated: {feedback_link}")
                        print(f"⏰ Expires: {response_data.get('feedback_expires', 'N/A')}")
                    else:
                        print("ℹ️ No feedback link generated (conversation may not be substantial enough)")
                        
                else:
                    print(f"❌ Chat request failed: {result}")
        except Exception as e:
            print(f"❌ Error testing chat with feedback: {e}")

if __name__ == "__main__":
    print("🚀 Starting Feedback System Tests...")
    print("📋 Make sure your backend server is running on http://localhost:8000")
    print("📋 Make sure database tables are created (run migrate_feedback_tables.py)")
    
    # Run database migration first
    print("\n📊 Running database migration...")
    import subprocess
    try:
        result = subprocess.run([sys.executable, "migrate_feedback_tables.py"], 
                              capture_output=True, text=True, cwd=".")
        if result.returncode == 0:
            print("✅ Database migration successful")
        else:
            print(f"⚠️ Database migration output: {result.stdout}")
            if result.stderr:
                print(f"⚠️ Migration errors: {result.stderr}")
    except Exception as e:
        print(f"⚠️ Could not run migration: {e}")
    
    # Run tests
    try:
        asyncio.run(test_feedback_system())
        asyncio.run(test_chat_with_feedback())
    except KeyboardInterrupt:
        print("\n⚡ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")

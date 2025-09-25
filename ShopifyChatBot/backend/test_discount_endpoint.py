#!/usr/bin/env python3
"""
Test script for the enhanced /api/abandoned-cart-discount endpoint
"""

import requests
import json

def test_abandoned_cart_discount():
    """Test the abandoned cart discount endpoint"""
    
    # Test endpoint URL (adjust if your server runs on different port)
    url = "http://localhost:8000/api/abandoned-cart-discount"
    
    # Test request payload matching your specifications
    payload = {
        "session_id": "test_session_123",
        "shop_domain": "aman-chatbot-test.myshopify.com",
        "customer_id": "customer_456",
        "cart_data": {
            "items": [
                {"product_id": "123", "quantity": 2},
                {"product_id": "456", "quantity": 1}
            ],
            "total": 99.99
        },
        "discount_percentage": 15
    }
    
    print("🧪 Testing /api/abandoned-cart-discount endpoint")
    print("=" * 50)
    print(f"📡 URL: {url}")
    print(f"📝 Payload: {json.dumps(payload, indent=2)}")
    print()
    
    try:
        # Send POST request
        response = requests.post(
            url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            timeout=10
        )
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📋 Response Headers: {dict(response.headers)}")
        print()
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS Response:")
            print(json.dumps(result, indent=2))
            
            # Validate response format
            if "discount_code" in result and "message" in result:
                print(f"✅ Response format is correct!")
                print(f"🎫 Discount Code: {result['discount_code']}")
                print(f"💬 Message: {result['message']}")
            else:
                print("⚠️ Response format doesn't match specifications")
                
        else:
            print("❌ ERROR Response:")
            try:
                error_data = response.json()
                print(json.dumps(error_data, indent=2))
            except:
                print(response.text)
    
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Server is not running")
        print("💡 Start your FastAPI server with: uvicorn main:app --reload")
    except requests.exceptions.Timeout:
        print("❌ Timeout Error: Request took too long")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")

def test_cors_preflight():
    """Test CORS preflight request"""
    url = "http://localhost:8000/api/abandoned-cart-discount"
    
    print("\n🧪 Testing CORS preflight (OPTIONS request)")
    print("=" * 50)
    
    try:
        response = requests.options(
            url,
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📋 CORS Headers:")
        cors_headers = {k: v for k, v in response.headers.items() if 'access-control' in k.lower()}
        for header, value in cors_headers.items():
            print(f"  {header}: {value}")
            
        if response.status_code == 200 and 'access-control-allow-origin' in response.headers:
            print("✅ CORS preflight working correctly!")
        else:
            print("⚠️ CORS preflight may not be configured correctly")
    
    except Exception as e:
        print(f"❌ CORS test failed: {e}")

if __name__ == "__main__":
    test_abandoned_cart_discount()
    test_cors_preflight()

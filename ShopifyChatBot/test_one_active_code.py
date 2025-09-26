#!/usr/bin/env python3
"""
Test script for the "One Active Code Per Customer" feature
"""

import requests
import json
import time

def test_one_active_code():
    """Test that the same customer gets the same active code"""
    
    url = "http://localhost:8000/api/abandoned-cart-discount"
    
    payload = {
        "session_id": "test_one_code_policy",
        "shop_domain": "aman-chatbot-test.myshopify.com",
        "customer_id": "customer_123",
        "discount_percentage": 20
    }
    
    print(" Testing One Active Code Per Customer Policy")
    print("=" * 60)
    print(f" Session ID: {payload['session_id']}")
    print(f" Customer ID: {payload['customer_id']}")
    print()
    
    codes_received = []
    
    # Make 3 requests in quick succession
    for i in range(1, 4):
        print(f" Request #{i}")
        try:
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                code = result.get('discount_code')
                codes_received.append(code)
                print(f" Status: {response.status_code}")
                print(f" Code: {code}")
                print(f" Message: {result.get('message')}")
            else:
                print(f" Status: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f" Error: {error_data}")
                except:
                    print(f" Error: {response.text}")
        
        except requests.exceptions.ConnectionError:
            print(" Connection Error: Server not running")
            return
        except Exception as e:
            print(f" Error: {e}")
        
        print("-" * 40)
        time.sleep(1)  # Small delay between requests
    
    # Analyze results
    print("\n RESULTS ANALYSIS:")
    print(f"Total codes received: {len(codes_received)}")
    print(f"Unique codes: {len(set(codes_received))}")
    print(f"All codes: {codes_received}")
    
    if len(set(codes_received)) == 1 and len(codes_received) > 1:
        print(" SUCCESS: One Active Code Policy is working!")
        print(" Customer received the same code for multiple requests")
    elif len(codes_received) == 0:
        print(" FAILED: No codes received (server may be down)")
    elif len(set(codes_received)) == len(codes_received):
        print(" FAILED: Different codes generated each time")
        print(" One Active Code Policy is NOT working")
    else:
        print(" PARTIAL: Mixed results - check implementation")

def test_different_sessions():
    """Test that different sessions get different codes"""
    
    url = "http://localhost:8000/api/abandoned-cart-discount"
    
    sessions = [
        {"session_id": "customer_A", "customer_id": "customer_A"},
        {"session_id": "customer_B", "customer_id": "customer_B"}
    ]
    
    print("\n Testing Different Sessions Get Different Codes")
    print("=" * 60)
    
    codes = {}
    
    for session_data in sessions:
        payload = {
            **session_data,
            "shop_domain": "aman-chatbot-test.myshopify.com",
            "discount_percentage": 15
        }
        
        print(f" Testing session: {session_data['session_id']}")
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                code = result.get('discount_code')
                codes[session_data['session_id']] = code
                print(f" Code: {code}")
            else:
                print(f" Error: {response.status_code}")
        
        except Exception as e:
            print(f" Error: {e}")
    
    print(f"\n Session Codes: {codes}")
    
    if len(codes) == 2 and len(set(codes.values())) == 2:
        print(" SUCCESS: Different sessions get different codes")
    else:
        print(" FAILED: Sessions should get different codes")

if __name__ == "__main__":
    test_one_active_code()
    test_different_sessions()

#!/usr/bin/env python3
"""
Remote Database Migration Runner
Run this after the backend is deployed to create feedback tables
"""

import requests
import time

def run_remote_migration():
    """
    This assumes you have a migration endpoint on your deployed backend
    If not, you'll need to run the migration script directly on Render
    """
    
    print("🔄 Waiting for backend deployment...")
    
    # Wait for backend to be ready
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            response = requests.get("https://cartrecover-bot.onrender.com/ping", timeout=10)
            if response.status_code == 200:
                print("✅ Backend is ready!")
                break
        except:
            pass
        
        print(f"⏳ Attempt {attempt + 1}/{max_attempts} - waiting for deployment...")
        time.sleep(10)
    else:
        print("❌ Backend deployment timeout")
        return False
    
    # Check if feedback routes are available
    try:
        response = requests.get("https://cartrecover-bot.onrender.com/api/feedback/submit", timeout=10)
        # Even a 405 (Method Not Allowed) means the route exists
        if response.status_code in [405, 422]:
            print("✅ Feedback routes are deployed!")
            return True
        elif response.status_code == 404:
            print("❌ Feedback routes not deployed yet")
            return False
    except Exception as e:
        print(f"❌ Error checking feedback routes: {e}")
        return False

if __name__ == "__main__":
    if run_remote_migration():
        print("\n🎉 Ready to test feedback system!")
        print("You can now run: python test_complete_integration.py")
    else:
        print("\n⏳ Please wait for deployment to complete and try again")

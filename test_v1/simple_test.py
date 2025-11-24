#!/usr/bin/env python3
"""
Simple test to verify the API is working
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_api():
    print("🧪 Testing Aurum Matrimony API...")
    
    try:
        # Test root endpoint
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API is running: {data['message']}")
        else:
            print(f"❌ API not responding: {response.status_code}")
            return
        
        # Test health endpoint
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Health check passed")
        
        # Test setup guide
        response = requests.get(f"{BASE_URL}/setup-guide")
        if response.status_code == 200:
            setup = response.json()
            print("✅ Setup guide available")
            print(f"   Current config: {setup['current_config']}")
        
        # Test API docs
        response = requests.get(f"{BASE_URL}/docs")
        if response.status_code == 200:
            print("✅ API documentation available at /docs")
        
        print("\n🎉 Basic API test completed!")
        print("Visit http://localhost:8000/docs to explore all endpoints")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server")
        print("Make sure to run: python run_dev_safe.py")
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_api()
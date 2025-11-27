#!/usr/bin/env python3
"""Debug script to test authentication"""
import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000"

async def test_login():
    async with httpx.AsyncClient() as client:
        # Test with a known phone from the database
        test_phones = [
            "+18547352813",
            "+18893797291",
            "+18129353878",
            "+919876543211",
            "+919876543212",
        ]
        
        # Common test password
        test_password = "Test@1234"
        
        print("=" * 60)
        print("TESTING LOGIN WITH KNOWN USERS")
        print("=" * 60)
        
        for phone in test_phones:
            print(f"\n[Testing] Phone: {phone}")
            
            response = await client.post(
                f"{BASE_URL}/api/v1/auth/login",
                json={
                    "phone": phone,
                    "password": test_password,
                }
            )
            
            print(f"  Status Code: {response.status_code}")
            try:
                data = response.json()
                print(f"  Response: {json.dumps(data, indent=2)}")
            except Exception as e:
                print(f"  Response Text: {response.text}")
            
            print("-" * 60)

async def test_register_and_login():
    """Register a new user and immediately try to login"""
    async with httpx.AsyncClient() as client:
        test_phone = "+919999999998"
        test_password = "TestPass@123"
        
        print("\n" + "=" * 60)
        print("TESTING REGISTER + LOGIN FLOW")
        print("=" * 60)
        
        # Step 1: Register
        print(f"\n[Step 1] Registering user with phone: {test_phone}")
        register_response = await client.post(
            f"{BASE_URL}/api/v1/auth/register",
            json={
                "phone": test_phone,
                "email": f"test_{test_phone.replace('+', '')}@test.com",
                "whatsapp": test_phone,
                "password": test_password,
            }
        )
        
        print(f"  Status Code: {register_response.status_code}")
        try:
            reg_data = register_response.json()
            print(f"  Response: {json.dumps(reg_data, indent=2)}")
        except Exception as e:
            print(f"  Response Text: {register_response.text}")
        
        # Step 2: Login with same credentials
        print(f"\n[Step 2] Logging in with same credentials")
        login_response = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={
                "phone": test_phone,
                "password": test_password,
            }
        )
        
        print(f"  Status Code: {login_response.status_code}")
        try:
            login_data = login_response.json()
            print(f"  Response: {json.dumps(login_data, indent=2)}")
        except Exception as e:
            print(f"  Response Text: {login_response.text}")

if __name__ == "__main__":
    print("Starting authentication debug tests...\n")
    asyncio.run(test_login())
    asyncio.run(test_register_and_login())
    print("\n" + "=" * 60)
    print("Testing complete!")
    print("=" * 60)

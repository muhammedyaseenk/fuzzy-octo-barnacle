#!/usr/bin/env python3
"""
Test script for profiles functionality
"""
import asyncio
import httpx


BASE_URL = "http://localhost:8000/api/v1"


async def test_profiles():
    """Test profiles functionality"""
    async with httpx.AsyncClient() as client:
        
        print("🧪 Testing Profiles Domain...")
        
        # 1. Login to get token
        print("\n1️⃣ Logging in...")
        login_data = {
            "phone": "+919876543210",
            "password": "testpassword123"
        }
        
        response = await client.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code != 200:
            print("❌ Login failed. Make sure you have a test user created.")
            print("Run: python test_onboarding.py first")
            return
        
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Login successful")
        
        # 2. Test dashboard
        print("\n2️⃣ Testing dashboard...")
        response = await client.get(f"{BASE_URL}/profiles/dashboard", headers=headers)
        if response.status_code == 200:
            dashboard = response.json()
            print(f"✅ Dashboard loaded:")
            print(f"   Profile completion: {dashboard['profile_completion']}%")
            print(f"   Verification status: {dashboard['verification_status']}")
        else:
            print(f"❌ Dashboard failed: {response.text}")
        
        # 3. Test profile summary
        print("\n3️⃣ Testing profile summary...")
        response = await client.get(f"{BASE_URL}/profiles/me/summary", headers=headers)
        if response.status_code == 200:
            summary = response.json()
            print(f"✅ Profile summary:")
            print(f"   Name: {summary['first_name']} {summary['last_name']}")
            print(f"   Age: {summary['age']}")
            print(f"   Location: {summary['location']}")
        else:
            print(f"❌ Profile summary failed: {response.text}")
        
        # 4. Test full profile
        print("\n4️⃣ Testing full profile...")
        response = await client.get(f"{BASE_URL}/profiles/me", headers=headers)
        if response.status_code == 200:
            profile = response.json()
            print(f"✅ Full profile loaded:")
            print(f"   Education: {profile['education']}")
            print(f"   Occupation: {profile['occupation']}")
            print(f"   Religion: {profile['religion']}")
        else:
            print(f"❌ Full profile failed: {response.text}")
        
        # 5. Test profile update
        print("\n5️⃣ Testing profile update...")
        update_data = {
            "height": 180,
            "weight": 75,
            "company": "Updated Tech Corp"
        }
        
        response = await client.patch(f"{BASE_URL}/profiles/me", json=update_data, headers=headers)
        if response.status_code == 200:
            print("✅ Profile updated successfully")
            
            # Verify update
            response = await client.get(f"{BASE_URL}/profiles/me", headers=headers)
            if response.status_code == 200:
                profile = response.json()
                print(f"   Updated height: {profile['height']}")
                print(f"   Updated company: {profile['company']}")
        else:
            print(f"❌ Profile update failed: {response.text}")
        
        print("\n🎉 Profiles test completed!")


if __name__ == "__main__":
    print("Make sure the server is running on http://localhost:8000")
    print("And you have a test user created (run test_onboarding.py first)")
    input("Press Enter when ready...")
    asyncio.run(test_profiles())
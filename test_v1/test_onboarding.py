#!/usr/bin/env python3
"""
Test script for onboarding functionality
"""
import asyncio
import httpx
from datetime import date


BASE_URL = "http://localhost:8000/api/v1"


async def test_onboarding_flow():
    """Test the complete onboarding flow"""
    async with httpx.AsyncClient() as client:
        
        print("🧪 Testing Onboarding Flow...")
        
        # 1. Test user signup
        print("\n1️⃣ Testing user signup...")
        signup_data = {
            "phone": "+919876543210",
            "email": "test@example.com",
            "password": "testpassword123",
            "first_name": "John",
            "last_name": "Doe"
        }
        
        response = await client.post(f"{BASE_URL}/onboarding/signup", json=signup_data)
        print(f"Signup Response: {response.status_code}")
        if response.status_code == 200:
            signup_result = response.json()
            user_id = signup_result["user_id"]
            print(f"✅ User created with ID: {user_id}")
        else:
            print(f"❌ Signup failed: {response.text}")
            return
        
        # 2. Test complete profile
        print("\n2️⃣ Testing profile completion...")
        profile_data = {
            "profile": {
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1990-01-15",
                "gender": "male",
                "marital_status": "never_married",
                "height": 175,
                "weight": 70,
                "complexion": "fair",
                "body_type": "average",
                "blood_group": "O+"
            },
            "location": {
                "country": "India",
                "state": "Kerala",
                "district": "Ernakulam",
                "city": "Kochi",
                "current_location": "Kochi, Kerala",
                "native_place": "Thrissur, Kerala"
            },
            "religion": {
                "religion": "Hindu",
                "caste": "Nair",
                "sub_caste": "Menon",
                "mother_tongue": "Malayalam"
            },
            "lifestyle": {
                "diet": "vegetarian",
                "smoking": "no",
                "drinking": "occasionally"
            },
            "education": {
                "highest_education": "Bachelor of Engineering",
                "institution": "Kerala University",
                "year_of_completion": 2012
            },
            "career": {
                "occupation": "Software Engineer",
                "company": "Tech Corp",
                "designation": "Senior Developer",
                "annual_income": 1200000,
                "employment_type": "private"
            },
            "family": {
                "father_name": "Ravi Doe",
                "mother_name": "Sita Doe",
                "family_type": "nuclear",
                "family_status": "middle_class",
                "siblings": 1,
                "family_contact": "+919876543211"
            },
            "preferences": {
                "min_age": 25,
                "max_age": 35,
                "min_height": 160,
                "max_height": 180,
                "preferred_religions": ["Hindu"],
                "preferred_castes": ["Nair", "Menon"],
                "min_income": 800000,
                "willing_to_relocate": True,
                "expectations": "Looking for a caring and understanding partner"
            }
        }
        
        response = await client.post(f"{BASE_URL}/onboarding/complete-profile/{user_id}", json=profile_data)
        print(f"Profile Completion Response: {response.status_code}")
        if response.status_code == 200:
            print("✅ Profile completed successfully")
        else:
            print(f"❌ Profile completion failed: {response.text}")
            return
        
        # 3. Test verification status
        print("\n3️⃣ Testing verification status...")
        response = await client.get(f"{BASE_URL}/onboarding/verification-status/{user_id}")
        print(f"Verification Status Response: {response.status_code}")
        if response.status_code == 200:
            status_result = response.json()
            print(f"✅ Verification Status: {status_result['verification_status']}")
        else:
            print(f"❌ Status check failed: {response.text}")
        
        # 4. Test admin login and verification
        print("\n4️⃣ Testing admin verification...")
        
        # Login as admin
        admin_login = {
            "phone": "+919999999999",
            "password": "admin123"
        }
        
        response = await client.post(f"{BASE_URL}/auth/login", json=admin_login)
        if response.status_code == 200:
            admin_token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            # Get pending verifications
            response = await client.get(f"{BASE_URL}/onboarding/admin/pending-verifications", headers=headers)
            if response.status_code == 200:
                pending = response.json()
                print(f"✅ Found {len(pending)} pending verifications")
                
                # Approve the user
                verify_data = {
                    "approved": True,
                    "notes": "Profile looks good. Approved."
                }
                
                response = await client.post(f"{BASE_URL}/onboarding/admin/verify-user/{user_id}", 
                                           json=verify_data, headers=headers)
                if response.status_code == 200:
                    print("✅ User approved successfully")
                else:
                    print(f"❌ User approval failed: {response.text}")
            else:
                print(f"❌ Failed to get pending verifications: {response.text}")
        else:
            print(f"❌ Admin login failed: {response.text}")
        
        print("\n🎉 Onboarding flow test completed!")


if __name__ == "__main__":
    print("Make sure the server is running on http://localhost:8000")
    print("Run: python run_dev.py")
    input("Press Enter when server is ready...")
    asyncio.run(test_onboarding_flow())
#!/usr/bin/env python3
"""
Test script for matching functionality
"""
import asyncio
import httpx


BASE_URL = "http://localhost:8000/api/v1"


async def test_matching():
    """Test matching functionality"""
    async with httpx.AsyncClient() as client:
        
        print("🧪 Testing Matching Domain...")
        
        # 1. Login as user
        print("\n1️⃣ Logging in...")
        login_data = {
            "phone": "+919876543210",
            "password": "testpassword123"
        }
        
        response = await client.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code != 200:
            print("❌ Login failed. Make sure you have a test user created.")
            return
        
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Login successful")
        
        # 2. Test recommendations
        print("\n2️⃣ Testing recommendations...")
        response = await client.get(f"{BASE_URL}/matching/recommendations", headers=headers)
        if response.status_code == 200:
            recommendations = response.json()
            print(f"✅ Found {recommendations['total_count']} recommendations")
            print(f"   Page {recommendations['page']} of {recommendations['total_pages']}")
        else:
            print(f"❌ Recommendations failed: {response.text}")
        
        # 3. Test search with POST
        print("\n3️⃣ Testing search with filters (POST)...")
        search_data = {
            "filters": {
                "min_age": 25,
                "max_age": 35,
                "min_height": 160,
                "max_height": 180,
                "religion": ["Hindu"],
                "country": "India",
                "state": "Kerala"
            },
            "sort_by": "age",
            "page": 1,
            "limit": 10
        }
        
        response = await client.post(f"{BASE_URL}/matching/search", json=search_data, headers=headers)
        if response.status_code == 200:
            search_results = response.json()
            print(f"✅ Found {search_results['total_count']} matches with filters")
            if search_results['matches']:
                first_match = search_results['matches'][0]
                print(f"   First match: {first_match['first_name']} {first_match['last_name']}, Age: {first_match['age']}")
        else:
            print(f"❌ Search failed: {response.text}")
        
        # 4. Test search with GET parameters
        print("\n4️⃣ Testing search with GET parameters...")
        params = {
            "min_age": 20,
            "max_age": 40,
            "religion": ["Hindu", "Christian"],
            "state": "Kerala",
            "sort_by": "height",
            "limit": 5
        }
        
        response = await client.get(f"{BASE_URL}/matching/search", params=params, headers=headers)
        if response.status_code == 200:
            search_results = response.json()
            print(f"✅ GET search found {search_results['total_count']} matches")
        else:
            print(f"❌ GET search failed: {response.text}")
        
        # 5. Test shortlisting (if we have matches)
        if 'search_results' in locals() and search_results['matches']:
            target_user_id = search_results['matches'][0]['user_id']
            
            print(f"\n5️⃣ Testing shortlist user {target_user_id}...")
            shortlist_data = {
                "target_user_id": target_user_id
            }
            
            response = await client.post(f"{BASE_URL}/matching/shortlist", 
                                       json=shortlist_data, headers=headers)
            if response.status_code == 200:
                shortlist_result = response.json()
                print(f"✅ User shortlisted. ID: {shortlist_result['shortlist_id']}")
                
                # 6. Test get shortlisted users
                print("\n6️⃣ Testing get shortlisted users...")
                response = await client.get(f"{BASE_URL}/matching/shortlisted", headers=headers)
                if response.status_code == 200:
                    shortlisted = response.json()
                    print(f"✅ Found {shortlisted['total_count']} shortlisted users")
                else:
                    print(f"❌ Get shortlisted failed: {response.text}")
                
                # 7. Test remove from shortlist
                print(f"\n7️⃣ Testing remove from shortlist...")
                response = await client.delete(f"{BASE_URL}/matching/shortlist/{target_user_id}", 
                                             headers=headers)
                if response.status_code == 200:
                    print("✅ User removed from shortlist")
                else:
                    print(f"❌ Remove shortlist failed: {response.text}")
            else:
                print(f"❌ Shortlist failed: {response.text}")
        else:
            print("\n5️⃣ Skipping shortlist tests (no matches found)")
        
        # 8. Test advanced search
        print("\n8️⃣ Testing advanced search...")
        advanced_search = {
            "filters": {
                "min_age": 22,
                "max_age": 45,
                "min_height": 150,
                "max_height": 190,
                "marital_status": ["never_married"],
                "religion": ["Hindu", "Christian", "Muslim"],
                "diet": ["vegetarian", "non_vegetarian"],
                "smoking": ["no"],
                "drinking": ["no", "occasionally"],
                "min_income": 500000
            },
            "sort_by": "income",
            "page": 1,
            "limit": 15
        }
        
        response = await client.post(f"{BASE_URL}/matching/search", json=advanced_search, headers=headers)
        if response.status_code == 200:
            advanced_results = response.json()
            print(f"✅ Advanced search found {advanced_results['total_count']} matches")
        else:
            print(f"❌ Advanced search failed: {response.text}")
        
        print("\n🎉 Matching test completed!")


if __name__ == "__main__":
    print("Make sure the server is running on http://localhost:8000")
    print("And you have test users created with preferences set")
    input("Press Enter when ready...")
    asyncio.run(test_matching())
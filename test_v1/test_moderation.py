#!/usr/bin/env python3
"""
Test script for moderation functionality
"""
import asyncio
import httpx


BASE_URL = "http://localhost:8000/api/v1"


async def test_moderation():
    """Test moderation functionality"""
    async with httpx.AsyncClient() as client:
        
        print("🧪 Testing Moderation Domain...")
        
        # 1. Login as regular user
        print("\n1️⃣ Logging in as user...")
        login_data = {
            "phone": "+919876543210",
            "password": "testpassword123"
        }
        
        response = await client.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code != 200:
            print("❌ Login failed. Make sure you have a test user created.")
            return
        
        user_token = response.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}
        print("✅ User login successful")
        
        # 2. Login as admin
        print("\n2️⃣ Logging in as admin...")
        admin_login = {
            "phone": "+919999999999",
            "password": "admin123"
        }
        
        response = await client.post(f"{BASE_URL}/auth/login", json=admin_login)
        if response.status_code != 200:
            print("❌ Admin login failed. Make sure admin user exists.")
            return
        
        admin_token = response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print("✅ Admin login successful")
        
        # 3. Test reporting a user
        print("\n3️⃣ Testing user reporting...")
        report_data = {
            "reported_user_id": 1,  # Assuming admin user has ID 1
            "reason": "inappropriate_behavior",
            "details": "User was being rude in messages"
        }
        
        response = await client.post(f"{BASE_URL}/moderation/report", 
                                   json=report_data, headers=user_headers)
        if response.status_code == 200:
            report_result = response.json()
            print(f"✅ User reported successfully. Report ID: {report_result['report_id']}")
        else:
            print(f"❌ Report failed: {response.text}")
        
        # 4. Test blocking a user
        print("\n4️⃣ Testing user blocking...")
        block_data = {
            "blocked_user_id": 1,  # Assuming admin user has ID 1
            "reason": "Don't want to interact"
        }
        
        response = await client.post(f"{BASE_URL}/moderation/block", 
                                   json=block_data, headers=user_headers)
        if response.status_code == 200:
            block_result = response.json()
            print(f"✅ User blocked successfully. Block ID: {block_result['block_id']}")
        else:
            print(f"❌ Block failed: {response.text}")
        
        # 5. Test getting my reports
        print("\n5️⃣ Testing get my reports...")
        response = await client.get(f"{BASE_URL}/moderation/my-reports", headers=user_headers)
        if response.status_code == 200:
            reports = response.json()["reports"]
            print(f"✅ Found {len(reports)} reports made by user")
        else:
            print(f"❌ Get reports failed: {response.text}")
        
        # 6. Test getting my blocks
        print("\n6️⃣ Testing get my blocks...")
        response = await client.get(f"{BASE_URL}/moderation/my-blocks", headers=user_headers)
        if response.status_code == 200:
            blocks = response.json()["blocked_users"]
            print(f"✅ Found {len(blocks)} users blocked by user")
        else:
            print(f"❌ Get blocks failed: {response.text}")
        
        # 7. Test admin - get pending reports
        print("\n7️⃣ Testing admin - get pending reports...")
        response = await client.get(f"{BASE_URL}/moderation/admin/reports", headers=admin_headers)
        if response.status_code == 200:
            pending_reports = response.json()
            print(f"✅ Found {len(pending_reports)} pending reports")
            
            # 8. Test admin - resolve report
            if pending_reports:
                print("\n8️⃣ Testing admin - resolve report...")
                report_id = pending_reports[0]["id"]
                resolve_data = {
                    "status": "reviewed",
                    "admin_notes": "Report reviewed and noted. Warning issued to user."
                }
                
                response = await client.post(f"{BASE_URL}/moderation/admin/reports/{report_id}/resolve",
                                           json=resolve_data, headers=admin_headers)
                if response.status_code == 200:
                    print("✅ Report resolved successfully")
                else:
                    print(f"❌ Report resolution failed: {response.text}")
        else:
            print(f"❌ Get pending reports failed: {response.text}")
        
        # 9. Test unblocking user
        print("\n9️⃣ Testing unblock user...")
        response = await client.delete(f"{BASE_URL}/moderation/block/1", headers=user_headers)
        if response.status_code == 200:
            print("✅ User unblocked successfully")
        else:
            print(f"❌ Unblock failed: {response.text}")
        
        print("\n🎉 Moderation test completed!")


if __name__ == "__main__":
    print("Make sure the server is running on http://localhost:8000")
    print("And you have test users created (run test_onboarding.py first)")
    input("Press Enter when ready...")
    asyncio.run(test_moderation())
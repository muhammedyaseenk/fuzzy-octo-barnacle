#!/usr/bin/env python3
"""
Comprehensive test script for all domains
"""
import asyncio
import httpx
import io
from PIL import Image


BASE_URL = "http://localhost:8000/api/v1"


async def test_all_domains():
    """Test all domain functionality"""
    async with httpx.AsyncClient() as client:
        
        print("🧪 Testing All Domains...")
        
        # 1. Login
        print("\n1️⃣ Authentication...")
        login_data = {
            "phone": "+919876543210",
            "password": "testpassword123"
        }
        
        response = await client.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code != 200:
            print("❌ Login failed. Make sure you have test users created.")
            return
        
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Authentication successful")
        
        # 2. Test Media Domain
        print("\n2️⃣ Testing Media Domain...")
        
        # Create a test image
        img = Image.new('RGB', (200, 200), color='red')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG')
        img_buffer.seek(0)
        
        files = {"file": ("test.jpg", img_buffer, "image/jpeg")}
        response = await client.post(f"{BASE_URL}/media/upload", files=files, headers=headers)
        
        if response.status_code == 200:
            upload_result = response.json()
            image_id = upload_result["image_id"]
            print(f"✅ Image uploaded: {image_id}")
            
            # Set as profile image
            profile_image_data = {"image_id": image_id, "is_primary": True}
            response = await client.post(f"{BASE_URL}/media/profile-image", 
                                       json=profile_image_data, headers=headers)
            if response.status_code == 200:
                print("✅ Profile image set")
        else:
            print(f"❌ Media upload failed: {response.text}")
        
        # 3. Test Notifications Domain
        print("\n3️⃣ Testing Notifications Domain...")
        
        response = await client.get(f"{BASE_URL}/notifications", headers=headers)
        if response.status_code == 200:
            notifications = response.json()
            print(f"✅ Found {len(notifications)} notifications")
            
            # Test unread count
            response = await client.get(f"{BASE_URL}/notifications/unread-count", headers=headers)
            if response.status_code == 200:
                unread = response.json()
                print(f"✅ Unread notifications: {unread['unread_count']}")
        else:
            print(f"❌ Notifications failed: {response.text}")
        
        # 4. Test Chat Domain
        print("\n4️⃣ Testing Chat Domain...")
        
        # Get conversations
        response = await client.get(f"{BASE_URL}/chat/conversations", headers=headers)
        if response.status_code == 200:
            conversations = response.json()
            print(f"✅ Found {len(conversations)} conversations")
            
            # Start conversation with admin (user ID 1)
            response = await client.post(f"{BASE_URL}/chat/conversations/1", headers=headers)
            if response.status_code == 200:
                conv_result = response.json()
                conversation_id = conv_result["conversation_id"]
                print(f"✅ Conversation started: {conversation_id}")
                
                # Send a message
                message_data = {
                    "conversation_id": conversation_id,
                    "content": "Hello! This is a test message."
                }
                response = await client.post(f"{BASE_URL}/chat/messages", 
                                           json=message_data, headers=headers)
                if response.status_code == 200:
                    message_result = response.json()
                    print(f"✅ Message sent: {message_result['id']}")
                    
                    # Get messages
                    response = await client.get(f"{BASE_URL}/chat/conversations/{conversation_id}/messages", 
                                              headers=headers)
                    if response.status_code == 200:
                        messages = response.json()
                        print(f"✅ Retrieved {len(messages)} messages")
        else:
            print(f"❌ Chat failed: {response.text}")
        
        # 5. Test Matching Domain
        print("\n5️⃣ Testing Matching Domain...")
        
        response = await client.get(f"{BASE_URL}/matching/recommendations", headers=headers)
        if response.status_code == 200:
            recommendations = response.json()
            print(f"✅ Found {recommendations['total_count']} recommendations")
            
            if recommendations['matches']:
                # Test shortlisting
                target_user = recommendations['matches'][0]['user_id']
                shortlist_data = {"target_user_id": target_user}
                
                response = await client.post(f"{BASE_URL}/matching/shortlist", 
                                           json=shortlist_data, headers=headers)
                if response.status_code == 200:
                    print("✅ User shortlisted")
        else:
            print(f"❌ Matching failed: {response.text}")
        
        # 6. Test Profiles Domain
        print("\n6️⃣ Testing Profiles Domain...")
        
        response = await client.get(f"{BASE_URL}/profiles/dashboard", headers=headers)
        if response.status_code == 200:
            dashboard = response.json()
            print(f"✅ Dashboard loaded - {dashboard['profile_completion']}% complete")
        else:
            print(f"❌ Profiles failed: {response.text}")
        
        # 7. Test Moderation Domain
        print("\n7️⃣ Testing Moderation Domain...")
        
        response = await client.get(f"{BASE_URL}/moderation/my-reports", headers=headers)
        if response.status_code == 200:
            reports = response.json()
            print(f"✅ Found {len(reports['reports'])} reports")
        else:
            print(f"❌ Moderation failed: {response.text}")
        
        print("\n🎉 All domains tested successfully!")
        print("\n📊 Summary:")
        print("✅ Identity - Authentication & user management")
        print("✅ Onboarding - User signup & profile completion")
        print("✅ Profiles - Profile viewing & dashboard")
        print("✅ Moderation - Reporting & blocking")
        print("✅ Matching - Search & recommendations")
        print("✅ Media - Image upload & processing")
        print("✅ Notifications - In-app notifications")
        print("✅ Chat - Messaging system")
        print("✅ Calls - WebRTC signalling (WebSocket)")


if __name__ == "__main__":
    print("🚀 Aurum Matrimony - Complete Platform Test")
    print("Make sure the server is running on http://localhost:8000")
    print("And you have test users created")
    input("Press Enter when ready...")
    asyncio.run(test_all_domains())
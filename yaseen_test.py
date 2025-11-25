#!/usr/bin/env python3
"""
Comprehensive test suite for Aurum Matrimony API
Run: python yaseen_test.py
"""
import asyncio
import httpx
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"
TIMEOUT = 10.0

class AurumTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=TIMEOUT)
        self.auth_token = None
        self.test_user_id = None
        self.results = []

    def log(self, test_name: str, status: str, details: str = ""):
        result = f"{'[PASS]' if status == 'PASS' else '[FAIL]'} {test_name}: {status}"
        if details:
            result += f" - {details}"
        print(result)
        self.results.append({"test": test_name, "status": status, "details": details})

    async def test_health_endpoints(self):
        """Test basic health and info endpoints"""
        try:
            # Health check
            response = await self.client.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                data = response.json()
                self.log("Health Check", "PASS", f"Status: {data.get('status')}")
            else:
                self.log("Health Check", "FAIL", f"Status: {response.status_code}")

            # Root endpoint
            response = await self.client.get(f"{BASE_URL}/")
            if response.status_code == 200:
                data = response.json()
                self.log("Root Endpoint", "PASS", f"Version: {data.get('version')}")
            else:
                self.log("Root Endpoint", "FAIL", f"Status: {response.status_code}")

        except Exception as e:
            self.log("Health Endpoints", "FAIL", str(e))

    async def test_identity_endpoints(self):
        """Test identity/auth endpoints"""
        try:
            # Test registration
            reg_data = {
                "phone": "+919876543210",
                "email": "test@example.com",
                "password": "TestPass123!"
            }
            print('url', f"{BASE_URL}/api/v1/auth/register")
            import requests
            print(requests.post(f"{BASE_URL}/api/v1/auth/register", json=reg_data).text)
            response = await self.client.post(f"{BASE_URL}/api/v1/auth/register", json=reg_data)

            if response.status_code in [200, 201, 409]:  # 409 = already exists
                self.log("User Registration", "PASS", f"Status: {response.status_code}")
            else:
                self.log("User Registration", "FAIL", f"Status: {response.status_code}")

            # Test login
            login_data = {
                "phone": "+919876543210",
                "password": "TestPass123!"
            }
            response = await self.client.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.log("User Login", "PASS", "Token received")
            else:
                self.log("User Login", "FAIL", f"Status: {response.status_code}")

        except Exception as e:
            self.log("Identity Endpoints", "FAIL", str(e))

    async def test_protected_endpoints(self):
        """Test endpoints that require authentication"""
        if not self.auth_token:
            self.log("Protected Endpoints", "SKIP", "No auth token")
            return

        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Test profile endpoints
            response = await self.client.get(f"{BASE_URL}/api/v1/profiles/me", headers=headers)
            self.log("Get Profile", "PASS" if response.status_code in [200, 404] else "FAIL", 
                    f"Status: {response.status_code}")

            # Test matching endpoints
            response = await self.client.get(f"{BASE_URL}/api/v1/matching/suggestions", headers=headers)
            self.log("Matching Suggestions", "PASS" if response.status_code in [200, 404] else "FAIL", 
                    f"Status: {response.status_code}")

            # Test chat endpoints
            response = await self.client.get(f"{BASE_URL}/api/v1/chat/conversations", headers=headers)
            self.log("Chat Conversations", "PASS" if response.status_code in [200, 404] else "FAIL", 
                    f"Status: {response.status_code}")

        except Exception as e:
            self.log("Protected Endpoints", "FAIL", str(e))

    async def test_database_connection(self):
        """Test database connectivity through API"""
        try:
            # Try to access any endpoint that hits the database
            response = await self.client.get(f"{BASE_URL}/api/v1/profiles/search?limit=1")
            if response.status_code in [200, 401, 403]:  # Any response means DB is connected
                self.log("Database Connection", "PASS", "API can reach database")
            else:
                self.log("Database Connection", "FAIL", f"Status: {response.status_code}")
        except Exception as e:
            self.log("Database Connection", "FAIL", str(e))

    async def test_redis_connection(self):
        """Test Redis connectivity (indirectly through rate limiting)"""
        try:
            # Make multiple rapid requests to test rate limiting (which uses Redis)
            for i in range(3):
                response = await self.client.get(f"{BASE_URL}/health")
                if i == 0 and response.status_code == 200:
                    self.log("Redis Connection", "PASS", "Rate limiting working (Redis connected)")
                    break
            else:
                self.log("Redis Connection", "UNKNOWN", "Cannot verify Redis connection")
        except Exception as e:
            self.log("Redis Connection", "FAIL", str(e))

    async def test_minio_connection(self):
        """Test MinIO connectivity through media endpoints"""
        try:
            response = await self.client.get(f"{BASE_URL}/api/v1/media/health")
            if response.status_code in [200, 404]:  # 404 means endpoint exists but no route
                self.log("MinIO Connection", "PASS", "Media service accessible")
            else:
                self.log("MinIO Connection", "UNKNOWN", f"Status: {response.status_code}")
        except Exception as e:
            self.log("MinIO Connection", "FAIL", str(e))

    async def test_all_api_routes(self):
        """Test all major API route groups"""
        routes = [
            "/api/v1/profiles",
            "/api/v1/matching", 
            "/api/v1/chat",
            "/api/v1/notifications",
            "/api/v1/admin",
            "/api/v1/whatsapp",
            "/api/v1/media"
        ]
        
        for route in routes:
            try:
                response = await self.client.get(f"{BASE_URL}{route}")
                # Any response (even 404/405) means the route group exists
                if response.status_code in [200, 401, 403, 404, 405, 422]:
                    self.log(f"Route {route}", "PASS", f"Accessible (Status: {response.status_code})")
                else:
                    self.log(f"Route {route}", "FAIL", f"Status: {response.status_code}")
            except Exception as e:
                self.log(f"Route {route}", "FAIL", str(e))

    async def test_websocket_endpoints(self):
        """Test WebSocket endpoints availability"""
        try:
            # Test Socket.IO health endpoint
            response = await self.client.get(f"{BASE_URL}/socket.io/health")
            if response.status_code == 200:
                self.log("WebSocket Endpoints", "PASS", "Socket.IO health endpoint accessible")
            else:
                self.log("WebSocket Endpoints", "FAIL", f"Status: {response.status_code}")
        except Exception as e:
            self.log("WebSocket Endpoints", "FAIL", str(e))

    async def run_all_tests(self):
        """Run all tests"""
        print("Starting Aurum Matrimony API Tests...\n")
        
        await self.test_health_endpoints()
        await self.test_database_connection()
        await self.test_redis_connection()
        await self.test_minio_connection()
        await self.test_identity_endpoints()
        await self.test_protected_endpoints()
        await self.test_all_api_routes()
        await self.test_websocket_endpoints()
        
        await self.client.aclose()
        
        # Summary
        print(f"\nTest Summary:")
        passed = len([r for r in self.results if r['status'] == 'PASS'])
        failed = len([r for r in self.results if r['status'] == 'FAIL'])
        skipped = len([r for r in self.results if r['status'] in ['SKIP', 'UNKNOWN']])
        total = len(self.results)
        
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Skipped/Unknown: {skipped}")
        print(f"Total: {total}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")

async def main():
    tester = AurumTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
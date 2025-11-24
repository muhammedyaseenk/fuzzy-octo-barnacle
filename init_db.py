#!/usr/bin/env python3
"""
Database initialization script for Aurum Matrimony
Run this to create all necessary tables
"""
import asyncio
import asyncpg
from app.core.config import settings


async def create_tables():
    """Create all database tables"""
    # Read the schema file
    with open('database_schema.sql', 'r') as f:
        schema_sql = f.read()
    
    # Connect to database
    conn = await asyncpg.connect(settings.ONBOARDING_POSTGRES_URL)
    
    try:
        # Execute schema
        await conn.execute(schema_sql)
        print("✅ Database tables created successfully!")
        
        # Create a test admin user (optional)
        admin_exists = await conn.fetchval(
            "SELECT id FROM users WHERE phone = $1", "+919999999999"
        )
        
        if not admin_exists:
            from app.core.security import get_password_hash
            hashed_password = get_password_hash("admin123")
            
            admin_id = await conn.fetchval("""
                INSERT INTO users (phone, email, hashed_password, role, is_active, admin_approved)
                VALUES ($1, $2, $3, 'admin', true, true)
                RETURNING id
            """, "+919999999999", "admin@aurum.com", hashed_password)
            
            await conn.execute("""
                INSERT INTO user_profiles (user_id, first_name, last_name)
                VALUES ($1, 'Admin', 'User')
            """, admin_id)
            
            print("✅ Admin user created:")
            print("   Phone: +919999999999")
            print("   Password: admin123")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(create_tables())
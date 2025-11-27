#!/usr/bin/env python3
"""Reset password for existing user in database"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.domains.identity.models import User
from app.core.security import get_password_hash
from app.core.config import settings

async def reset_user_password():
    # Create database connection
    engine = create_async_engine(settings.POSTGRES_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Pick one of the existing users
        result = await session.execute(select(User).where(User.phone == "+18547352813"))
        user = result.scalar_one_or_none()
        
        if user:
            print(f"Found user: {user.phone} ({user.email})")
            
            # Set a new password
            new_password = "Test@1234"
            user.hashed_password = get_password_hash(new_password)
            
            session.add(user)
            await session.commit()
            
            print(f"✓ Password reset to: {new_password}")
            print(f"✓ User is active: {user.is_active}")
            print(f"✓ User is approved: {user.admin_approved}")
        else:
            print("User not found!")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reset_user_password())

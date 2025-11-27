#!/usr/bin/env python3
"""Fix corrupted password hashes in database"""
import asyncio
import os
import sys
sys.path.insert(0, '/app')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.domains.identity.models import User
from app.core.security import get_password_hash
from app.core.config import settings

async def fix_passwords():
    # Create database connection
    engine = create_async_engine(settings.POSTGRES_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Generate correct hash
    password = "Test@1234"
    hashed_password = get_password_hash(password)
    
    print(f"Updating all users with password: {password}")
    print(f"Hash: {hashed_password}")
    
    async with async_session() as session:
        # Get all users
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        print(f"\nFound {len(users)} users to update\n")
        
        for user in users:
            old_hash = user.hashed_password
            user.hashed_password = hashed_password
            session.add(user)
            print(f"✓ Updated {user.phone} ({user.email})")
        
        await session.commit()
        print("\n✓ All users updated successfully!")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix_passwords())

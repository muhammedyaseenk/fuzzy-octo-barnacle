# app/core/session.py
import uuid
from datetime import datetime, timedelta
from typing import Optional
from app.core.db import get_pg_connection
from app.core.config import settings


class SessionManager:
    
    @staticmethod
    async def create_session(user_id: int, ip_address: str, user_agent: str) -> str:
        """Create new user session"""
        session_id = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(minutes=settings.SESSION_EXPIRE_MINUTES)
        
        async with get_pg_connection() as conn:
            await conn.execute("""
                INSERT INTO user_sessions (session_id, user_id, ip_address, user_agent, expires_at)
                VALUES ($1, $2, $3, $4, $5)
            """, session_id, user_id, ip_address, user_agent, expires_at)
        
        return session_id
    
    @staticmethod
    async def validate_session(session_id: str) -> Optional[int]:
        """Validate session and return user_id"""
        async with get_pg_connection() as conn:
            result = await conn.fetchrow("""
                SELECT user_id FROM user_sessions
                WHERE session_id = $1 AND expires_at > NOW()
            """, session_id)
            
            if result:
                # Update last activity
                await conn.execute("""
                    UPDATE user_sessions 
                    SET last_activity = NOW()
                    WHERE session_id = $1
                """, session_id)
                
                return result['user_id']
        
        return None
    
    @staticmethod
    async def invalidate_session(session_id: str):
        """Invalidate user session"""
        async with get_pg_connection() as conn:
            await conn.execute("""
                DELETE FROM user_sessions WHERE session_id = $1
            """, session_id)
    
    @staticmethod
    async def invalidate_all_user_sessions(user_id: int):
        """Invalidate all sessions for a user"""
        async with get_pg_connection() as conn:
            await conn.execute("""
                DELETE FROM user_sessions WHERE user_id = $1
            """, user_id)
    
    @staticmethod
    async def get_active_sessions(user_id: int) -> list:
        """Get all active sessions for a user"""
        async with get_pg_connection() as conn:
            results = await conn.fetch("""
                SELECT session_id, ip_address, user_agent, created_at, last_activity
                FROM user_sessions
                WHERE user_id = $1 AND expires_at > NOW()
                ORDER BY last_activity DESC
            """, user_id)
            
            return [dict(row) for row in results]
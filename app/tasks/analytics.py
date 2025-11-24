# app/tasks/analytics.py
from app.celery_app import celery_app
from app.core.db import get_pg_connection


@celery_app.task
async def cleanup_expired_sessions():
    """Cleanup expired user sessions"""
    async with get_pg_connection() as conn:
        await conn.execute("""
            DELETE FROM user_sessions 
            WHERE expires_at < NOW()
        """)
    print("Cleaned up expired sessions")


@celery_app.task
async def generate_daily_analytics():
    """Generate daily analytics reports"""
    async with get_pg_connection() as conn:
        stats = await conn.fetchrow("""
            SELECT 
                COUNT(DISTINCT id) as total_users,
                COUNT(DISTINCT CASE WHEN last_login > NOW() - INTERVAL '24 hours' THEN id END) as active_users,
                COUNT(DISTINCT CASE WHEN created_at > NOW() - INTERVAL '24 hours' THEN id END) as new_users
            FROM users
        """)
    print(f"Daily analytics: {dict(stats)}")


@celery_app.task
def track_user_activity(user_id: int, activity_type: str, metadata: dict = None):
    """Track user activity for analytics"""
    print(f"Tracking activity: {activity_type} for user {user_id}")
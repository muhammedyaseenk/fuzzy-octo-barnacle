# app/domains/engagement/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from app.domains.engagement.models import EngagementEvent, EventType, UserEngagementScore
from app.domains.onboarding.models import Profile
from app.core.cache import redis_client
from datetime import datetime, timedelta
import json
from app.core.cache import get_redis

class EngagementService:
    
    @staticmethod
    async def track_event(user_id: int, event_type: EventType, target_user_id: int = None, metadata: dict = None, db: AsyncSession = None):
        """Track engagement event"""
        event = EngagementEvent(
            user_id=user_id,
            event_type=event_type,
            target_user_id=target_user_id,
            metadata=json.dumps(metadata) if metadata else None
        )
        db.add(event)
        await db.commit()
        
        # Queue for processing
        # await redis_client.lpush("engagement_queue", json.dumps({
        redis = await get_redis()
        await redis.lpush("engagement_queue", json.dumps({
            "user_id": user_id,
            "event_type": event_type.value,
            "target_user_id": target_user_id,
            "metadata": metadata
        }))
    
    @staticmethod
    async def get_new_users_for_notification(gender: str, hours: int, db: AsyncSession):
        """Get new users joined in last N hours for notification"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        result = await db.execute(
            select(Profile).where(
                and_(
                    Profile.gender == gender,
                    Profile.verification_status == "approved",
                    Profile.created_at >= cutoff
                )
            ).limit(50)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_users_to_notify(target_gender: str, db: AsyncSession):
        """Get active users who should be notified about new profiles"""
        # Get users active in last 7 days
        cutoff = datetime.utcnow() - timedelta(days=7)
        
        result = await db.execute(
            select(Profile).where(
                and_(
                    Profile.gender != target_gender,
                    Profile.verification_status == "approved"
                )
            ).join(
                UserEngagementScore,
                Profile.user_id == UserEngagementScore.user_id
            ).where(
                UserEngagementScore.last_active >= cutoff
            ).limit(1000)
        )
        return result.scalars().all()
    
    @staticmethod
    async def update_engagement_score(user_id: int, db: AsyncSession):
        """Calculate and update user engagement score"""
        result = await db.execute(
            select(UserEngagementScore).where(UserEngagementScore.user_id == user_id)
        )
        score_record = result.scalar_one_or_none()
        
        if not score_record:
            score_record = UserEngagementScore(user_id=user_id)
            db.add(score_record)
        
        # Calculate score (0-100)
        score = 0
        score += min(score_record.profile_views * 2, 20)
        score += min(score_record.interests_sent * 5, 20)
        score += min(score_record.interests_received * 5, 20)
        score += min(score_record.messages_sent * 3, 15)
        score += min(score_record.messages_received * 3, 15)
        score += min(score_record.response_rate // 10, 10)
        
        score_record.engagement_score = min(score, 100)
        score_record.updated_at = datetime.utcnow()
        
        await db.commit()
        return score_record.engagement_score

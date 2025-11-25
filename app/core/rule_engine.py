# app/core/rule_engine.py
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.cache import redis_client
import json

class UserTier(str, Enum):
    FREE = "free"
    PREMIUM = "premium"
    ELITE = "elite"

class RuleEngine:
    """Business rules engine for permissions and features"""
    
    # Contact visibility rules
    CONTACT_RULES = {
        UserTier.FREE: {
            "can_view_contact": False,
            "requires_mutual_interest": True,
            "requires_admin_approval": True,
            "daily_profile_views": 10,
            "daily_interests": 5,
            "can_initiate_chat": False
        },
        UserTier.PREMIUM: {
            "can_view_contact": True,
            "requires_mutual_interest": False,
            "requires_admin_approval": False,
            "daily_profile_views": 100,
            "daily_interests": 50,
            "can_initiate_chat": True,
            "priority_support": True,
            "verified_badge": True
        },
        UserTier.ELITE: {
            "can_view_contact": True,
            "requires_mutual_interest": False,
            "requires_admin_approval": False,
            "daily_profile_views": -1,  # Unlimited
            "daily_interests": -1,
            "can_initiate_chat": True,
            "priority_support": True,
            "verified_badge": True,
            "featured_profile": True,
            "dedicated_manager": True
        }
    }
    
    @staticmethod
    async def can_view_contact(viewer_id: int, target_id: int, db: AsyncSession) -> tuple[bool, str]:
        """Check if user can view contact details"""
        viewer = await RuleEngine._get_user_tier(viewer_id, db)
        target = await RuleEngine._get_user_tier(target_id, db)
        
        viewer_rules = RuleEngine.CONTACT_RULES[viewer.tier]
        
        # Premium/Elite can always view
        if viewer_rules["can_view_contact"]:
            return True, "allowed"
        
        # Free users need mutual interest
        if viewer_rules["requires_mutual_interest"]:
            mutual = await RuleEngine._check_mutual_interest(viewer_id, target_id, db)
            if not mutual:
                return False, "requires_mutual_interest"
        
        # Check admin approval
        if viewer_rules["requires_admin_approval"]:
            approved = await RuleEngine._check_admin_approval(viewer_id, target_id, db)
            if not approved:
                return False, "requires_admin_approval"
        
        return True, "allowed"
    
    @staticmethod
    async def check_daily_limit(user_id: int, action: str, db: AsyncSession) -> tuple[bool, int]:
        """Check if user exceeded daily limits"""
        user = await RuleEngine._get_user_tier(user_id, db)
        rules = RuleEngine.CONTACT_RULES[user.tier]
        
        limit_key = f"daily_{action}"
        if limit_key not in rules:
            return True, -1
        
        limit = rules[limit_key]
        if limit == -1:  # Unlimited
            return True, -1
        
        # Check Redis counter
        cache_key = f"limit:{user_id}:{action}:{datetime.now().strftime('%Y%m%d')}"
        count = await redis_client.get(cache_key)
        current = int(count) if count else 0
        
        if current >= limit:
            return False, limit
        
        # Increment counter
        await redis_client.incr(cache_key)
        await redis_client.expire(cache_key, 86400)  # 24 hours
        
        return True, limit - current - 1
    
    @staticmethod
    async def can_initiate_chat(user_id: int, db: AsyncSession) -> bool:
        """Check if user can start chat"""
        user = await RuleEngine._get_user_tier(user_id, db)
        return RuleEngine.CONTACT_RULES[user.tier]["can_initiate_chat"]
    
    @staticmethod
    async def get_user_features(user_id: int, db: AsyncSession) -> Dict[str, Any]:
        """Get all features available to user"""
        user = await RuleEngine._get_user_tier(user_id, db)
        return RuleEngine.CONTACT_RULES[user.tier]
    
    @staticmethod
    async def _get_user_tier(user_id: int, db: AsyncSession):
        """Get user tier from cache or DB"""
        cache_key = f"user_tier:{user_id}"
        cached = await redis_client.get(cache_key)
        
        if cached:
            return json.loads(cached)
        
        from app.domains.identity.models import User
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return {"tier": UserTier.FREE}
        
        # Check subscription
        tier = UserTier.FREE
        if user.subscription_tier:
            tier = UserTier(user.subscription_tier)
        
        user_data = {"tier": tier, "id": user_id}
        await redis_client.setex(cache_key, 3600, json.dumps(user_data))
        return user_data
    
    @staticmethod
    async def _check_mutual_interest(user1_id: int, user2_id: int, db: AsyncSession) -> bool:
        """Check if both users showed interest"""
        from app.domains.matching.models import UserShortlist
        
        result = await db.execute(
            select(UserShortlist).where(
                and_(
                    UserShortlist.user_id == user1_id,
                    UserShortlist.target_user_id == user2_id
                )
            )
        )
        interest1 = result.scalar_one_or_none()
        
        result = await db.execute(
            select(UserShortlist).where(
                and_(
                    UserShortlist.user_id == user2_id,
                    UserShortlist.target_user_id == user1_id
                )
            )
        )
        interest2 = result.scalar_one_or_none()
        
        return interest1 is not None and interest2 is not None
    
    @staticmethod
    async def _check_admin_approval(viewer_id: int, target_id: int, db: AsyncSession) -> bool:
        """Check if admin approved contact sharing"""
        cache_key = f"admin_approval:{viewer_id}:{target_id}"
        cached = await redis_client.get(cache_key)
        
        if cached:
            return cached == "1"
        
        from app.domains.matching.models import ContactApproval
        result = await db.execute(
            select(ContactApproval).where(
                and_(
                    ContactApproval.requester_id == viewer_id,
                    ContactApproval.target_id == target_id,
                    ContactApproval.status == "approved"
                )
            )
        )
        approval = result.scalar_one_or_none()
        
        approved = approval is not None
        await redis_client.setex(cache_key, 3600, "1" if approved else "0")
        return approved

rule_engine = RuleEngine()

# app/tasks/engagement.py
from app.celery_app import celery_app
from app.core.db import AsyncSessionLocal
from app.domains.engagement.service import EngagementService
from app.domains.engagement.models import EventType
from app.tasks.notifications import send_push_notification_task
from app.core.cache import redis_client
import json

@celery_app.task(name="process_engagement_events")
def process_engagement_events():
    """Process queued engagement events and send notifications"""
    import asyncio
    asyncio.run(_process_events())

async def _process_events():
    async with AsyncSessionLocal() as db:
        while True:
            event_data = await redis_client.rpop("engagement_queue")
            if not event_data:
                break
            
            event = json.loads(event_data)
            event_type = event["event_type"]
            
            # Send appropriate notification
            if event_type == EventType.MESSAGE_RECEIVED.value:
                await _notify_message_received(event, db)
            elif event_type == EventType.INTEREST_RECEIVED.value:
                await _notify_interest_received(event, db)
            elif event_type == EventType.PROFILE_VIEWED.value:
                await _notify_profile_viewed(event, db)
            elif event_type == EventType.CONTACT_APPROVED.value:
                await _notify_contact_approved(event, db)

async def _notify_message_received(event, db):
    """Notify user about new message"""
    from app.tasks.notifications import send_push_notification_task
    send_push_notification_task.delay(
        user_id=event["user_id"],
        title="New Message",
        body=f"You have a new message",
        data={"type": "message", "sender_id": event["target_user_id"]}
    )

async def _notify_interest_received(event, db):
    """Notify user about interest"""
    from app.tasks.notifications import send_push_notification_task
    send_push_notification_task.delay(
        user_id=event["user_id"],
        title="Someone is interested!",
        body="A member showed interest in your profile",
        data={"type": "interest", "user_id": event["target_user_id"]}
    )

async def _notify_profile_viewed(event, db):
    """Notify premium users about profile views"""
    from app.core.rule_engine import rule_engine
    from app.tasks.notifications import send_push_notification_task
    features = await rule_engine.get_user_features(event["user_id"], db)
    
    if features.get("verified_badge"):  # Premium/Elite only
        send_push_notification_task.delay(
            user_id=event["user_id"],
            title="Profile View",
            body="Someone viewed your profile",
            data={"type": "profile_view"}
        )

async def _notify_contact_approved(event, db):
    """Notify user about contact approval"""
    from app.tasks.notifications import send_push_notification_task
    send_push_notification_task.delay(
        user_id=event["user_id"],
        title="Contact Approved!",
        body="You can now view contact details",
        data={"type": "contact_approved", "target_id": event["target_user_id"]}
    )

@celery_app.task(name="notify_new_users_joined")
def notify_new_users_joined():
    """Daily task: Notify users about new profiles matching their preference"""
    import asyncio
    asyncio.run(_notify_new_users())

async def _notify_new_users():
    async with AsyncSessionLocal() as db:
        # Get new brides (last 24 hours)
        new_brides = await EngagementService.get_new_users_for_notification("female", 24, db)
        
        if new_brides:
            # Notify grooms
            from app.tasks.notifications import send_push_notification_task
            grooms = await EngagementService.get_users_to_notify("female", db)
            for groom in grooms[:500]:  # Batch limit
                send_push_notification_task.delay(
                    user_id=groom.user_id,
                    title=f"{len(new_brides)} New Brides Joined!",
                    body="Check out new profiles matching your preferences",
                    data={"type": "new_users", "count": len(new_brides)}
                )
        
        # Get new grooms
        new_grooms = await EngagementService.get_new_users_for_notification("male", 24, db)
        
        if new_grooms:
            # Notify brides
            from app.tasks.notifications import send_push_notification_task
            brides = await EngagementService.get_users_to_notify("male", db)
            for bride in brides[:500]:
                send_push_notification_task.delay(
                    user_id=bride.user_id,
                    title=f"{len(new_grooms)} New Grooms Joined!",
                    body="Check out new profiles matching your preferences",
                    data={"type": "new_users", "count": len(new_grooms)}
                )

@celery_app.task(name="send_inactive_user_reminders")
def send_inactive_user_reminders():
    """Send reminders to inactive users"""
    import asyncio
    asyncio.run(_send_reminders())

async def _send_reminders():
    from datetime import datetime, timedelta
    from sqlalchemy import select, and_
    from app.domains.engagement.models import UserEngagementScore
    
    async with AsyncSessionLocal() as db:
        cutoff = datetime.utcnow() - timedelta(days=3)
        
        result = await db.execute(
            select(UserEngagementScore).where(
                and_(
                    UserEngagementScore.last_active < cutoff,
                    UserEngagementScore.engagement_score > 20
                )
            ).limit(1000)
        )
        inactive_users = result.scalars().all()
        
        from app.tasks.notifications import send_push_notification_task
        for user_score in inactive_users:
            send_push_notification_task.delay(
                user_id=user_score.user_id,
                title="We miss you!",
                body="New profiles are waiting for you. Come back and find your match!",
                data={"type": "re_engagement"}
            )

@celery_app.task(name="send_profile_completion_reminders")
def send_profile_completion_reminders():
    """Remind users with incomplete profiles"""
    import asyncio
    asyncio.run(_send_completion_reminders())

async def _send_completion_reminders():
    from sqlalchemy import select, and_
    from app.domains.onboarding.models import Profile
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Profile).where(
                and_(
                    Profile.verification_status == "pending",
                    Profile.created_at < datetime.utcnow() - timedelta(days=1)
                )
            ).limit(500)
        )
        incomplete_profiles = result.scalars().all()
        
        from app.tasks.notifications import send_push_notification_task
        for profile in incomplete_profiles:
            send_push_notification_task.delay(
                user_id=profile.user_id,
                title="Complete Your Profile",
                body="Complete your profile to get 10x more matches!",
                data={"type": "profile_completion"}
            )

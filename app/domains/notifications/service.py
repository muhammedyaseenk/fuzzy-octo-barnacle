# app/domains/notifications/service.py
from typing import List
from app.core.db import get_pg_connection
from app.domains.notifications.schemas import NotificationCreate, NotificationResponse


class NotificationService:
    
    @staticmethod
    async def create_notification(notification: NotificationCreate) -> int:
        """Create a new notification"""
        async with get_pg_connection() as conn:
            notification_id = await conn.fetchval("""
                INSERT INTO notifications (user_id, type, title, message, data)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """, notification.user_id, notification.type.value, 
                notification.title, notification.message, notification.data)
            
            return notification_id
    
    @staticmethod
    async def get_user_notifications(user_id: int, skip: int = 0, limit: int = 50) -> List[NotificationResponse]:
        """Get user notifications"""
        async with get_pg_connection() as conn:
            results = await conn.fetch("""
                SELECT id, type, title, message, data, is_read, created_at
                FROM notifications 
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """, user_id, limit, skip)
            
            return [
                NotificationResponse(
                    id=row['id'],
                    type=row['type'],
                    title=row['title'],
                    message=row['message'],
                    data=row['data'],
                    is_read=row['is_read'],
                    created_at=row['created_at']
                )
                for row in results
            ]
    
    @staticmethod
    async def mark_as_read(user_id: int, notification_ids: List[int]):
        """Mark notifications as read"""
        async with get_pg_connection() as conn:
            await conn.execute("""
                UPDATE notifications SET is_read = true
                WHERE user_id = $1 AND id = ANY($2)
            """, user_id, notification_ids)
    
    @staticmethod
    async def get_unread_count(user_id: int) -> int:
        """Get unread notification count"""
        async with get_pg_connection() as conn:
            count = await conn.fetchval("""
                SELECT COUNT(*) FROM notifications
                WHERE user_id = $1 AND is_read = false
            """, user_id)
            
            return count or 0
    
    # Helper methods for common notifications
    @staticmethod
    async def notify_message(user_id: int, sender_name: str):
        """Notify about new message"""
        notification = NotificationCreate(
            user_id=user_id,
            type="message",
            title="New Message",
            message=f"You have a new message from {sender_name}"
        )
        return await NotificationService.create_notification(notification)
    
    @staticmethod
    async def notify_profile_view(user_id: int, viewer_name: str):
        """Notify about profile view"""
        notification = NotificationCreate(
            user_id=user_id,
            type="profile_view",
            title="Profile Viewed",
            message=f"{viewer_name} viewed your profile"
        )
        return await NotificationService.create_notification(notification)
    
    @staticmethod
    async def notify_shortlist(user_id: int, shortlister_name: str):
        """Notify about being shortlisted"""
        notification = NotificationCreate(
            user_id=user_id,
            type="shortlist",
            title="Added to Shortlist",
            message=f"{shortlister_name} added you to their shortlist"
        )
        return await NotificationService.create_notification(notification)
    
    @staticmethod
    async def notify_verification(user_id: int, approved: bool):
        """Notify about verification status"""
        status = "approved" if approved else "rejected"
        notification = NotificationCreate(
            user_id=user_id,
            type="verification",
            title="Profile Verification",
            message=f"Your profile has been {status}"
        )
        return await NotificationService.create_notification(notification)
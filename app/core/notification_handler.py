# app/core/notification_handler.py
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, messaging
from app.core.config import settings
from app.core.cache import redis_client
import json

logger = logging.getLogger(__name__)

class NotificationHandler:
    """Graceful notification handling with fallback and admin alerts"""
    
    def __init__(self):
        self.fcm_initialized = False
        self.admin_alert_threshold = 10  # Alert admin after 10 failures
        self.failure_count_key = "notification_failures"
    
    def initialize_fcm(self):
        """Initialize Firebase Cloud Messaging"""
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(settings.FCM_CREDENTIALS_PATH)
                firebase_admin.initialize_app(cred)
            self.fcm_initialized = True
            logger.info("FCM initialized successfully")
        except Exception as e:
            logger.error(f"FCM initialization failed: {e}")
            self._alert_admin("FCM initialization failed", str(e))
    
    async def send_push(self, user_id: int, title: str, body: str, data: Dict = None) -> Dict[str, Any]:
        """Send push notification with graceful error handling"""
        try:
            # Get device tokens
            tokens = await self._get_device_tokens(user_id)
            if not tokens:
                return {"status": "no_devices", "user_id": user_id}
            
            # Try FCM
            if self.fcm_initialized:
                result = await self._send_fcm(tokens, title, body, data)
                if result["status"] == "success":
                    await self._reset_failure_count()
                    return result
            
            # Fallback: Store for later retry
            await self._queue_for_retry(user_id, title, body, data)
            return {"status": "queued_retry", "user_id": user_id}
            
        except Exception as e:
            logger.error(f"Push notification error for user {user_id}: {e}")
            await self._handle_failure(user_id, "push", str(e))
            return {"status": "failed", "error": str(e)}
    
    async def send_email(self, user_id: int, template: str, data: Dict) -> Dict[str, Any]:
        """Send email with graceful error handling"""
        try:
            from app.core.email_sender import EmailSender
            sender = EmailSender()
            result = await sender.send(user_id, template, data)
            
            if result["status"] == "success":
                await self._reset_failure_count()
                return result
            else:
                raise Exception(result.get("error", "Unknown error"))
                
        except Exception as e:
            logger.error(f"Email notification error for user {user_id}: {e}")
            await self._handle_failure(user_id, "email", str(e))
            
            # Fallback: Try SMS if email fails
            try:
                phone = await self._get_user_phone(user_id)
                if phone:
                    return await self.send_sms(phone, f"{template}: Check your account")
            except:
                pass
            
            return {"status": "failed", "error": str(e)}
    
    async def send_sms(self, phone: str, message: str) -> Dict[str, Any]:
        """Send SMS with graceful error handling"""
        try:
            from app.core.sms_sender import SMSSender
            sender = SMSSender()
            result = await sender.send(phone, message)
            
            if result["status"] == "success":
                await self._reset_failure_count()
                return result
            else:
                raise Exception(result.get("error", "Unknown error"))
                
        except Exception as e:
            logger.error(f"SMS notification error for {phone}: {e}")
            await self._handle_failure(None, "sms", str(e))
            return {"status": "failed", "error": str(e)}
    
    async def _send_fcm(self, tokens: list, title: str, body: str, data: Dict = None) -> Dict[str, Any]:
        """Send via Firebase Cloud Messaging"""
        try:
            message = messaging.MulticastMessage(
                notification=messaging.Notification(title=title, body=body),
                data=data or {},
                tokens=tokens
            )
            
            response = messaging.send_multicast(message)
            
            # Handle failed tokens
            if response.failure_count > 0:
                failed_tokens = [
                    tokens[idx] for idx, resp in enumerate(response.responses)
                    if not resp.success
                ]
                await self._deactivate_tokens(failed_tokens)
            
            return {
                "status": "success",
                "success_count": response.success_count,
                "failure_count": response.failure_count
            }
            
        except Exception as e:
            logger.error(f"FCM send error: {e}")
            raise
    
    async def _get_device_tokens(self, user_id: int) -> list:
        """Get active device tokens for user"""
        from app.core.db import AsyncSessionLocal
        from sqlalchemy import text
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("SELECT device_token FROM user_devices WHERE user_id = :uid AND is_active = true"),
                {"uid": user_id}
            )
            return [row[0] for row in result.fetchall()]
    
    async def _get_user_phone(self, user_id: int) -> Optional[str]:
        """Get user phone number"""
        from app.core.db import AsyncSessionLocal
        from sqlalchemy import text
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("SELECT phone FROM users WHERE id = :uid"),
                {"uid": user_id}
            )
            row = result.fetchone()
            return row[0] if row else None
    
    async def _deactivate_tokens(self, tokens: list):
        """Deactivate invalid device tokens"""
        from app.core.db import AsyncSessionLocal
        from sqlalchemy import text
        
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("UPDATE user_devices SET is_active = false WHERE device_token = ANY(:tokens)"),
                {"tokens": tokens}
            )
            await db.commit()
    
    async def _queue_for_retry(self, user_id: int, title: str, body: str, data: Dict):
        """Queue notification for retry"""
        retry_data = {
            "user_id": user_id,
            "title": title,
            "body": body,
            "data": data,
            "queued_at": datetime.utcnow().isoformat()
        }
        await redis_client.lpush("notification_retry_queue", json.dumps(retry_data))
    
    async def _handle_failure(self, user_id: Optional[int], channel: str, error: str):
        """Handle notification failure and alert admin if threshold reached"""
        # Increment failure count
        count = await redis_client.incr(self.failure_count_key)
        await redis_client.expire(self.failure_count_key, 3600)  # Reset hourly
        
        # Log failure
        await self._log_failure(user_id, channel, error)
        
        # Alert admin if threshold reached
        if count >= self.admin_alert_threshold:
            await self._alert_admin(
                f"Notification failures threshold reached",
                f"Channel: {channel}, Count: {count}, Last error: {error}"
            )
            await redis_client.delete(self.failure_count_key)  # Reset after alert
    
    async def _log_failure(self, user_id: Optional[int], channel: str, error: str):
        """Log notification failure to database"""
        from app.core.db import AsyncSessionLocal
        from sqlalchemy import text
        
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("""
                        INSERT INTO notification_failures 
                        (user_id, channel, error_message, created_at)
                        VALUES (:uid, :channel, :error, NOW())
                    """),
                    {"uid": user_id, "channel": channel, "error": error}
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to log notification failure: {e}")
    
    async def _alert_admin(self, subject: str, details: str):
        """Send alert to admin via multiple channels"""
        admin_alert = {
            "subject": subject,
            "details": details,
            "timestamp": datetime.utcnow().isoformat(),
            "severity": "high"
        }
        
        # Store in Redis for admin dashboard
        await redis_client.lpush("admin_alerts", json.dumps(admin_alert))
        await redis_client.ltrim("admin_alerts", 0, 99)  # Keep last 100
        
        # Log to file
        logger.critical(f"ADMIN ALERT: {subject} - {details}")
        
        # Try to send email to admin
        try:
            admin_emails = settings.ADMIN_EMAILS.split(",")
            for email in admin_emails:
                await self._send_admin_email(email, subject, details)
        except Exception as e:
            logger.error(f"Failed to send admin alert email: {e}")
    
    async def _send_admin_email(self, email: str, subject: str, details: str):
        """Send email to admin (simplified)"""
        # This would use your email service
        logger.info(f"Admin alert email to {email}: {subject}")
    
    async def _reset_failure_count(self):
        """Reset failure count after successful send"""
        await redis_client.delete(self.failure_count_key)

notification_handler = NotificationHandler()

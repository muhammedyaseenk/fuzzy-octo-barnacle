# app/core/whatsapp_sender.py
import aiohttp
from typing import Dict, Any
from app.core.config import settings
from app.core.content_moderator import content_moderator
from app.core.rule_engine import rule_engine, UserTier
import logging

logger = logging.getLogger(__name__)

class WhatsAppSender:
    """WhatsApp Business API sender - Premium users only"""
    
    def __init__(self):
        self.api_url = f"https://graph.facebook.com/v18.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        self.enabled = bool(settings.WHATSAPP_ACCESS_TOKEN)
    
    async def send_message(self, sender_id: int, recipient_id: int, message: str, db) -> Dict[str, Any]:
        """
        Send WhatsApp message with security checks
        1. Verify premium tier
        2. Content moderation (AI + patterns)
        3. Admin approval if needed
        4. Send via WhatsApp Business API
        """
        
        # Step 1: Verify sender is premium/elite
        sender_tier = await rule_engine._get_user_tier(sender_id, db)
        if sender_tier["tier"] not in [UserTier.PREMIUM, UserTier.ELITE]:
            return {
                "status": "forbidden",
                "error": "WhatsApp messaging is only available for Premium and Elite members"
            }
        
        # Step 2: Get recipient phone number
        recipient_phone = await self._get_user_whatsapp(recipient_id, db)
        if not recipient_phone:
            return {
                "status": "no_whatsapp",
                "error": "Recipient has not provided WhatsApp number"
            }
        
        # Step 3: Content moderation (CRITICAL SECURITY)
        moderation_result = await content_moderator.moderate_message(sender_id, recipient_id, message)
        
        if not moderation_result["approved"]:
            if moderation_result["requires_admin"]:
                return {
                    "status": "pending_review",
                    "message": "Your message is under review by our team for safety compliance"
                }
            else:
                return {
                    "status": "blocked",
                    "error": "Message blocked for policy violation"
                }
        
        # Step 4: Send via WhatsApp Business API
        if not self.enabled:
            return {"status": "disabled", "error": "WhatsApp service not configured"}
        
        try:
            result = await self._send_whatsapp_api(recipient_phone, message)
            
            # Log successful send
            await self._log_sent_message(sender_id, recipient_id, message, result.get("message_id"))
            
            # Track cost
            await self._track_cost(sender_id, "whatsapp_message")
            
            return {
                "status": "sent",
                "message_id": result.get("message_id"),
                "cost": 0.005  # $0.005 per message
            }
            
        except Exception as e:
            logger.error(f"WhatsApp send error: {e}")
            await self._alert_admin_send_failure(sender_id, recipient_id, str(e))
            return {
                "status": "failed",
                "error": "Failed to send WhatsApp message"
            }
    
    async def _send_whatsapp_api(self, phone: str, message: str) -> Dict:
        """Send via WhatsApp Business API"""
        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": message}
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.api_url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return {"message_id": data["messages"][0]["id"]}
                else:
                    error = await response.text()
                    raise Exception(f"WhatsApp API error: {error}")
    
    async def _get_user_whatsapp(self, user_id: int, db) -> str:
        """Get user's WhatsApp number"""
        from sqlalchemy import text
        
        result = await db.execute(
            text("SELECT whatsapp FROM users WHERE id = :uid"),
            {"uid": user_id}
        )
        row = result.fetchone()
        return row[0] if row and row[0] else None
    
    async def _log_sent_message(self, sender_id: int, recipient_id: int, message: str, message_id: str):
        """Log sent WhatsApp message"""
        from app.core.db import AsyncSessionLocal
        from sqlalchemy import text
        
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("""
                    INSERT INTO whatsapp_message_log 
                    (sender_id, recipient_id, message_content, whatsapp_message_id, status, created_at)
                    VALUES (:sender, :recipient, :message, :msg_id, 'sent', NOW())
                """),
                {
                    "sender": sender_id,
                    "recipient": recipient_id,
                    "message": message,
                    "msg_id": message_id
                }
            )
            await db.commit()
    
    async def _track_cost(self, user_id: int, service: str):
        """Track WhatsApp usage cost"""
        from app.core.cache import redis_client
        
        # Increment monthly cost
        month_key = f"whatsapp_cost:{user_id}:{datetime.now().strftime('%Y%m')}"
        await redis_client.incrbyfloat(month_key, 0.005)
        await redis_client.expire(month_key, 86400 * 60)  # 60 days
        
        # Alert admin if cost exceeds threshold
        cost = float(await redis_client.get(month_key) or 0)
        if cost > 100:  # $100/month threshold
            await self._alert_admin_high_cost(user_id, cost)
    
    async def _alert_admin_send_failure(self, sender_id: int, recipient_id: int, error: str):
        """Alert admin of send failure"""
        from app.core.cache import redis_client
        import json
        
        alert = {
            "subject": "WhatsApp send failure",
            "details": f"Failed to send from user {sender_id} to {recipient_id}: {error}",
            "timestamp": str(datetime.utcnow()),
            "severity": "high"
        }
        
        await redis_client.lpush("admin_alerts", json.dumps(alert))
    
    async def _alert_admin_high_cost(self, user_id: int, cost: float):
        """Alert admin of high WhatsApp costs"""
        from app.core.cache import redis_client
        import json
        
        alert = {
            "subject": "High WhatsApp usage cost",
            "details": f"User {user_id} has incurred ${cost:.2f} in WhatsApp costs this month",
            "timestamp": str(datetime.utcnow()),
            "severity": "medium"
        }
        
        await redis_client.lpush("admin_alerts", json.dumps(alert))

whatsapp_sender = WhatsAppSender()

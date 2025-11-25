# app/core/content_moderator.py
import re
from typing import Dict, Tuple
import openai
from app.core.config import settings
from app.core.cache import redis_client
import logging

logger = logging.getLogger(__name__)

class ContentModerator:
    """AI-powered content moderation for WhatsApp messages"""
    
    # Harmful patterns (regex-based first line of defense)
    HARMFUL_PATTERNS = [
        r'\b(kill|murder|harm|hurt|attack|violence)\b',
        r'\b(scam|fraud|cheat|steal|money\s*transfer)\b',
        r'\b(sex|porn|nude|explicit)\b',
        r'\b(drug|cocaine|heroin|marijuana)\b',
        r'\b(bomb|weapon|gun|knife)\b',
        r'\b(hate|racist|terrorist)\b',
        r'(\d{16})',  # Credit card numbers
        r'(\d{3}[-.\s]?\d{2}[-.\s]?\d{4})',  # SSN
        r'(password|passwd|pwd)\s*[:=]\s*\S+',  # Password sharing
    ]
    
    # Suspicious patterns (require AI review)
    SUSPICIOUS_PATTERNS = [
        r'\b(meet|hotel|room|private|alone)\b',
        r'\b(money|cash|payment|bank|account)\b',
        r'\b(urgent|emergency|help|please)\b',
        r'(whatsapp|telegram|signal|wickr)',  # External messaging
        r'(\+?\d{10,15})',  # Phone numbers
        r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',  # Email
    ]
    
    def __init__(self):
        self.openai_enabled = False
        try:
            openai.api_key = settings.OPENAI_API_KEY
            self.openai_enabled = True
        except:
            logger.warning("OpenAI not configured - using pattern matching only")
    
    async def moderate_message(self, sender_id: int, recipient_id: int, message: str) -> Dict:
        """
        Moderate message before sending to WhatsApp
        Returns: {"approved": bool, "reason": str, "requires_admin": bool}
        """
        
        # Check cache for repeat offenders
        if await self._is_blocked_user(sender_id):
            return {
                "approved": False,
                "reason": "User blocked for policy violations",
                "requires_admin": False
            }
        
        # Step 1: Pattern-based filtering (instant block)
        harmful_match = self._check_harmful_patterns(message)
        if harmful_match:
            await self._log_violation(sender_id, recipient_id, message, harmful_match, "harmful")
            await self._alert_admin_critical(sender_id, message, harmful_match)
            return {
                "approved": False,
                "reason": f"Harmful content detected: {harmful_match}",
                "requires_admin": False
            }
        
        # Step 2: Suspicious pattern check
        suspicious_match = self._check_suspicious_patterns(message)
        if suspicious_match:
            # Queue for AI review
            if self.openai_enabled:
                ai_result = await self._ai_moderate(message)
                if not ai_result["safe"]:
                    await self._log_violation(sender_id, recipient_id, message, ai_result["reason"], "ai_flagged")
                    await self._queue_admin_review(sender_id, recipient_id, message, ai_result["reason"])
                    return {
                        "approved": False,
                        "reason": "Message requires admin approval",
                        "requires_admin": True
                    }
            else:
                # No AI - queue for manual review
                await self._queue_admin_review(sender_id, recipient_id, message, suspicious_match)
                return {
                    "approved": False,
                    "reason": "Message requires admin approval",
                    "requires_admin": True
                }
        
        # Step 3: AI safety check (for all messages)
        if self.openai_enabled:
            ai_result = await self._ai_moderate(message)
            if not ai_result["safe"]:
                await self._log_violation(sender_id, recipient_id, message, ai_result["reason"], "ai_flagged")
                await self._queue_admin_review(sender_id, recipient_id, message, ai_result["reason"])
                return {
                    "approved": False,
                    "reason": "Message requires admin approval",
                    "requires_admin": True
                }
        
        # Approved
        await self._log_approved(sender_id, recipient_id, message)
        return {
            "approved": True,
            "reason": "Message approved",
            "requires_admin": False
        }
    
    def _check_harmful_patterns(self, message: str) -> str:
        """Check for harmful content patterns"""
        message_lower = message.lower()
        for pattern in self.HARMFUL_PATTERNS:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                return f"Pattern: {pattern}"
        return None
    
    def _check_suspicious_patterns(self, message: str) -> str:
        """Check for suspicious content patterns"""
        message_lower = message.lower()
        suspicious_count = 0
        matched_patterns = []
        
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                suspicious_count += 1
                matched_patterns.append(pattern)
        
        # Flag if 2+ suspicious patterns
        if suspicious_count >= 2:
            return f"Multiple suspicious patterns: {', '.join(matched_patterns[:3])}"
        
        return None
    
    async def _ai_moderate(self, message: str) -> Dict:
        """Use OpenAI to moderate content"""
        try:
            response = openai.Moderation.create(input=message)
            result = response["results"][0]
            
            if result["flagged"]:
                categories = [cat for cat, flagged in result["categories"].items() if flagged]
                return {
                    "safe": False,
                    "reason": f"AI flagged: {', '.join(categories)}"
                }
            
            # Additional GPT-4 check for context
            gpt_response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a content moderator for a premium matrimony platform. Analyze if this message is appropriate for WhatsApp communication between potential matches. Consider: safety, appropriateness, scam indicators, harmful intent. Respond with SAFE or UNSAFE followed by reason."},
                    {"role": "user", "content": message}
                ],
                max_tokens=100,
                temperature=0
            )
            
            gpt_result = gpt_response.choices[0].message.content.strip()
            
            if gpt_result.startswith("UNSAFE"):
                return {
                    "safe": False,
                    "reason": gpt_result.replace("UNSAFE", "").strip()
                }
            
            return {"safe": True, "reason": "AI approved"}
            
        except Exception as e:
            logger.error(f"AI moderation error: {e}")
            # Fail safe - require admin review on error
            return {"safe": False, "reason": "AI moderation unavailable"}
    
    async def _is_blocked_user(self, user_id: int) -> bool:
        """Check if user is blocked"""
        blocked = await redis_client.get(f"blocked_user:{user_id}")
        return blocked == "1"
    
    async def _log_violation(self, sender_id: int, recipient_id: int, message: str, reason: str, severity: str):
        """Log content violation"""
        from app.core.db import AsyncSessionLocal
        from sqlalchemy import text
        
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("""
                    INSERT INTO content_violations 
                    (sender_id, recipient_id, message_content, violation_reason, severity, created_at)
                    VALUES (:sender, :recipient, :message, :reason, :severity, NOW())
                """),
                {
                    "sender": sender_id,
                    "recipient": recipient_id,
                    "message": message,
                    "reason": reason,
                    "severity": severity
                }
            )
            await db.commit()
        
        # Increment violation count
        count = await redis_client.incr(f"violation_count:{sender_id}")
        
        # Auto-block after 3 violations
        if count >= 3:
            await redis_client.setex(f"blocked_user:{sender_id}", 86400 * 7, "1")  # 7 days
            await self._alert_admin_critical(sender_id, message, f"User auto-blocked after {count} violations")
    
    async def _log_approved(self, sender_id: int, recipient_id: int, message: str):
        """Log approved message"""
        from app.core.db import AsyncSessionLocal
        from sqlalchemy import text
        
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("""
                    INSERT INTO whatsapp_message_log 
                    (sender_id, recipient_id, message_content, status, created_at)
                    VALUES (:sender, :recipient, :message, 'approved', NOW())
                """),
                {
                    "sender": sender_id,
                    "recipient": recipient_id,
                    "message": message
                }
            )
            await db.commit()
    
    async def _queue_admin_review(self, sender_id: int, recipient_id: int, message: str, reason: str):
        """Queue message for admin review"""
        import json
        
        review_data = {
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "message": message,
            "reason": reason,
            "timestamp": str(datetime.utcnow())
        }
        
        await redis_client.lpush("whatsapp_admin_review_queue", json.dumps(review_data))
        
        # Alert admin
        await self._alert_admin_review_needed(sender_id, message, reason)
    
    async def _alert_admin_critical(self, sender_id: int, message: str, reason: str):
        """Send critical alert to admin"""
        from app.core.notification_handler import notification_handler
        
        alert = {
            "subject": "CRITICAL: Harmful content detected",
            "details": f"User {sender_id} attempted to send harmful content: {reason}",
            "message_preview": message[:100],
            "timestamp": str(datetime.utcnow()),
            "severity": "critical"
        }
        
        await redis_client.lpush("admin_alerts", json.dumps(alert))
        logger.critical(f"HARMFUL CONTENT: User {sender_id} - {reason}")
    
    async def _alert_admin_review_needed(self, sender_id: int, message: str, reason: str):
        """Alert admin that review is needed"""
        alert = {
            "subject": "WhatsApp message requires review",
            "details": f"User {sender_id} message flagged: {reason}",
            "message_preview": message[:100],
            "timestamp": str(datetime.utcnow()),
            "severity": "medium"
        }
        
        await redis_client.lpush("admin_alerts", json.dumps(alert))

content_moderator = ContentModerator()

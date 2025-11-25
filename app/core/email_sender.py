# app/core/email_sender.py
import boto3
from typing import Dict, Any
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class EmailSender:
    """Email sender using AWS SES with fallback"""
    
    def __init__(self):
        try:
            self.ses_client = boto3.client(
                'ses',
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
            self.enabled = True
        except Exception as e:
            logger.error(f"SES initialization failed: {e}")
            self.enabled = False
    
    async def send(self, user_id: int, template: str, data: Dict) -> Dict[str, Any]:
        """Send email via SES"""
        if not self.enabled:
            return {"status": "disabled", "error": "SES not configured"}
        
        try:
            # Get user email
            from app.core.db import AsyncSessionLocal
            from sqlalchemy import text
            
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("SELECT email, first_name FROM users u LEFT JOIN profiles p ON u.id = p.user_id WHERE u.id = :uid"),
                    {"uid": user_id}
                )
                row = result.fetchone()
                
                if not row or not row[0]:
                    return {"status": "no_email", "user_id": user_id}
                
                email, first_name = row[0], row[1] or "User"
            
            # Get template
            subject, body = self._get_template(template, first_name, data)
            
            # Send via SES
            response = self.ses_client.send_email(
                Source=settings.EMAIL_FROM,
                Destination={'ToAddresses': [email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {'Html': {'Data': body, 'Charset': 'UTF-8'}}
                }
            )
            
            return {
                "status": "success",
                "message_id": response['MessageId'],
                "email": email
            }
            
        except Exception as e:
            logger.error(f"Email send error: {e}")
            return {"status": "error", "error": str(e)}
    
    def _get_template(self, template: str, first_name: str, data: Dict) -> tuple:
        """Get email template"""
        templates = {
            "daily_matches": (
                "Your Daily Matches Are Here!",
                f"<h2>Hi {first_name},</h2><p>We found {data.get('count', 0)} great matches for you!</p>"
            ),
            "new_message": (
                "You Have a New Message",
                f"<h2>Hi {first_name},</h2><p>You received a new message. Login to view it.</p>"
            ),
            "interest_received": (
                "Someone is Interested!",
                f"<h2>Hi {first_name},</h2><p>A member showed interest in your profile!</p>"
            ),
            "profile_approved": (
                "Profile Approved",
                f"<h2>Hi {first_name},</h2><p>Your profile has been approved and is now live!</p>"
            )
        }
        
        return templates.get(template, ("Notification", f"<p>Hi {first_name}, you have a new notification.</p>"))

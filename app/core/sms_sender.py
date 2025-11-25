# app/core/sms_sender.py
import boto3
from typing import Dict, Any
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class SMSSender:
    """SMS sender using AWS SNS with Twilio fallback"""
    
    def __init__(self):
        self.sns_enabled = False
        self.twilio_enabled = False
        
        # Try AWS SNS
        try:
            self.sns_client = boto3.client(
                'sns',
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
            self.sns_enabled = True
        except Exception as e:
            logger.error(f"SNS initialization failed: {e}")
        
        # Try Twilio as fallback
        try:
            from twilio.rest import Client
            self.twilio_client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            self.twilio_enabled = True
        except Exception as e:
            logger.error(f"Twilio initialization failed: {e}")
    
    async def send(self, phone: str, message: str) -> Dict[str, Any]:
        """Send SMS via SNS or Twilio"""
        
        # Try SNS first
        if self.sns_enabled:
            try:
                response = self.sns_client.publish(
                    PhoneNumber=phone,
                    Message=message
                )
                return {
                    "status": "success",
                    "provider": "sns",
                    "message_id": response['MessageId']
                }
            except Exception as e:
                logger.error(f"SNS send failed: {e}")
        
        # Fallback to Twilio
        if self.twilio_enabled:
            try:
                message_obj = self.twilio_client.messages.create(
                    body=message,
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=phone
                )
                return {
                    "status": "success",
                    "provider": "twilio",
                    "message_id": message_obj.sid
                }
            except Exception as e:
                logger.error(f"Twilio send failed: {e}")
                return {"status": "error", "error": str(e)}
        
        return {"status": "disabled", "error": "No SMS provider configured"}

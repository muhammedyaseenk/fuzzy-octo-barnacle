# app/tasks/notifications.py
import asyncio
import json
from typing import Dict, List, Optional
from datetime import datetime
from celery import current_task
from app.celery_app import celery_app
from app.domains.notifications.service import NotificationService
from app.core.db import get_pg_connection


@celery_app.task(bind=True, retry_backoff=True, max_retries=3, rate_limit='100/m')
def send_push_notification(self, user_id: int, title: str, message: str, data: dict = None):
    """Send push notification via FCM/APNs"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_send_push_notification_async(user_id, title, message, data))


async def _send_push_notification_async(user_id: int, title: str, message: str, data: dict = None):
    """Async implementation of push notification"""
    try:
        async with get_pg_connection() as conn:
            # Get user's FCM/APNs tokens
            tokens = await conn.fetch("""
                SELECT device_token, device_type, is_active
                FROM user_devices
                WHERE user_id = $1 AND is_active = true
            """, user_id)
            
            if not tokens:
                return {"status": "no_devices", "user_id": user_id}
            
            sent_count = 0
            failed_tokens = []
            
            for token_row in tokens:
                try:
                    # FCM implementation (placeholder)
                    if token_row['device_type'] == 'android':
                        # import firebase_admin
                        # from firebase_admin import messaging
                        # message = messaging.Message(
                        #     notification=messaging.Notification(title=title, body=message),
                        #     data=data or {},
                        #     token=token_row['device_token']
                        # )
                        # response = messaging.send(message)
                        sent_count += 1
                    
                    # APNs implementation (placeholder)
                    elif token_row['device_type'] == 'ios':
                        # from aioapns import APNs, NotificationRequest
                        # apns = APNs(...)
                        # request = NotificationRequest(
                        #     device_token=token_row['device_token'],
                        #     message={"aps": {"alert": {"title": title, "body": message}}}
                        # )
                        # await apns.send_notification(request)
                        sent_count += 1
                    
                except Exception as e:
                    print(f"Failed to send to token {token_row['device_token'][:10]}...: {e}")
                    failed_tokens.append(token_row['device_token'])
            
            # Deactivate failed tokens
            if failed_tokens:
                await conn.execute("""
                    UPDATE user_devices SET is_active = false
                    WHERE device_token = ANY($1)
                """, failed_tokens)
            
            # Log notification
            await conn.execute("""
                INSERT INTO notification_logs (user_id, type, title, message, sent_at, status)
                VALUES ($1, 'push', $2, $3, NOW(), $4)
            """, user_id, title, message, 'sent' if sent_count > 0 else 'failed')
            
            return {
                "status": "sent" if sent_count > 0 else "failed",
                "user_id": user_id,
                "devices_sent": sent_count,
                "devices_failed": len(failed_tokens)
            }
    
    except Exception as exc:
        print(f"Push notification error for user {user_id}: {exc}")
        raise


@celery_app.task(bind=True, retry_backoff=True, max_retries=3, rate_limit='50/m')
def send_email_notification(self, user_id: int, template: str, data: dict):
    """Send email notification via SES/SendGrid"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_send_email_notification_async(user_id, template, data))


async def _send_email_notification_async(user_id: int, template: str, data: dict):
    """Async implementation of email notification"""
    try:
        async with get_pg_connection() as conn:
            # Get user email
            user = await conn.fetchrow("""
                SELECT u.email, p.first_name, p.last_name
                FROM users u
                JOIN user_profiles p ON u.id = p.user_id
                WHERE u.id = $1 AND u.email IS NOT NULL
            """, user_id)
            
            if not user or not user['email']:
                return {"status": "no_email", "user_id": user_id}
            
            # Email templates
            templates = {
                "daily_matches": {
                    "subject": "Your Daily Matches Are Here!",
                    "body": _render_daily_matches_email(user['first_name'], data.get('matches', []))
                },
                "profile_approved": {
                    "subject": "Your Profile Has Been Approved!",
                    "body": f"Hi {user['first_name']}, your profile has been approved and is now live."
                },
                "new_message": {
                    "subject": "You Have a New Message",
                    "body": f"Hi {user['first_name']}, you have received a new message."
                },
                "profile_view": {
                    "subject": "Someone Viewed Your Profile",
                    "body": f"Hi {user['first_name']}, someone viewed your profile."
                }
            }
            
            email_content = templates.get(template, {
                "subject": "Notification from Aurum Matrimony",
                "body": "You have a new notification."
            })
            
            # AWS SES implementation (placeholder)
            # import boto3
            # ses = boto3.client('ses', region_name='us-east-1')
            # response = ses.send_email(
            #     Source='noreply@aurummatrimony.com',
            #     Destination={'ToAddresses': [user['email']]},
            #     Message={
            #         'Subject': {'Data': email_content['subject']},
            #         'Body': {'Html': {'Data': email_content['body']}}
            #     }
            # )
            
            # Log email
            await conn.execute("""
                INSERT INTO notification_logs (user_id, type, title, message, sent_at, status)
                VALUES ($1, 'email', $2, $3, NOW(), 'sent')
            """, user_id, email_content['subject'], template)
            
            return {
                "status": "sent",
                "user_id": user_id,
                "email": user['email'],
                "template": template
            }
    
    except Exception as exc:
        print(f"Email notification error for user {user_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)


def _render_daily_matches_email(first_name: str, matches: List[Dict]) -> str:
    """Render daily matches email HTML"""
    html = f"""
    <html>
    <body>
        <h2>Hi {first_name},</h2>
        <p>We found some great matches for you today!</p>
        <div style="margin: 20px 0;">
    """
    
    for match in matches[:5]:
        html += f"""
        <div style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px;">
            <h3>{match.get('first_name', '')} {match.get('last_name', '')}</h3>
            <p><strong>Age:</strong> {match.get('age', 'N/A')} | <strong>Height:</strong> {match.get('height', 'N/A')} cm</p>
            <p><strong>Occupation:</strong> {match.get('occupation', 'N/A')}</p>
            <p><strong>Location:</strong> {match.get('location', 'N/A')}</p>
        </div>
        """
    
    html += """
        </div>
        <p><a href="https://aurummatrimony.com/matches" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View All Matches</a></p>
        <p>Best regards,<br>Aurum Matrimony Team</p>
    </body>
    </html>
    """
    
    return html


@celery_app.task(bind=True, retry_backoff=True, max_retries=3, rate_limit='100/m')
def send_sms_notification(self, phone: str, message: str):
    """Send SMS notification via Twilio/AWS SNS"""
    try:
        # Twilio implementation (placeholder)
        # from twilio.rest import Client
        # client = Client(account_sid, auth_token)
        # message = client.messages.create(
        #     body=message,
        #     from_='+1234567890',
        #     to=phone
        # )
        
        # AWS SNS implementation (placeholder)
        # import boto3
        # sns = boto3.client('sns', region_name='us-east-1')
        # response = sns.publish(
        #     PhoneNumber=phone,
        #     Message=message
        # )
        
        print(f"SMS sent to {phone}: {message}")
        return {"status": "sent", "phone": phone}
    
    except Exception as exc:
        print(f"SMS error for {phone}: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(rate_limit='10/m')
def create_notification_batch(user_ids: list, notification_type: str, title: str, message: str, data: dict = None):
    """Create notifications for multiple users with rate limiting"""
    # Split into chunks to avoid overwhelming the queue
    chunk_size = 100
    for i in range(0, len(user_ids), chunk_size):
        chunk = user_ids[i:i + chunk_size]
        for user_id in chunk:
            create_notification.apply_async(
                args=[user_id, notification_type, title, message, data],
                countdown=i // chunk_size * 5  # Stagger execution
            )
    
    return {"status": "queued", "total_users": len(user_ids)}


@celery_app.task(bind=True, retry_backoff=True, max_retries=3)
def create_notification(self, user_id: int, notification_type: str, title: str, message: str, data: dict = None):
    """Create in-app notification"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_create_notification_async(user_id, notification_type, title, message, data))


async def _create_notification_async(user_id: int, notification_type: str, title: str, message: str, data: dict = None):
    """Async implementation of notification creation"""
    from app.domains.notifications.schemas import NotificationCreate
    
    notification = NotificationCreate(
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        data=data
    )
    
    notification_id = await NotificationService.create_notification(notification)
    
    # Also send push notification if user has devices
    send_push_notification.apply_async(
        args=[user_id, title, message, data],
        countdown=2
    )
    
    return {"status": "created", "notification_id": notification_id}


@celery_app.task
def send_bulk_notification(user_ids: List[int], title: str, message: str, channels: List[str] = None):
    """Send notification via multiple channels"""
    channels = channels or ['push', 'in_app']
    
    for user_id in user_ids:
        if 'in_app' in channels:
            create_notification.apply_async(args=[user_id, 'system', title, message])
        
        if 'push' in channels:
            send_push_notification.apply_async(args=[user_id, title, message], countdown=5)
        
        if 'email' in channels:
            send_email_notification.apply_async(args=[user_id, 'general', {'message': message}], countdown=10)
    
    return {"status": "queued", "users": len(user_ids), "channels": channels}


@celery_app.task
def cleanup_old_notifications():
    """Cleanup notifications older than 30 days"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_cleanup_old_notifications_async())


async def _cleanup_old_notifications_async():
    """Delete old read notifications"""
    async with get_pg_connection() as conn:
        result = await conn.execute("""
            DELETE FROM notifications
            WHERE is_read = true AND created_at < NOW() - INTERVAL '30 days'
        """)
        
        deleted_count = int(result.split()[-1]) if result else 0
        return {"status": "cleaned", "deleted_count": deleted_count}
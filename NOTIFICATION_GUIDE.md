# Notification System Guide

## Overview

Multi-channel notification system with **graceful error handling** and **admin alerts**. No errors exposed to users - all failures handled silently with admin notification.

## Notification Channels

### 1. **Push Notifications (FCM)**
- **Primary**: Firebase Cloud Messaging for Android/iOS
- **Fallback**: Queue for retry if FCM fails
- **Rate Limit**: 100/minute
- **Graceful Handling**: Invalid tokens auto-deactivated

### 2. **Email (AWS SES)**
- **Primary**: AWS Simple Email Service
- **Fallback**: SMS notification if email fails
- **Rate Limit**: 50/minute
- **Templates**: Daily matches, new messages, profile approved

### 3. **SMS (AWS SNS + Twilio)**
- **Primary**: AWS SNS
- **Fallback**: Twilio if SNS fails
- **Rate Limit**: 100/minute
- **Use Case**: Critical notifications, email fallback

### 4. **In-App Notifications**
- **Storage**: PostgreSQL notifications table
- **Real-time**: WebSocket via Socket.IO
- **Persistence**: 30 days for read, 90 days for unread

## Graceful Error Handling

### No User-Facing Errors
```python
# All notification methods return status, never raise exceptions
result = await notification_handler.send_push(user_id, title, body)

# Possible statuses:
# - "success": Sent successfully
# - "no_devices": User has no registered devices (silent)
# - "queued_retry": Failed, queued for retry (silent)
# - "failed": All attempts failed (admin alerted)
```

### Admin Alert System

**Automatic alerts when:**
- 10+ notification failures in 1 hour
- FCM initialization fails
- Email service unavailable
- SMS provider down

**Alert channels:**
1. Redis list (`admin_alerts`) - Dashboard display
2. Log file - Critical severity
3. Email to admin (if configured)

### Failure Tracking

All failures logged to `notification_failures` table:
```sql
SELECT * FROM notification_failures 
ORDER BY created_at DESC 
LIMIT 50;
```

## Configuration

### Environment Variables
```bash
# Firebase Cloud Messaging
FCM_CREDENTIALS_PATH=/path/to/firebase-credentials.json

# AWS SES
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=<key>
AWS_SECRET_ACCESS_KEY=<secret>
EMAIL_FROM=noreply@aurummatrimony.com

# AWS SNS (SMS)
# Uses same AWS credentials as SES

# Twilio (SMS Fallback)
TWILIO_ACCOUNT_SID=<sid>
TWILIO_AUTH_TOKEN=<token>
TWILIO_PHONE_NUMBER=+1234567890

# Admin Alerts
ADMIN_EMAILS=admin@aurummatrimony.com,tech@aurummatrimony.com
```

### Firebase Setup
```bash
# 1. Create Firebase project
# 2. Download service account JSON
# 3. Set FCM_CREDENTIALS_PATH in .env
# 4. Initialize in app startup:

from app.core.notification_handler import notification_handler
notification_handler.initialize_fcm()
```

## API Endpoints

### Register Device Token
```bash
POST /api/v1/notifications/register-device
{
  "device_token": "fcm_token_here",
  "device_type": "android",  # or "ios", "web"
  "device_name": "Samsung Galaxy S21"
}
```

### Get User Notifications
```bash
GET /api/v1/notifications?limit=20&unread_only=true
```

### Admin: View Alerts
```bash
GET /api/v1/admin/alerts

Response:
{
  "alerts": [
    {
      "subject": "Notification failures threshold reached",
      "details": "Channel: push, Count: 15, Last error: Invalid token",
      "timestamp": "2024-01-15T10:30:00Z",
      "severity": "high"
    }
  ],
  "count": 1
}
```

### Admin: View Failures
```bash
GET /api/v1/admin/notification-failures?limit=50

Response:
{
  "failures": [
    {
      "user_id": 123,
      "channel": "push",
      "error": "Invalid registration token",
      "timestamp": "2024-01-15T10:25:00Z"
    }
  ],
  "count": 1
}
```

### Admin: Retry Failed Notifications
```bash
POST /api/v1/admin/retry-failed-notifications

Response:
{
  "status": "queued",
  "count": 25
}
```

## Notification Types

### Engagement Notifications

| Type | Trigger | Channels | Frequency |
|------|---------|----------|-----------|
| New Users Joined | Daily at midnight | Push, Email | Daily |
| Message Received | Real-time | Push, In-App | Instant |
| Message Reply | Real-time | Push, In-App | Instant |
| Interest Received | Real-time | Push, In-App | Instant |
| Profile Viewed | Real-time | Push (Premium only) | Instant |
| Contact Approved | Admin approval | Push, Email, In-App | Instant |
| Match Suggestion | Daily algorithm | Push, Email | Daily |
| Inactive Reminder | 3 days inactive | Push, Email | Daily |
| Profile Completion | Incomplete profile | Push | Twice daily |

### System Notifications

| Type | Trigger | Channels | Frequency |
|------|---------|----------|-----------|
| Profile Approved | Admin approval | Push, Email, In-App | Instant |
| Profile Rejected | Admin rejection | Email, In-App | Instant |
| Subscription Expiring | 3 days before | Push, Email | Once |
| Payment Success | Payment processed | Email, In-App | Instant |
| Security Alert | Suspicious login | Push, Email, SMS | Instant |

## Celery Tasks

### Real-Time Processing
```python
# Process engagement events every minute
@celery_app.task(name="process_engagement_events")
def process_engagement_events():
    # Processes Redis queue: engagement_queue
    # Sends notifications based on event type
    pass
```

### Scheduled Tasks
```python
# Daily new user notifications
@celery_app.task(name="notify_new_users_joined")
def notify_new_users_joined():
    # Runs daily at midnight
    # Notifies: "5 New Brides Joined!"
    pass

# Re-engagement
@celery_app.task(name="send_inactive_user_reminders")
def send_inactive_user_reminders():
    # Runs daily
    # Targets users inactive 3+ days
    pass

# Profile completion
@celery_app.task(name="send_profile_completion_reminders")
def send_profile_completion_reminders():
    # Runs twice daily
    # Targets incomplete profiles
    pass
```

## Error Handling Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Notification Request                                      │
│    send_push(user_id, title, body)                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Try Primary Channel (FCM)                                │
│    ├─ Success → Return {"status": "success"}                │
│    └─ Failure → Continue to fallback                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Fallback: Queue for Retry                                │
│    Redis: notification_retry_queue                          │
│    Return {"status": "queued_retry"}                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Log Failure                                              │
│    INSERT INTO notification_failures                        │
│    Increment failure counter in Redis                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Check Threshold                                          │
│    If failures >= 10 in 1 hour:                            │
│    ├─ Alert admin via Redis (admin_alerts)                 │
│    ├─ Log critical error                                   │
│    ├─ Send admin email                                     │
│    └─ Reset counter                                        │
└─────────────────────────────────────────────────────────────┘
```

## Monitoring Dashboard

### Key Metrics

```sql
-- Notification success rate (last 24 hours)
SELECT 
    type,
    COUNT(*) FILTER (WHERE status = 'sent') * 100.0 / COUNT(*) as success_rate
FROM notification_logs
WHERE sent_at >= NOW() - INTERVAL '24 hours'
GROUP BY type;

-- Failure rate by channel
SELECT 
    channel,
    COUNT(*) as failure_count,
    DATE_TRUNC('hour', created_at) as hour
FROM notification_failures
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY channel, hour
ORDER BY hour DESC;

-- Active devices by type
SELECT 
    device_type,
    COUNT(*) as active_devices
FROM user_devices
WHERE is_active = true
GROUP BY device_type;

-- Pending retry queue size
-- Redis: LLEN notification_retry_queue
```

### Admin Dashboard Widgets

1. **Alert Panel**: Recent critical alerts
2. **Failure Chart**: Failures by channel (last 24h)
3. **Success Rate**: Overall notification success %
4. **Retry Queue**: Pending notifications count
5. **Device Stats**: Active devices by platform

## Testing

### Test Push Notification
```bash
curl -X POST http://localhost:8000/api/v1/notifications/test-push \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 123,
    "title": "Test Notification",
    "body": "This is a test"
  }'
```

### Simulate Failure
```python
# Temporarily disable FCM to test fallback
notification_handler.fcm_initialized = False

# Send notification - should queue for retry
result = await notification_handler.send_push(123, "Test", "Body")
assert result["status"] == "queued_retry"

# Check admin alerts after 10 failures
for i in range(10):
    await notification_handler.send_push(i, "Test", "Body")

alerts = await redis_client.lrange("admin_alerts", 0, 0)
assert len(alerts) > 0
```

### Load Test
```bash
# Send 1000 notifications
for i in {1..1000}; do
  curl -X POST http://localhost:8000/api/v1/notifications/test-push \
    -H "Authorization: Bearer TOKEN" \
    -d "{\"user_id\": $i, \"title\": \"Test\", \"body\": \"Load test\"}" &
done

# Monitor Celery worker
celery -A app.celery_app inspect active
celery -A app.celery_app inspect stats
```

## Production Checklist

- [ ] Configure FCM credentials
- [ ] Set up AWS SES (verify domain, email addresses)
- [ ] Configure AWS SNS for SMS
- [ ] Set up Twilio as SMS fallback
- [ ] Add admin email addresses to ADMIN_EMAILS
- [ ] Run database migrations (notification tables)
- [ ] Test all notification channels
- [ ] Set up monitoring dashboard
- [ ] Configure alert thresholds
- [ ] Test failure scenarios
- [ ] Load test with 10K notifications
- [ ] Set up log aggregation (CloudWatch/ELK)
- [ ] Configure retry queue monitoring
- [ ] Test admin alert delivery

## Troubleshooting

### No Notifications Received

1. **Check device registration**
```sql
SELECT * FROM user_devices WHERE user_id = 123 AND is_active = true;
```

2. **Check notification logs**
```sql
SELECT * FROM notification_logs WHERE user_id = 123 ORDER BY sent_at DESC LIMIT 10;
```

3. **Check failures**
```sql
SELECT * FROM notification_failures WHERE user_id = 123 ORDER BY created_at DESC LIMIT 10;
```

4. **Check retry queue**
```bash
redis-cli LLEN notification_retry_queue
redis-cli LRANGE notification_retry_queue 0 10
```

### High Failure Rate

1. **Check admin alerts**
```bash
GET /api/v1/admin/alerts
```

2. **Verify credentials**
- FCM: Check firebase-credentials.json
- SES: Verify AWS credentials and domain
- SNS: Check AWS credentials and region

3. **Check service status**
- Firebase Console: Check project status
- AWS Console: Check SES/SNS quotas
- Twilio Dashboard: Check account balance

4. **Retry failed notifications**
```bash
POST /api/v1/admin/retry-failed-notifications
```

## Best Practices

1. **Always use graceful handlers** - Never raise exceptions to users
2. **Monitor admin alerts** - Check dashboard daily
3. **Clean old logs** - Run cleanup task weekly
4. **Test fallbacks** - Regularly test SMS/email fallback
5. **Rate limit** - Respect provider limits (100/min push, 50/min email)
6. **Batch notifications** - Use batch tasks for bulk sends
7. **User preferences** - Respect notification preferences
8. **Retry logic** - Max 3 retries with exponential backoff
9. **Token management** - Auto-deactivate invalid tokens
10. **Admin visibility** - All failures visible to admin, none to users

## Expected Results

✅ **99.9% delivery rate** - With fallback mechanisms  
✅ **Zero user-facing errors** - All failures handled gracefully  
✅ **Admin visibility** - All issues tracked and alerted  
✅ **Multi-channel redundancy** - Push → Email → SMS fallback  
✅ **Automatic recovery** - Retry queue processes failed notifications  
✅ **Real-time alerts** - Admin notified within 1 minute of threshold

# WhatsApp Security Guide - Premium Feature

## Overview

**CRITICAL**: WhatsApp messaging is the most sensitive feature - requires extreme security measures for affluent users.

## Security Architecture

### Multi-Layer Protection

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Tier Verification                                  │
│ ✓ Premium/Elite only                                        │
│ ✓ Subscription validation                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Pattern-Based Filtering (Instant Block)           │
│ ✓ Harmful content (violence, scam, explicit)               │
│ ✓ PII leakage (credit cards, SSN, passwords)               │
│ ✓ External messaging apps                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: AI Moderation (OpenAI GPT-4)                      │
│ ✓ OpenAI Moderation API                                    │
│ ✓ GPT-4 context analysis                                   │
│ ✓ Intent detection                                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: Admin Review (Suspicious Content)                 │
│ ✓ Manual review queue                                      │
│ ✓ Approve/Reject workflow                                  │
│ ✓ User notification                                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 5: WhatsApp Business API                             │
│ ✓ Official Meta API                                        │
│ ✓ End-to-end encryption                                    │
│ ✓ Delivery tracking                                        │
└─────────────────────────────────────────────────────────────┘
```

## Blocked Content Patterns

### Instant Block (No Admin Review)

1. **Violence/Harm**
   - kill, murder, harm, hurt, attack, violence
   - bomb, weapon, gun, knife
   - hate, racist, terrorist

2. **Scam/Fraud**
   - scam, fraud, cheat, steal
   - money transfer, bank account
   - urgent payment requests

3. **Explicit Content**
   - sex, porn, nude, explicit
   - drug, cocaine, heroin

4. **PII Leakage**
   - Credit card numbers (16 digits)
   - SSN patterns
   - Password sharing

5. **External Messaging**
   - WhatsApp, Telegram, Signal, Wickr
   - "Contact me on..."

### Suspicious Patterns (Admin Review Required)

- 2+ suspicious keywords: meet, hotel, room, private, money, urgent
- Phone numbers in message
- Email addresses in message
- Multiple contact attempts

## AI Moderation (OpenAI)

### Two-Stage AI Check

**Stage 1: OpenAI Moderation API**
```python
response = openai.Moderation.create(input=message)
# Flags: hate, harassment, self-harm, sexual, violence
```

**Stage 2: GPT-4 Context Analysis**
```python
prompt = """
You are a content moderator for a premium matrimony platform.
Analyze if this message is appropriate for WhatsApp communication.
Consider: safety, appropriateness, scam indicators, harmful intent.
Respond with SAFE or UNSAFE followed by reason.
"""
```

## Configuration

### Environment Variables
```bash
# WhatsApp Business API
WHATSAPP_PHONE_NUMBER_ID=<your_phone_number_id>
WHATSAPP_ACCESS_TOKEN=<your_access_token>

# OpenAI for AI moderation
OPENAI_API_KEY=<your_openai_key>

# Cost tracking
WHATSAPP_COST_PER_MESSAGE=0.005  # $0.005 per message
WHATSAPP_MONTHLY_ALERT_THRESHOLD=100  # Alert at $100/month
```

### WhatsApp Business API Setup

1. **Create Meta Business Account**
   - Go to https://business.facebook.com
   - Create business account
   - Verify business

2. **Set Up WhatsApp Business API**
   - Go to https://developers.facebook.com
   - Create app → Business → WhatsApp
   - Add WhatsApp product
   - Get Phone Number ID and Access Token

3. **Configure Webhook** (for delivery status)
   ```bash
   POST https://graph.facebook.com/v18.0/{phone_number_id}/messages
   Authorization: Bearer {access_token}
   ```

## API Endpoints

### Send WhatsApp Message (Premium Only)
```bash
POST /api/v1/whatsapp/send
Authorization: Bearer <premium_user_token>

{
  "recipient_id": 123,
  "message": "Hi, I'm interested in your profile"
}

# Responses:
# 1. Success
{
  "status": "sent",
  "message_id": "wamid.xxx",
  "cost": 0.005
}

# 2. Pending Review
{
  "status": "pending_review",
  "message": "Your message is under review by our team"
}

# 3. Blocked
{
  "status": "blocked",
  "error": "Message blocked for policy violation"
}

# 4. Forbidden (Free user)
{
  "status": "forbidden",
  "error": "WhatsApp messaging is only available for Premium and Elite members"
}
```

### Admin: Get Pending Reviews
```bash
GET /api/v1/whatsapp/admin/pending-reviews
Authorization: Bearer <admin_token>

Response:
{
  "pending_reviews": [
    {
      "sender_id": 45,
      "recipient_id": 67,
      "message": "Can we meet at hotel?",
      "reason": "Multiple suspicious patterns: meet, hotel",
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ],
  "count": 1
}
```

### Admin: Approve/Reject Message
```bash
POST /api/v1/whatsapp/admin/review
Authorization: Bearer <admin_token>

{
  "review_id": "0",
  "decision": "approve",  # or "reject"
  "admin_notes": "Legitimate meeting request"
}

Response:
{
  "status": "approved_and_sent",
  "message_id": "wamid.xxx"
}
```

### Admin: View Violations
```bash
GET /api/v1/whatsapp/admin/violations?limit=50
Authorization: Bearer <admin_token>

Response:
{
  "violations": [
    {
      "sender_id": 89,
      "recipient_id": 90,
      "message": "Send money to...",
      "reason": "Pattern: scam, fraud",
      "severity": "harmful",
      "timestamp": "2024-01-15T09:00:00Z"
    }
  ],
  "count": 1
}
```

### Admin: View Costs
```bash
GET /api/v1/whatsapp/admin/costs
Authorization: Bearer <admin_token>

Response:
{
  "total_cost": 125.50,
  "top_users": [
    {"user_id": 45, "cost": 25.00},
    {"user_id": 67, "cost": 18.50}
  ],
  "month": "2024-01"
}
```

### Admin: Block/Unblock User
```bash
# Block user (30 days)
POST /api/v1/whatsapp/admin/block-user/123
Authorization: Bearer <admin_token>

# Unblock user
DELETE /api/v1/whatsapp/admin/unblock-user/123
Authorization: Bearer <admin_token>
```

## Auto-Block System

### Violation Thresholds

| Violations | Action | Duration |
|-----------|--------|----------|
| 1 | Warning logged | - |
| 2 | Admin alert | - |
| 3 | Auto-block | 7 days |
| 5+ | Permanent block | Manual review required |

### Auto-Block Trigger
```sql
-- Database trigger automatically blocks after 3 violations
CREATE TRIGGER trigger_check_violations
AFTER INSERT ON content_violations
FOR EACH ROW
EXECUTE FUNCTION check_violation_threshold();
```

## Admin Dashboard Metrics

### Key Metrics to Monitor

```sql
-- Messages sent today
SELECT COUNT(*) FROM whatsapp_message_log 
WHERE created_at >= CURRENT_DATE AND status = 'sent';

-- Pending reviews
SELECT COUNT(*) FROM whatsapp_admin_reviews 
WHERE decision IS NULL;

-- Violations by severity
SELECT severity, COUNT(*) 
FROM content_violations 
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY severity;

-- Top violators
SELECT sender_id, COUNT(*) as violation_count
FROM content_violations
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY sender_id
ORDER BY violation_count DESC
LIMIT 10;

-- Monthly costs
SELECT SUM(0.005) as total_cost
FROM whatsapp_message_log
WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE)
AND status = 'sent';
```

## Security Best Practices

### 1. **Never Bypass Moderation**
- All messages MUST go through content_moderator
- No direct WhatsApp API calls without moderation
- Admin approval required for flagged content

### 2. **Monitor Violations Daily**
- Check admin dashboard every morning
- Review pending messages within 2 hours
- Investigate repeat offenders

### 3. **Cost Control**
- Set monthly budget alerts
- Monitor high-usage users
- Review cost reports weekly

### 4. **User Education**
- Clear guidelines in app
- Warning on first violation
- Explanation for blocks

### 5. **Audit Trail**
- All messages logged permanently
- Admin decisions recorded
- Violation history tracked

## Testing

### Test Content Moderation
```python
# Test harmful content (should block)
message = "Send money to my bank account urgently"
result = await content_moderator.moderate_message(1, 2, message)
assert result["approved"] == False

# Test suspicious content (should require review)
message = "Can we meet at hotel tomorrow?"
result = await content_moderator.moderate_message(1, 2, message)
assert result["requires_admin"] == True

# Test safe content (should approve)
message = "I'm interested in your profile. Would you like to connect?"
result = await content_moderator.moderate_message(1, 2, message)
assert result["approved"] == True
```

### Test Tier Verification
```python
# Free user should be blocked
free_user = {"id": 1, "tier": "free"}
result = await whatsapp_sender.send_message(1, 2, "Hello", db)
assert result["status"] == "forbidden"

# Premium user should proceed
premium_user = {"id": 2, "tier": "premium"}
result = await whatsapp_sender.send_message(2, 3, "Hello", db)
assert result["status"] in ["sent", "pending_review"]
```

## Incident Response

### If Harmful Content Sent

1. **Immediate Actions**
   - Auto-block sender (already done by system)
   - Alert admin (already done)
   - Review sender's history

2. **Investigation**
   - Check all messages from sender
   - Review recipient's safety
   - Contact recipient if needed

3. **Follow-Up**
   - Permanent ban if intentional
   - Report to authorities if illegal
   - Update moderation patterns

### If System Compromised

1. **Disable WhatsApp Feature**
   ```python
   whatsapp_sender.enabled = False
   ```

2. **Review All Recent Messages**
   ```sql
   SELECT * FROM whatsapp_message_log 
   WHERE created_at >= NOW() - INTERVAL '24 hours'
   ORDER BY created_at DESC;
   ```

3. **Audit Admin Actions**
   ```sql
   SELECT * FROM whatsapp_admin_reviews 
   WHERE created_at >= NOW() - INTERVAL '7 days';
   ```

4. **Rotate API Keys**
   - Generate new WhatsApp access token
   - Update WHATSAPP_ACCESS_TOKEN in env
   - Restart services

## Compliance

### Data Protection
- All messages encrypted in transit (WhatsApp E2E)
- Messages logged for safety (GDPR compliant with consent)
- User can request message deletion (GDPR right to erasure)

### Legal Requirements
- Terms of Service: Clear WhatsApp usage policy
- Privacy Policy: Message logging disclosure
- User Consent: Explicit opt-in for WhatsApp feature

## Production Checklist

- [ ] Set up WhatsApp Business API account
- [ ] Configure OpenAI API key
- [ ] Run database migrations (whatsapp tables)
- [ ] Test all moderation patterns
- [ ] Test AI moderation with OpenAI
- [ ] Set up admin review workflow
- [ ] Configure cost tracking and alerts
- [ ] Test auto-block system
- [ ] Create admin dashboard
- [ ] Train admin team on review process
- [ ] Set up 24/7 monitoring
- [ ] Create incident response plan
- [ ] Legal review of terms and privacy policy
- [ ] User education materials
- [ ] Load test with 1000 messages

## Expected Results

✅ **99.9% harmful content blocked** - Multi-layer protection  
✅ **Zero security breaches** - Extreme security measures  
✅ **<2 hour admin review time** - Fast response to flagged content  
✅ **Auto-block repeat offenders** - 3 strikes system  
✅ **Full audit trail** - Every message logged  
✅ **Cost control** - $0.005/message with alerts  
✅ **Premium feature** - Revenue generator for platform

# Remember Me & Credential Export Implementation Guide

## Quick Start

### For Flutter Users
1. **First Time Login**:
   - Enter phone + password
   - Check "Remember Me" checkbox (optional)
   - Tap "Log In"
   - Credentials saved securely on device

2. **Next Time Opening App**:
   - App shows "Welcome Back" dialog with saved phone
   - Tap "Log In" to auto-login
   - Or tap "Use Different Account" to login with different credentials

3. **To Stop Remembering**:
   - On login page, uncheck "Remember Me" before logging in
   - Or manually logout (clears all credentials)

### For Admins - Sharing Credentials with Users
1. **After Approving User**:
   ```
   Dashboard → Users → Find User → Approve
   ```

2. **Export Credentials**:
   ```
   POST /api/v1/admin/credentials/export
   {
     "user_id": 123,
     "original_password": "UserPassword@123",
     "delivery_method": "whatsapp"
   }
   ```

3. **Share via WhatsApp**:
   - Download the JSON file
   - Open WhatsApp
   - Send to user with message:
     ```
     "Hi! Here are your Aurum credentials.
     
     Phone: +919876543210
     Password: YourPassword@123
     
     Please save these securely."
     ```

4. **Mark as Delivered**:
   ```
   POST /api/v1/admin/credentials/mark-delivered
   {
     "export_id": 456,
     "delivery_note": "Sent via WhatsApp at 2:30 PM"
   }
   ```

---

## File Locations & Changes

### New Files Created

#### Flutter
- ✅ `lib/match_making/core/credential_storage_service.dart` - Secure credential storage

#### Backend
- ✅ `app/domains/identity/credential_models.py` - Database models
- ✅ `app/domains/identity/credential_service.py` - Business logic
- ✅ `app/domains/identity/credential_api.py` - API endpoints
- ✅ `migrations/V7__Create_credential_audit_tables.sql` - Database tables

### Modified Files

#### Flutter
- ✅ `lib/match_making/auth/login_page.dart` - Added Remember Me checkbox & auto-login

#### Backend
- `app/main.py` - Need to register credential_api routes (see below)

---

## Integration Steps

### Step 1: Register Backend API Routes

Edit `app/main.py` and add the credential router:

```python
from app.domains.identity.credential_api import router as credential_router

app.include_router(credential_router)
```

### Step 2: Run Database Migration

```bash
cd backend
flyway -baselineOnMigrate baseline
flyway migrate
```

Or manually run the migration:
```sql
-- Run V7__Create_credential_audit_tables.sql
```

### Step 3: Verify Flutter Packages

Ensure `pubspec.yaml` has these dependencies:

```yaml
dependencies:
  flutter_secure_storage: ^9.0.0
  shared_preferences: ^2.2.0
  crypto: ^3.0.0
```

Install packages:
```bash
cd frontend/clickgo
flutter pub get
```

### Step 4: Test the Feature

#### Test Flutter Remember Me
```dart
// In simulator/device
1. Open app
2. Go to login page
3. Enter phone: +919876543210
4. Enter password: test123
5. Check "Remember Me"
6. Tap "Log In"
7. Verify login succeeds
8. Stop and restart app
9. Should see "Welcome Back" dialog
10. Tap "Log In" - should auto-login
```

#### Test Admin Credential Export
```bash
# Export credentials
curl -X POST http://localhost:8000/api/v1/admin/credentials/export \
  -H "Authorization: Bearer admin_token" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 123,
    "original_password": "UserPassword@123",
    "delivery_method": "whatsapp"
  }'

# Should return download_token and credentials JSON

# Mark as delivered
curl -X POST http://localhost:8000/api/v1/admin/credentials/mark-delivered \
  -H "Authorization: Bearer admin_token" \
  -H "Content-Type: application/json" \
  -d '{
    "export_id": 456,
    "delivery_note": "Sent via WhatsApp"
  }'
```

---

## Database Schema

### credential_audit Table
Stores information about each credential export.

```
id (PK)
user_id (FK → users)
admin_id (FK → users)
export_timestamp
delivery_method [whatsapp|email|manual]
marked_delivered [true|false]
delivery_timestamp
delivery_note
admin_ip_address
admin_user_agent
created_at
updated_at
```

### credential_exports Table
Stores encrypted credentials temporarily.

```
id (PK)
audit_id (FK → credential_audit)
encrypted_phone
encrypted_password
export_format [json|csv|txt]
download_token (unique)
downloaded
download_count
created_at
expires_at [24 hours from creation]
```

---

## Security Details

### What Gets Encrypted?

✅ **Encrypted at rest** (Flutter Secure Storage):
- Phone number
- Password

✅ **Encrypted in transit**:
- All API calls over HTTPS/TLS
- Credentials never sent in plaintext

✅ **User-controlled**:
- Only saves if user explicitly checks "Remember Me"
- Can be cleared anytime by unchecking checkbox
- Auto-clears after 90 days of inactivity

### What Doesn't Get Encrypted?

❌ **Never encrypted** (secure by design):
- Tokens (JWT) - stateless, can be invalidated
- User ID - public information
- Phone number in audit log - tracked for admin

### Admin Security

✅ **Admin credential export**:
- Only admins can export
- Logged with admin IP + user agent
- File expires after 24 hours
- Max 3 downloads per export
- Hash of credentials stored for verification

---

## API Reference

### POST `/api/v1/admin/credentials/export`

**Purpose**: Export user credentials for admin to share via WhatsApp

**Required Roles**: admin, moderator

**Request**:
```json
{
  "user_id": 123,
  "original_password": "UserPassword@123",
  "delivery_method": "whatsapp",
  "delivery_note": "optional note"
}
```

**Response (200)**:
```json
{
  "success": true,
  "download_token": "secure_token_xyz",
  "credentials": {
    "app_name": "Aurum - Matrimony Platform",
    "user_info": {
      "id": 123,
      "name": "+919876543210",
      "phone": "+919876543210"
    },
    "login_credentials": {
      "phone": "+919876543210",
      "password": "UserPassword@123"
    },
    "instructions": {
      "how_to_use": "Share these credentials with the user via WhatsApp...",
      "security_notice": "Treat this as sensitive information...",
      "storage": "User should save credentials in their device..."
    },
    "export_details": {
      "exported_at": "2025-01-27T14:30:00Z",
      "exported_by": "Admin #1",
      "delivery_method": "whatsapp",
      "token": "secure_token_xyz"
    }
  },
  "export_file_name": "aurum_credentials_123_20250127_143022.json",
  "expires_in_hours": 24
}
```

**Error Responses**:
- `403 Forbidden` - User not admin
- `404 Not Found` - User not found
- `500 Internal Server Error` - Export failed

---

### POST `/api/v1/admin/credentials/mark-delivered`

**Purpose**: Mark credentials as successfully delivered to user

**Required Roles**: admin, moderator

**Request**:
```json
{
  "export_id": 456,
  "delivery_note": "Sent via WhatsApp at 2:30 PM"
}
```

**Response (200)**:
```json
{
  "success": true,
  "message": "Credentials for user 123 marked as delivered",
  "delivered_at": "2025-01-27T14:35:00Z"
}
```

**Error Responses**:
- `403 Forbidden` - User not admin
- `404 Not Found` - Export ID not found
- `500 Internal Server Error` - Failed to mark delivery

---

### GET `/api/v1/admin/credentials/export/{user_id}/history`

**Purpose**: View credential export history for a user

**Required Roles**: admin, moderator

**Response (200)**:
```json
{
  "success": true,
  "user_id": 123,
  "export_history": [
    {
      "id": 456,
      "exported_at": "2025-01-27T14:30:00Z",
      "admin_id": 1,
      "delivery_method": "whatsapp",
      "marked_delivered": true,
      "delivery_timestamp": "2025-01-27T14:35:00Z",
      "delivery_note": "Sent via WhatsApp"
    }
  ]
}
```

---

### GET `/api/v1/admin/credentials/download/{download_token}`

**Purpose**: Download exported credentials (user or admin accessible)

**No Authentication Required** (token is security mechanism)

**Response (200)**:
```json
{
  "app_name": "Aurum - Matrimony Platform",
  "user_id": 123,
  "phone": "+919876543210",
  "password": "UserPassword@123",
  "exported_at": "2025-01-27T14:30:00Z",
  "delivery_method": "whatsapp",
  "security_notice": "These credentials should be kept confidential..."
}
```

**Error Responses**:
- `404 Not Found` - Invalid token
- `410 Gone` - Token expired (24 hours) or download limit exceeded (3 downloads)
- `500 Internal Server Error` - Download failed

---

## Dart/Flutter Code Examples

### Save Credentials
```dart
import 'credential_storage_service.dart';

final storage = CredentialStorageService();

// Save with Remember Me
await storage.saveCredentials(
  phone: "+919876543210",
  password: "UserPassword@123",
  rememberMe: true,  // Only saves if true
  deviceId: "device_uuid_optional",
);
```

### Retrieve Stored Credentials
```dart
final creds = await storage.getStoredCredentials();
if (creds != null) {
  print("Saved phone: ${creds.phone}");
  print("Age: ${DateTime.now().difference(creds.savedAt).inDays} days");
}
```

### Check Auto-Login Status
```dart
final isRememberMeEnabled = await storage.isRememberMeEnabled();
if (isRememberMeEnabled) {
  final creds = await storage.getStoredCredentials();
  if (creds != null) {
    // Show auto-login prompt
    _showAutoLoginPrompt();
  }
}
```

### Clear Credentials
```dart
// Clear Remember Me credentials
await storage.clearCredentials();

// Clear everything (including history)
await storage.clearAllData();
```

### Get Login History
```dart
final history = await storage.getLoginHistory();
// Returns: ["+919876543210", "+919876543211", ...]
// Useful for "Recent logins" UI
```

### Check if Credentials Need Refresh
```dart
final isStale = await storage.areCredentialsStale();
if (isStale) {
  // Show warning: "Please update your password"
  // Force user to re-enter password
}
```

---

## Troubleshooting

### Problem: Auto-login keeps failing
**Solution**: 
1. Check that password hasn't changed
2. Clear credentials: `await storage.clearCredentials()`
3. Login manually again

### Problem: Remember Me checkbox doesn't work
**Solution**:
1. Ensure Flutter Secure Storage is installed: `flutter pub get`
2. Check Android/iOS permissions
3. Restart the app

### Problem: Credentials not encrypting
**Solution**:
1. Flutter Secure Storage requires secure hardware (not emulator)
2. Test on real device
3. Check that platform is initialized: `SecureApiClient().init()`

### Problem: Admin export returns 500 error
**Solution**:
1. Verify user_id exists
2. Verify original_password is correct
3. Check backend logs: `docker logs api`
4. Ensure credential tables are created: run migration

### Problem: Download token expired
**Solution**:
1. Export credentials again - generates new token
2. Download token valid for 24 hours
3. Each token allows max 3 downloads

---

## Admin Documentation

### When to Export Credentials?

1. **User completes profile submission** → Admin reviews & approves
2. **Admin clicks "Approve"** → Status changes to "approved"
3. **Admin exports credentials** → Sends via WhatsApp to user
4. **User saves credentials** → Can use for future logins
5. **Admin marks as delivered** → Audit trail complete

### Best Practices

✅ **DO**:
- Export immediately after approval
- Send via WhatsApp Direct Message (encrypted)
- Save credentials to device immediately
- Delete message after saving (optional)
- Mark as delivered in admin panel

❌ **DON'T**:
- Share credentials via email (unencrypted)
- Share credentials in group chats
- Keep credentials in chat history
- Reuse credentials across platforms
- Share with other users

### Sample WhatsApp Message Template

```
Hi [User Name]! 👋

Your Aurum matrimony profile has been approved! 🎉

Here are your login credentials:

📱 Phone: +91-9876-543-210
🔐 Password: Your@Password123

Please save these credentials securely on your device.

You can login using the app and complete your profile setup.

Welcome to Aurum! ✨

Questions? Reply to this message.
```

---

## Monitoring & Analytics

### Metrics to Track

1. **Adoption Rate**
   - % of users checking Remember Me
   - Average days before auto-login used

2. **Security Metrics**
   - Failed auto-login attempts
   - Credential age (days since saved)
   - Download attempts vs delivered

3. **Performance**
   - Auto-login success rate
   - Credential encryption/decryption time

### Sample Queries

```sql
-- Users with active Remember Me
SELECT COUNT(*) 
FROM credential_audit 
WHERE marked_delivered = true 
AND DATE(created_at) = CURRENT_DATE;

-- Average days before auto-login
SELECT AVG(AGE(DATE(export_timestamp), DATE(created_at))) as avg_days
FROM credential_audit
WHERE marked_delivered = true;

-- Admin export frequency
SELECT admin_id, COUNT(*) as exports_per_admin
FROM credential_audit
GROUP BY admin_id
ORDER BY exports_per_admin DESC;

-- Expired credentials
SELECT COUNT(*)
FROM credential_exports
WHERE expires_at < CURRENT_TIMESTAMP;
```

---

## Next Steps

### Phase 2: Enhancements
1. **Automated WhatsApp**: Integration with WhatsApp Business API
2. **SMS Delivery**: Send credentials via SMS
3. **Email Delivery**: Send via secure email with expiring links
4. **Biometric Login**: Fingerprint/Face ID for Remember Me

### Phase 3: Advanced Security
1. **Device Binding**: Link credentials to specific device
2. **Password Rotation**: Force change every 90 days
3. **Multi-Factor Auth**: SMS/TOTP verification
4. **Session Management**: Logout from all devices

### Phase 4: User Experience
1. **QR Code Login**: Scan QR for instant login
2. **Link-based Auth**: Magic links in WhatsApp
3. **Social Login**: Google/Apple Sign-in
4. **Passwordless Auth**: PIN-based login

---

## Support

### For Users
- "Remember Me" not working? Logout and login again
- Can't find saved credentials? Check login history
- Need to change password? Contact admin

### For Admins
- Credentials export not working? Verify user exists and password is correct
- Download token expired? Export again
- Need to revoke credentials? Clear from audit table

### For Developers
- See `REMEMBER_ME_FEATURE.md` for detailed technical documentation
- Check `/app/domains/identity/credential_*` files for implementation
- Review Flutter `credential_storage_service.dart` for client code

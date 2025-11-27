# Remember Me & Credential Storage Feature

## Overview

Users can now opt-in to save their login credentials locally on their device using the **Remember Me** checkbox. This enables:

1. **Auto-login** - When user opens app, they're automatically logged in if credentials are valid
2. **Convenient re-login** - Saved phone numbers appear in login history
3. **User-controlled** - Credentials are only saved if user explicitly checks "Remember Me"
4. **Secure storage** - Credentials encrypted using device-level encryption
5. **Admin credential export** - Admins can export credentials as JSON files to share via WhatsApp

---

## User Flow

### 1. Login with Remember Me

```
User fills in Phone + Password
  ↓
Checks "Remember Me" checkbox (OPTIONAL)
  ↓
Taps "Log In" button
  ↓
Backend validates credentials
  ↓
If successful:
  - Credentials saved locally (encrypted, device-level security)
  - Tokens saved to secure storage
  - User navigated to dashboard
```

### 2. Auto-Login on App Restart

```
User opens app after previous login
  ↓
App checks for stored credentials
  ↓
If credentials exist + Remember Me enabled:
  - Show "Welcome Back" dialog with saved phone number
  - User chooses: "Log In" or "Use Different Account"
  ↓
If "Log In":
  - Auto-login with saved credentials
  - Validate tokens
  - Navigate to dashboard
↓
If "Use Different Account":
  - Clear auto-login prompt
  - User can enter different credentials manually
```

### 3. Manual Logout

```
User taps "Log Out" in settings
  ↓
Clear tokens from secure storage
  ↓
Clear credentials (if Remember Me was enabled)
  ↓
Navigate to login page
```

### 4. Credentials Expire (Security)

Stored credentials automatically expire after **90 days** to force periodic password refresh. When expired:
- Credentials cleared from device
- User prompted to login again manually
- This ensures stale credentials don't persist too long

---

## Admin Workflow - Credential Export

### Prerequisites
- User has completed profile submission
- Admin has approved user's profile
- Admin now needs to send credentials to user via WhatsApp

### Steps

#### 1. Admin Exports Credentials
```bash
POST /api/v1/admin/credentials/export
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "user_id": 123,
  "original_password": "UserPassword@123",
  "delivery_method": "whatsapp"
}

Response:
{
  "success": true,
  "download_token": "eyJ...",
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
    "instructions": {...},
    "export_details": {...}
  },
  "export_file_name": "aurum_credentials_123_20250127_143022.json",
  "expires_in_hours": 24
}
```

#### 2. Admin Downloads JSON File
Backend generates encrypted JSON file with credentials and metadata.
Admin downloads from file system or download endpoint.

#### 3. Admin Shares via WhatsApp
Admin manually opens WhatsApp and sends the JSON file to user.
Can include message:
```
"Hi! Here are your Aurum login credentials. 
Please save them securely on your device.

Phone: +919876543210
Password: YourPassword@123

Download the full details from: [download_link]"
```

#### 4. Admin Marks as Delivered
```bash
POST /api/v1/admin/credentials/mark-delivered
Authorization: Bearer <admin_token>

{
  "export_id": 456,
  "delivery_note": "Shared via WhatsApp at 14:30"
}

Response:
{
  "success": true,
  "message": "Credentials for user 123 marked as delivered",
  "delivered_at": "2025-01-27T14:30:00Z"
}
```

---

## Flutter Implementation

### 1. Credential Storage Service
**File**: `lib/match_making/core/credential_storage_service.dart`

Handles all credential operations:
```dart
final storage = CredentialStorageService();

// Save credentials with Remember Me
await storage.saveCredentials(
  phone: "+919876543210",
  password: "password123",
  rememberMe: true,  // Only saves if true
);

// Retrieve stored credentials
final creds = await storage.getStoredCredentials();
print("Saved phone: ${creds?.phone}");

// Check if Remember Me is enabled
final isEnabled = await storage.isRememberMeEnabled();

// Clear credentials
await storage.clearCredentials();

// Get login history
final history = await storage.getLoginHistory();
print("Recent logins: $history"); // ["+919876543210", "+919876543211"]
```

### 2. Login Page Integration
**File**: `lib/match_making/auth/login_page.dart`

#### Remember Me Checkbox
```dart
Checkbox(
  value: _rememberMe,
  onChanged: (value) {
    setState(() => _rememberMe = value ?? false);
  },
  activeColor: primaryGold,
)
Text("Remember Me")
```

#### Save Credentials on Login
```dart
if (loginResult['success'] == true) {
  if (_rememberMe) {
    await _credentialStorage.saveCredentials(
      phone: identifier,
      password: password,
      rememberMe: true,
    );
  } else {
    await _credentialStorage.clearCredentials();
  }
  // Navigate to dashboard
  Navigator.pushReplacementNamed(context, '/dashboard');
}
```

#### Auto-Login Prompt
```dart
// Check for stored credentials on app startup
Future<void> _checkForStoredCredentials() async {
  final credentials = await _credentialStorage.getStoredCredentials();
  if (credentials != null) {
    setState(() {
      _storedCredentials = credentials;
      _showAutoLoginPrompt = true;
    });
  }
}

// Show dialog with saved phone
// User chooses: Auto-login or Use Different Account
```

---

## Backend Database Schema

### Tables

#### 1. `credential_audit`
Tracks all credential exports for security auditing.

```sql
CREATE TABLE credential_audit (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  admin_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  export_timestamp TIMESTAMP DEFAULT NOW(),
  delivery_method VARCHAR(50) DEFAULT 'whatsapp',
  export_file_hash VARCHAR(256),
  marked_delivered BOOLEAN DEFAULT FALSE,
  delivery_timestamp TIMESTAMP,
  delivery_note VARCHAR(500),
  admin_ip_address VARCHAR(45),
  admin_user_agent VARCHAR(500),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

#### 2. `credential_exports`
Stores encrypted credentials temporarily for download.

```sql
CREATE TABLE credential_exports (
  id SERIAL PRIMARY KEY,
  audit_id INTEGER NOT NULL REFERENCES credential_audit(id) ON DELETE CASCADE,
  encrypted_phone VARCHAR(255) NOT NULL,
  encrypted_password VARCHAR(255) NOT NULL,
  export_format VARCHAR(20) DEFAULT 'json',
  download_token VARCHAR(256) UNIQUE,
  downloaded BOOLEAN DEFAULT FALSE,
  download_count INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP NOT NULL,  -- 24 hours from creation
  CONSTRAINT credentials_expire_check CHECK (expires_at > created_at)
);
```

---

## Security Considerations

### Frontend (Flutter)
✅ **Device-level encryption** - Uses native Android/iOS encryption
✅ **Secure storage** - Flutter Secure Storage with hardware-backed encryption
✅ **User consent** - Only saves if user explicitly checks "Remember Me"
✅ **Expiration** - Credentials auto-delete after 90 days
✅ **Manual logout** - User can clear credentials anytime

### Backend (FastAPI)
✅ **Encryption in transit** - HTTPS/TLS for all requests
✅ **Rate limiting** - Prevents brute force attacks
✅ **Admin authentication** - Only admins can export
✅ **Audit logging** - All exports logged with admin IP/user agent
✅ **Token expiration** - Download links expire after 24 hours
✅ **Download limits** - Max 3 downloads per export
✅ **SQL injection prevention** - Parameterized queries
✅ **CSRF protection** - Auth endpoints bypass CSRF for mobile clients

### Never Stored Unencrypted
- ❌ Credentials in SharedPreferences (unencrypted)
- ❌ Credentials in plain text files
- ❌ Credentials in logs
- ❌ Credentials in analytics events
- ✅ Credentials in Flutter Secure Storage only

---

## API Endpoints

### Admin Credential Export

#### POST `/api/v1/admin/credentials/export`
Export user credentials for WhatsApp delivery.

**Request**:
```json
{
  "user_id": 123,
  "original_password": "UserPassword@123",
  "delivery_method": "whatsapp"
}
```

**Response**:
```json
{
  "success": true,
  "download_token": "secure_token_here",
  "credentials": {...},
  "export_file_name": "aurum_credentials_123_20250127.json",
  "expires_in_hours": 24
}
```

#### POST `/api/v1/admin/credentials/mark-delivered`
Mark credentials as delivered to user.

**Request**:
```json
{
  "export_id": 456,
  "delivery_note": "Sent via WhatsApp"
}
```

#### GET `/api/v1/admin/credentials/export/{user_id}/history`
Get export history for a user.

**Response**:
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
      "delivery_timestamp": "2025-01-27T15:00:00Z",
      "delivery_note": "Sent via WhatsApp"
    }
  ]
}
```

#### GET `/api/v1/admin/credentials/download/{download_token}`
Download exported credentials (user-accessible via shared link).

**Response**:
```json
{
  "app_name": "Aurum - Matrimony Platform",
  "user_id": 123,
  "phone": "+919876543210",
  "password": "UserPassword@123",
  "exported_at": "2025-01-27T14:30:00Z",
  "delivery_method": "whatsapp"
}
```

---

## Configuration

### Environment Variables
```bash
# Optional: Custom encryption key
CREDENTIAL_CIPHER_KEY=your_fernet_key_here

# Duration credentials remain valid
CREDENTIAL_EXPIRY_DAYS=90

# Download token expiration
CREDENTIAL_TOKEN_EXPIRY_HOURS=24

# Max downloads per export
CREDENTIAL_MAX_DOWNLOADS=3
```

### Flutter Dependencies
```yaml
dependencies:
  flutter:
    sdk: flutter
  flutter_secure_storage: ^9.0.0
  shared_preferences: ^2.2.0
  crypto: ^3.0.0
  http: ^1.1.0
```

### Backend Dependencies
```python
# Add to requirements.txt
cryptography>=41.0.0
```

---

## Testing

### Flutter Testing
```dart
// Test Remember Me save
await credentialStorage.saveCredentials(
  phone: "+919876543210",
  password: "test123",
  rememberMe: true,
);

// Verify saved
final saved = await credentialStorage.getStoredCredentials();
expect(saved?.phone, "+919876543210");

// Test auto-login
_checkForStoredCredentials();
expect(_showAutoLoginPrompt, isTrue);

// Test clear
await credentialStorage.clearCredentials();
final cleared = await credentialStorage.getStoredCredentials();
expect(cleared, isNull);
```

### Backend Testing
```python
# Test credential export
response = await client.post(
    "/api/v1/admin/credentials/export",
    json={
        "user_id": 123,
        "original_password": "test123",
        "delivery_method": "whatsapp"
    },
    headers={"Authorization": "Bearer admin_token"}
)
assert response.status_code == 200
assert "download_token" in response.json()

# Test credential download with token
response = await client.get(
    f"/api/v1/admin/credentials/download/{download_token}"
)
assert response.status_code == 200
assert response.json()["phone"] == "+919876543210"
```

---

## Troubleshooting

### Auto-Login Failing
- **Issue**: Auto-login prompt shows but login fails
- **Cause**: Stored credentials are outdated or password was changed
- **Fix**: Clear credentials and login manually
- **Code**:
  ```dart
  await _credentialStorage.clearCredentials();
  _dismissAutoLoginPrompt();
  ```

### Remember Me Not Working
- **Issue**: Checkbox checked but credentials not saving
- **Cause**: Secure storage initialization failed
- **Fix**: Check Flutter Secure Storage permissions
- **Android**: Add to `AndroidManifest.xml`:
  ```xml
  <uses-permission android:name="android.permission.INTERNET" />
  <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
  ```

### Credentials Stale
- **Issue**: "Your saved credentials are no longer valid"
- **Cause**: Password changed since credentials were saved
- **Fix**: User must login with new password
- **Result**: Stored credentials automatically cleared

### Admin Export Fails
- **Issue**: `POST /admin/credentials/export` returns 500
- **Cause**: Original password incorrect or user not found
- **Fix**: Verify user_id and original_password are correct

---

## Future Enhancements

1. **Automatic SMS/WhatsApp** - Send credentials directly via API instead of manual
2. **QR Code Login** - Scan QR code to login (like Instagram)
3. **Biometric Authentication** - Fingerprint/Face ID for auto-login
4. **Device Binding** - Link credentials to specific device
5. **Password Reset** - User can change password without admin
6. **Credential Rotation** - Force password change every 90 days
7. **Multi-device Sync** - Sync login across multiple devices
8. **Session Management** - Logout from all devices

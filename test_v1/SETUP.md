# Aurum Matrimony - Setup Guide

## Quick Start

### 1. Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- MinIO (or S3-compatible storage)

### 2. Environment Setup

```bash
# Create virtual environment
python -m venv aurum_env
aurum_env\Scripts\activate  # Windows
# source aurum_env/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 3. Infrastructure Setup

#### PostgreSQL
```sql
-- Connect to PostgreSQL and create database
CREATE DATABASE aurum_db;
CREATE USER aurum_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE aurum_db TO aurum_user;
```

#### Redis (Windows)
Download and install Redis from: https://github.com/microsoftarchive/redis/releases

#### MinIO (Windows)
```bash
# Download MinIO
# Run MinIO server
minio.exe server ./sample_image_database --console-address ":9001"
```

### 4. Configuration

Copy `.env.example` to `.env` and update the values:

```bash
cp .env.example .env
```

Update database credentials in `.env`:
```env
POSTGRES_URL=postgresql+asyncpg://aurum_user:your_password@localhost:5432/aurum_db
ONBOARDING_POSTGRES_URL=postgresql://aurum_user:your_password@localhost:5432/aurum_db
```

### 5. Initialize Database

```bash
# Create all tables and admin user
python init_db.py
```

### 6. Run the Application

```bash
# Development server
python run_dev.py

# Or using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Test the API

Visit: http://localhost:8000/docs for Swagger UI

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user
- `POST /api/v1/auth/refresh` - Refresh tokens
- `GET /api/v1/auth/me` - Get current user info
- `GET /api/v1/auth/mfa/setup` - Setup MFA
- `POST /api/v1/auth/mfa/enable` - Enable MFA

### Onboarding
- `POST /api/v1/onboarding/signup` - User signup with basic profile
- `POST /api/v1/onboarding/complete-profile/{user_id}` - Complete user profile
- `GET /api/v1/onboarding/verification-status/{user_id}` - Check verification status
- `GET /api/v1/onboarding/admin/pending-verifications` - Get pending verifications (admin)
- `POST /api/v1/onboarding/admin/verify-user/{user_id}` - Approve/reject user (admin)

### Profiles
- `GET /api/v1/profiles/me` - Get current user's full profile
- `GET /api/v1/profiles/me/summary` - Get current user's profile summary
- `GET /api/v1/profiles/dashboard` - Get user dashboard data
- `PATCH /api/v1/profiles/me` - Update current user's profile
- `GET /api/v1/profiles/{user_id}` - View another user's profile
- `GET /api/v1/profiles/{user_id}/summary` - View another user's profile summary

### Moderation
- `POST /api/v1/moderation/report` - Report a user for inappropriate behavior
- `POST /api/v1/moderation/block` - Block a user
- `DELETE /api/v1/moderation/block/{user_id}` - Unblock a user
- `GET /api/v1/moderation/my-reports` - Get reports made by current user
- `GET /api/v1/moderation/my-blocks` - Get users blocked by current user
- `GET /api/v1/moderation/admin/reports` - Get pending reports (admin)
- `POST /api/v1/moderation/admin/reports/{report_id}/resolve` - Resolve report (admin)

### Matching
- `GET /api/v1/matching/recommendations` - Get personalized match recommendations
- `POST /api/v1/matching/search` - Search matches with detailed filters
- `GET /api/v1/matching/search` - Search matches with URL parameters
- `POST /api/v1/matching/shortlist` - Add user to shortlist
- `DELETE /api/v1/matching/shortlist/{user_id}` - Remove from shortlist
- `GET /api/v1/matching/shortlisted` - Get shortlisted users

### Media
- `POST /api/v1/media/upload` - Upload and process images
- `POST /api/v1/media/profile-image` - Set profile image
- `GET /api/v1/media/my-images` - Get user's uploaded images

### Notifications
- `GET /api/v1/notifications` - Get user notifications
- `POST /api/v1/notifications/mark-read` - Mark notifications as read
- `GET /api/v1/notifications/unread-count` - Get unread notification count

### Chat
- `GET /api/v1/chat/conversations` - Get user's conversations
- `GET /api/v1/chat/conversations/{id}/messages` - Get messages in conversation
- `POST /api/v1/chat/conversations/{user_id}` - Start conversation with user
- `POST /api/v1/chat/messages` - Send a message
- `POST /api/v1/chat/conversations/{id}/read` - Mark messages as read
- `WebSocket /ws/chat` - Real-time messaging

### Calls
- `WebSocket /ws/call` - WebRTC call signalling (audio/video calls)

### Example Usage

#### Register User
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+919876543210",
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

#### Login
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+919876543210",
    "password": "securepassword123"
  }'
```

## Development Status

### ✅ Completed - Full Platform
- **Core infrastructure** (config, db, security, cache, storage, rate limiting)
- **Identity domain** (authentication, MFA, user management)
- **Onboarding domain** (signup, profile completion, admin verification)
- **Profiles domain** (profile viewing, dashboard, updates with caching)
- **Moderation domain** (reporting, blocking, admin management)
- **Matching domain** (search, recommendations, shortlisting with caching)
- **Media domain** (image upload, processing, profile pictures)
- **Notifications domain** (in-app notifications, unread tracking)
- **Chat domain** (HTTP + WebSocket messaging, conversations)
- **Calls domain** (WebRTC signalling for audio/video calls)
- **Complete database schema** with all necessary tables and indexes
- **Production-ready** FastAPI setup with comprehensive error handling

### 🚧 Ready for Enhancement
- Database migrations with Alembic
- Advanced matching algorithms
- Push notifications (FCM/APNs)
- Email/SMS notifications
- Advanced admin dashboard
- Analytics and reporting
- Payment integration
- Mobile app APIs

### 📋 TODO
- Profiles domain
- Matching domain
- Chat domain (HTTP + WebSocket)
- Calls domain (WebSocket signalling)
- Media domain (image upload/processing)
- Notifications domain
- Moderation domain
- Admin verification workflow

## Database Schema

The application will automatically create tables on startup. For production, use proper migrations with Alembic.

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Ensure PostgreSQL is running
   - Check database credentials in `.env`
   - Verify database exists

2. **Redis Connection Error**
   - Ensure Redis server is running
   - Check Redis host/port in `.env`

3. **MinIO Connection Error**
   - Ensure MinIO server is running
   - Check MinIO credentials in `.env`
   - Verify bucket permissions

4. **Import Errors**
   - Ensure virtual environment is activated
   - Install all requirements: `pip install -r requirements.txt`

### Logs
Check application logs for detailed error information. The development server runs with `log_level="info"`.

## Next Steps

1. Set up your infrastructure (PostgreSQL, Redis, MinIO)
2. Update `.env` with your actual credentials
3. Run the application: `python run_dev.py`
4. Test authentication endpoints
5. Implement remaining domains as needed

For production deployment, see the main README.md file.
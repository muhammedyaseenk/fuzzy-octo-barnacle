````markdown
# Aurum Matrimony Platform – Backend

World-class, production-grade backend for a Kerala-first matrimony platform.

This backend is designed as a **modular monolith, ready to be split into microservices** later.  
Domains are clearly separated, but the file structure stays **simple** so every developer can understand it quickly.

---

## ✨ Key Features

- **Identity & Security**
  - Signup with phone/email & password
  - JWT-based auth (access + refresh tokens)
  - Optional MFA (TOTP, QR code)
  - Role-based access (user, admin, moderator)

- **Onboarding & Profiles**
  - Multi-step onboarding: basic + profile + education + career + family + preferences
  - Profile completion tracking
  - Admin verification queue

- **Moderation & Safety**
  - Admin profile verification flow
  - User reports & blocks
  - Audit logs for critical actions

- **Matching & Discovery**
  - Filtered profile search (age, height, religion, caste, location, income, etc.)
  - Feed endpoints with Redis caching
  - Shortlist / ignore / blocked user handling

- **Chat & Calls**
  - Real-time 1:1 chat via WebSockets
  - Call signalling endpoints for audio/video calls (WebRTC/SIP integration ready)
  - Block/report rules enforced at messaging layer

- **Media**
  - Image upload to MinIO (S3 compatible)
  - On-the-fly image processing (tiny/medium/full sizes)
  - Signed URLs for secure access

- **Notifications**
  - In-app notifications API
  - Extensible for SMS / email / push

- **Ops & Infra**
  - PostgreSQL as primary DB
  - asyncpg for high-performance onboarding queries
  - SQLAlchemy for core domain models
  - Redis for caching feeds & profiles
  - MinIO for object storage
  - SlowAPI for rate limiting
  - CORS configured for Flutter Web & Mobile

---

## 🏗 Architecture Overview

High-level domain view:

```text
               ┌──────────────────────────────┐
               │         API Gateway          │
               │      (FastAPI main app)      │
               └─────────────┬────────────────┘
                             │
               ┌─────────────┼───────────────────────┐
               │             │                       │
        ┌──────▼──────┐ ┌────▼─────────┐      ┌──────▼───────┐
        │  Identity   │ │  Onboarding  │      │   Profiles   │
        │  (auth)     │ │  (asyncpg)   │      │   & Matching │
        └────┬────────┘ └────┬─────────┘      └──────┬───────┘
             │               │                        │
        ┌────▼────────┐ ┌────▼──────────┐       ┌─────▼────────┐
        │ Moderation  │ │  Chat & Calls │       │   Media      │
        │ (reports,   │ │  (WebSocket)  │       │ (MinIO / img)│
        │ blocks)     │ └───────────────┘       └──────────────┘
        └────┬────────┘
             │
        ┌────▼────────┐
        │Notifications│
        └─────────────┘
````

All modules share common infra from `app/core`:

* Config, env
* DB connections (SQLAlchemy + asyncpg pool)
* Redis client
* MinIO client
* Security utilities (JWT, password hashing)
* Rate limiting

---

## 📁 Project Structure

> This structure is intentionally **minimal but clear**. Each domain has only a few files.

```bash
backend/
  app/
    __init__.py
    main.py               # FastAPI app, router wiring, startup

    core/
      __init__.py
      config.py           # Config / env settings
      db.py               # SQLAlchemy engine, AsyncSession, asyncpg pool init
      security.py         # JWT helpers, password hashing, get_current_user, roles
      cache.py            # Redis helpers for profile/feed caching
      storage.py          # MinIO client & helpers (ensure_bucket, upload, signed URL)
      rate_limit.py       # SlowAPI limiter setup (optional)

    domains/
      identity/           # Signup, login, JWT, MFA, roles
        __init__.py
        api.py            # /auth routes
        models.py         # User, Session, etc. (SQLAlchemy)
        schemas.py        # UserCreate, UserRead, Token, etc.
        service.py        # Business logic (create_user, authenticate, etc.)

      onboarding/         # Multi-step onboarding & admin verification
        __init__.py
        api.py            # /onboarding/signup, /onboarding/complete-profile, /onboarding/admin...
        schemas.py        # Gender, MaritalStatus, UserSignupRequest, CompleteOnboardingRequest, etc.
        service.py        # asyncpg logic for insert/update into onboarding tables

      profiles/           # User profile view/update + dashboard snippets
        __init__.py
        api.py            # /profiles/me, /profiles/{id}, profile update, dashboard data
        models.py         # Profile, Education, Career, Family, Preferences (SQLAlchemy or views)
        service.py        # Read/write logic

      moderation/         # Reports & blocks
        __init__.py
        api.py            # /moderation/report, /moderation/block, /moderation/admin/...
        models.py         # UserReport, UserBlock, risk flags
        service.py        # Enforce business rules, integrate with chat/matching

      matching/           # Search & recommendations
        __init__.py
        api.py            # /matching/feed, /matching/search, /matching/shortlist
        models.py         # Match, Shortlist, etc. (optional)
        service.py        # Scoring, feed generation, filtering

      chat/               # Real-time chat
        __init__.py
        api_http.py       # /chat/conversations, /chat/messages, etc.
        api_ws.py         # /ws/chat (WebSocket)
        models.py         # Conversation, Message
        service.py        # Send message, load history, unread counts

      calls/              # Audio/video call signalling
        __init__.py
        api_ws.py         # /ws/call (WebSocket signalling)
        service.py        # Offer/answer, ICE forwarding, integration hooks for SFU/TURN

      media/              # Upload & image processing
        __init__.py
        api.py            # /media/upload, /media/profile-image
        service.py        # process_image, store in MinIO, return URLs

      notifications/      # User notifications
        __init__.py
        api.py            # /notifications, mark-as-read
        service.py        # Send email/SMS/push (integrate with providers later)
```

---

## 🧱 Tech Stack

* **Language:** Python 3.11+
* **Framework:** FastAPI
* **DB:** PostgreSQL

  * SQLAlchemy (async) for core domains
  * asyncpg connection pool for high-volume onboarding inserts/updates
* **Cache:** Redis
* **Object Storage:** MinIO (S3 compatible)
* **Auth:** JWT (access + refresh), OAuth2PasswordBearer
* **Security:** Passlib (bcrypt), pyotp, qrcode, rate limiting with SlowAPI
* **Images:** Pillow (PIL), WebP output
* **Runtime:** uvicorn / gunicorn (for production)
* **Containers (optional):** Docker & Docker Compose

---

## ⚙️ Configuration

Create a `.env` file at the project root (or use env variables in your deployment):

```env
# Environment
ENV=dev

# PostgreSQL
POSTGRES_URL=postgresql+asyncpg://postgres:password@localhost:5432/aurum_db
ONBOARDING_POSTGRES_URL=postgresql://postgres:password@localhost:5432/aurum_db

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_BUCKET=profile-images

# Auth / Security
SECRET_KEY=super_secret_prod_key_change_me
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Images
IMAGE_RAM_TINY=./images/tiny
IMAGE_RAM_MEDIUM=./images/medium

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:4200", "http://localhost:8080", "http://localhost:5173"]
```

> In production, **never** commit `.env`, and use a real secret key.

---

## 🚀 Getting Started (Local Development)

### 1. Prerequisites

* Python 3.11+
* PostgreSQL running locally
* Redis running locally
* MinIO running locally (or S3-compatible storage)
* `pip` or `poetry`

Minimal Docker for infra (optional):

```bash
docker run -d --name aurum-postgres \
  -e POSTGRES_PASSWORD=mysecretpassword \
  -e POSTGRES_DB=aurum_db \
  -p 5432:5432 postgres:16

docker run -d --name aurum-redis -p 6379:6379 redis:7

docker run -d --name aurum-minio \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  quay.io/minio/minio server /data --console-address ":9001"
```

### 2. Install dependencies

From the `backend/` directory:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt
# or: poetry install
```

### 3. Set up environment

Create `.env` with values as above (adjust DB passwords, etc.).

### 4. Run database migrations (if using Alembic)

If you have Alembic configured:

```bash
alembic upgrade head
```

If not yet, the app can create tables automatically on startup via SQLAlchemy metadata (development only; for production use migrations).

### 5. Run the server

```bash
uvicorn app.main:app --reload
```

API will be available at:

* Swagger UI: `http://localhost:8000/docs`
* ReDoc: `http://localhost:8000/redoc`

---

## 🔐 Authentication & Authorization

* **Signup**

  * `/api/v1/auth/register`
  * Creates `User` with:

    * `is_active = False`
    * `role = "user"`
    * `admin_approved = False` (via onboarding/admin flow)

* **Login**

  * `/api/v1/auth/login`
  * Returns:

    * `access_token` (short-lived)
    * `refresh_token` (long-lived)
    * `token_type = "bearer"`

* **Refresh token**

  * `/api/v1/auth/refresh`
  * Validates refresh token and issues new access & refresh tokens.

* **MFA**

  * `/api/v1/auth/mfa/qrcode` – generates QR for TOTP apps
  * `login` can require `mfa_code` if `mfa_secret` exists.

* **Role based**

  * `get_current_user` reads `sub` & `role` from JWT.
  * `require_roles("admin", "moderator")` guards sensitive endpoints like:

    * `/onboarding/admin/*`
    * `/moderation/admin/*`

---

## 👤 Onboarding Flow

> Implemented with asyncpg for performance; lives in `domains/onboarding`.

1. **User Signup**

   * Endpoint: `POST /api/v1/onboarding/signup`
   * Stores:

     * `users`: phone, email, WhatsApp, password hash, verification token
     * `user_profiles`: first_name, last_name (initial row)
   * Returns: `user_id` + message prompting to complete profile.

2. **Complete Profile**

   * Endpoint: `POST /api/v1/onboarding/complete-profile/{user_id}`
   * Request body: `CompleteOnboardingRequest`:

     * `profile` (Basic + physical + location + religion/community + lifestyle)
     * `education`
     * `career`
     * `family`
     * `preferences`
   * Writes to:

     * `user_profiles`
     * `user_education`
     * `user_career`
     * `user_family`
     * `user_preferences`
     * `admin_verification_queue (status='Pending')`

3. **Check Verification Status**

   * Endpoint: `GET /api/v1/onboarding/verification-status/{user_id}`
   * Returns:

     * `admin_approved`
     * `verification_status` (Pending/Approved/Rejected)
     * `admin_notes`
     * timestamps

4. **Admin Verification**

   * `GET /api/v1/onboarding/admin/pending-verifications`
   * `POST /api/v1/onboarding/admin/verify-user/{user_id}?approved=true/false`
   * On approve:

     * `users.admin_approved = true`
     * Optionally `users.is_active = true`

---

## 🛡 Moderation & Safety

Endpoints (in `domains/moderation/api.py`):

* `POST /api/v1/moderation/report`

  * Payload: reported user, reason, optional extra details.
  * Inserts into `user_reports` (status: Pending).

* `POST /api/v1/moderation/block`

  * Payload: `blocked_user_id`
  * Inserts into `user_blocks`.

* `GET /api/v1/moderation/admin/reports?status=Pending`

* `POST /api/v1/moderation/admin/reports/{report_id}/resolve`

Integration:

* Chat and matching services consult `moderation.service` to:

  * Prevent messaging blocked users.
  * Exclude blocked/severely flagged users from feeds.

---

## 📸 Media & Images

Endpoints (in `domains/media/api.py`):

* `POST /api/v1/media/upload`

  * Accepts `UploadFile`
  * Uses Pillow to:

    * Save temp original
    * Generate:

      * Tiny (≈200x200, WebP)
      * Medium (≈800x800, WebP)
  * Uploads full JPG to MinIO via `storage.upload_full_image`
  * Returns:

    * `image_id`
    * `tiny_url` (local path or signed URL)
    * `medium_url`

MinIO is prepared at startup:

* `ensure_bucket()` checks & creates `MINIO_BUCKET`.

---

## 💬 Chat & 📞 Calls (Signalling)

Chat (HTTP):

* `/api/v1/chat/conversations`
* `/api/v1/chat/messages/{conversation_id}`
* `/api/v1/chat/messages/send`

Chat (WebSocket):

* `/ws/chat`

  * Join conversation, send/receive messages in real time.
  * Enforces:

    * Auth via JWT
    * Block rules from `moderation.service`

Calls (WebSocket signalling):

* `/ws/call`

  * Handles:

    * `offer`, `answer`, `ice_candidate`
  * Integrates with WebRTC/SIP clients on mobile/web apps.

> Actual media (audio/video) flows P2P or via SFU; the backend only orchestrates signalling.

---

## 📊 Matching & Dashboard

Matching endpoints:

* `GET /api/v1/matching/feed`

  * Uses:

    * Profile/preferences
    * Filters (age, height, caste, district, income, etc.)
    * Redis caching for popular queries
* `GET /api/v1/matching/search`

  * Advanced search with query parameters.
* `GET /api/v1/matching/shortlisted`

Dashboard:

* `GET /api/v1/dashboard`

  * Aggregates:

    * Profile summary
    * Recommendation summary
    * Recent chats
    * Notifications
  * This may live in `profiles.api` or its own small `dashboard` module depending on your preference.

---

## 📬 Notifications

Endpoints:

* `GET /api/v1/notifications`
* `POST /api/v1/notifications/mark-read`

Internally, `notifications.service` can:

* Send in-app notifications immediately
* Push tasks for:

  * SMS (via Twilio, etc.)
  * Email (via SES/SendGrid, etc.)
  * Push notifications (FCM/APNs)

---

## 🧪 Testing

Recommended patterns:

* Unit tests per domain:

  * `tests/domains/identity/`
  * `tests/domains/onboarding/`, etc.
* Use:

  * Test database (separate schema or in-memory)
  * Fake MinIO / Redis in tests (or Docker containers)

Example test run:

```bash
pytest
```

---

## 🛠 Coding Conventions

* **Domain-first**: all features live under `app/domains/<domain_name>`.
* **One main FastAPI app**: `app/main.py` wires everything.
* **Few files per domain**:

  * `api.py` → endpoints
  * `schemas.py` → Pydantic models
  * `models.py` → SQLAlchemy models (if used)
  * `service.py` → business logic
* **Shared infra** lives in `app/core`.
* **No circular imports**: domains depend on `core`, but not on each other directly (use services if needed).

---

## 🚢 Production Deployment Notes

* Run under **gunicorn + uvicorn workers** or equivalent:

  ```bash
  gunicorn -k uvicorn.workers.UvicornWorker app.main:app -b 0.0.0.0:8000 -w 4
  ```
* Put **Nginx** or another reverse proxy in front for:

  * TLS termination
  * HTTP/2
  * WebSocket upgrade
* Use:

  * Managed PostgreSQL / Redis / object storage
  * Centralized logging (ELK / Loki / etc.)
  * Monitoring (Prometheus + Grafana)

---

## ✅ Summary

* Single repository, **simple structure**, easy for every developer to navigate.
* Clear domain separation so you can:

  * Scale features independently
  * Eventually split into true microservices if needed
* Ready for:

  * High-throughput onboarding
  * Secure auth & moderation
  * Real-time chat & call signalling
  * Rich profile and matching logic for a premium matrimony experience.

```
```

# 🚀 Aurum Matrimony - ONE COMMAND DEPLOYMENT

## Start Entire Production Stack in 60 Seconds

```bash
docker-compose up -d
```

That's it! Your entire premium matrimony platform is now running.

## What Gets Deployed

✅ **PostgreSQL** - Database (port 5432)
✅ **Redis** - Cache (port 6379)
✅ **MinIO** - Object Storage (ports 9000, 9001)
✅ **RabbitMQ** - Message Queue (ports 5672, 15672)
✅ **FastAPI** - API Server (port 8000)
✅ **Celery Workers** - Background Tasks
✅ **Celery Beat** - Scheduled Tasks
✅ **Nginx** - Reverse Proxy (ports 80, 443)

## Prerequisites

- Docker Desktop installed
- 8GB RAM minimum
- 20GB disk space

## Quick Start

```bash
# 1. Clone/Navigate to project
cd D:\auram_sharahiya

# 2. Start everything
docker-compose up -d

# 3. Wait for services (30-60 seconds)
docker-compose ps

# 4. Initialize database
docker-compose exec api python init_db.py

# 5. Access the platform
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
# MinIO Console: http://localhost:9001
# RabbitMQ Console: http://localhost:15672
```

## Verify Deployment

```bash
# Check all services are running
docker-compose ps

# Should show 8 services as "Up"
# ✅ postgres
# ✅ redis
# ✅ minio
# ✅ rabbitmq
# ✅ api
# ✅ celery-worker
# ✅ celery-beat
# ✅ nginx

# Test API
curl http://localhost/health

# View logs
docker-compose logs -f api
```

## Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| **API** | http://localhost:8000 | - |
| **API Docs** | http://localhost:8000/docs | - |
| **Nginx** | http://localhost | - |
| **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin2024 |
| **RabbitMQ Console** | http://localhost:15672 | aurum_user / rabbitmq_password_2024 |
| **PostgreSQL** | localhost:5432 | aurum_user / aurum_password_2024 |
| **Redis** | localhost:6379 | redis_password_2024 |

## Test the Platform

```bash
# 1. Create admin user
curl -X POST http://localhost/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+919999999999",
    "email": "admin@aurum.com",
    "password": "admin123"
  }'

# 2. Login
curl -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+919999999999",
    "password": "admin123"
  }'

# 3. Get token and test authenticated endpoint
TOKEN="<your_access_token>"
curl http://localhost/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

## Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (CAUTION: deletes data)
docker-compose down -v
```

## Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart api
docker-compose restart celery-worker
```

## View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f celery-worker
docker-compose logs -f nginx

# Last 100 lines
docker-compose logs --tail=100 api
```

## Scale Services

```bash
# Scale API to 3 instances
docker-compose up -d --scale api=3

# Scale Celery workers to 5
docker-compose up -d --scale celery-worker=5
```

## Troubleshooting

### Services not starting
```bash
# Check logs
docker-compose logs

# Restart specific service
docker-compose restart postgres
```

### Database connection error
```bash
# Wait for PostgreSQL to be ready
docker-compose exec postgres pg_isready -U aurum_user

# Reinitialize database
docker-compose exec api python init_db.py
```

### Port already in use
```bash
# Change ports in docker-compose.yml
# Example: "8001:8000" instead of "8000:8000"
```

### Out of memory
```bash
# Increase Docker Desktop memory to 8GB
# Settings → Resources → Memory
```

## Production Deployment

For production, use:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

Or deploy to Kubernetes:
```bash
kubectl apply -f k8s/
```

## Monitoring

```bash
# Resource usage
docker stats

# Service health
docker-compose ps

# API health
curl http://localhost/health

# RabbitMQ queues
# Visit http://localhost:15672
```

## Backup

```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U aurum_user aurum_db > backup.sql

# Backup MinIO
docker-compose exec minio mc mirror /data /backup
```

## Update Application

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up -d --build
```

## Environment Variables

Edit `docker-compose.yml` to change:
- Database passwords
- Redis password
- MinIO credentials
- RabbitMQ credentials
- JWT secret key

## Performance Tips

1. **Increase worker concurrency**
   ```yaml
   celery-worker:
     command: celery -A app.celery_app worker --concurrency=8
   ```

2. **Add more API instances**
   ```bash
   docker-compose up -d --scale api=5
   ```

3. **Increase PostgreSQL connections**
   ```yaml
   postgres:
     command: postgres -c max_connections=200
   ```

## Complete Stack Architecture

```
┌─────────────────────────────────────────┐
│         Internet / Users                 │
└──────────────┬──────────────────────────┘
               │
        ┌──────▼──────┐
        │    Nginx    │ (Port 80/443)
        │ Rate Limit  │
        │   Caching   │
        └──────┬──────┘
               │
        ┌──────▼──────┐
        │  FastAPI    │ (Port 8000)
        │  API Server │
        └──────┬──────┘
               │
    ┌──────────┼──────────┐
    │          │          │
┌───▼───┐  ┌──▼───┐  ┌──▼────┐
│Postgres│ │Redis │  │ MinIO │
│  DB    │ │Cache │  │Storage│
└────────┘ └──────┘  └───────┘
    │
    │
┌───▼────────┐
│  RabbitMQ  │
│   Queue    │
└───┬────────┘
    │
┌───▼────────┐
│   Celery   │
│  Workers   │
└────────────┘
```

## Success Indicators

✅ All 8 services show "Up" status
✅ API responds at http://localhost/health
✅ Swagger docs accessible at http://localhost/docs
✅ Can create user and login
✅ MinIO console accessible
✅ RabbitMQ console accessible
✅ No errors in logs

## Next Steps

1. ✅ Platform is running
2. Create admin user via API
3. Test all endpoints in Swagger UI
4. Upload test images
5. Create test profiles
6. Test matching algorithm
7. Test chat functionality
8. Monitor Celery tasks in RabbitMQ console

---

**Your premium matrimony platform is now live!** 🎉

Access the API documentation: http://localhost:8000/docs
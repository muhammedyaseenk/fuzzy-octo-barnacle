# Aurum Matrimony - Production Deployment Guide

## 🚀 Production-Ready Kubernetes Deployment

### Prerequisites

1. **Kubernetes Cluster** (v1.24+)
2. **kubectl** configured
3. **Docker** installed
4. **KEDA** installed in cluster
5. **Nginx Ingress Controller**
6. **Cert-Manager** for SSL

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Load Balancer                         │
│                   (Nginx Ingress)                        │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼────────┐      ┌────────▼────────┐
│   API Pods     │      │  WebSocket Pods │
│  (3-10 pods)   │      │   (Auto-scale)  │
└───────┬────────┘      └────────┬────────┘
        │                        │
        └────────────┬───────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼────────┐      ┌────────▼────────┐
│   PostgreSQL   │      │     Redis       │
│  (StatefulSet) │      │   (Deployment)  │
└────────────────┘      └─────────────────┘
        │                        │
        └────────────┬───────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼────────┐      ┌────────▼────────┐
│    RabbitMQ    │      │     MinIO       │
│  (StatefulSet) │      │  (Deployment)   │
└───────┬────────┘      └─────────────────┘
        │
┌───────▼────────┐
│ Celery Workers │
│  (2-20 pods)   │
│  KEDA Scaling  │
└────────────────┘
```

## Step 1: Build Docker Image

```bash
cd D:\auram_sharahiya
docker build -t aurum-matrimony-api:latest -f docker/Dockerfile .
docker tag aurum-matrimony-api:latest your-registry/aurum-matrimony-api:latest
docker push your-registry/aurum-matrimony-api:latest
```

## Step 2: Update Secrets

Edit `k8s/secrets.yaml` with production values:

```bash
# Generate secure passwords
openssl rand -base64 32  # For each secret
```

## Step 3: Deploy to Kubernetes

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Apply secrets and config
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml

# Deploy infrastructure
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/minio.yaml
kubectl apply -f k8s/rabbitmq.yaml

# Wait for infrastructure to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n aurum-matrimony --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n aurum-matrimony --timeout=300s
kubectl wait --for=condition=ready pod -l app=rabbitmq -n aurum-matrimony --timeout=300s

# Initialize database
kubectl run -it --rm init-db --image=aurum-matrimony-api:latest --restart=Never -n aurum-matrimony -- python init_db.py

# Deploy application
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/celery-worker.yaml

# Apply autoscaling
kubectl apply -f k8s/hpa.yaml

# Deploy KEDA scalers
kubectl apply -f k8s/keda-scaledobject.yaml

# Setup ingress
kubectl apply -f k8s/ingress.yaml
```

## Step 4: Install KEDA (if not installed)

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm repo update
helm install keda kedacore/keda --namespace keda --create-namespace
```

## Step 5: Verify Deployment

```bash
# Check all pods
kubectl get pods -n aurum-matrimony

# Check services
kubectl get svc -n aurum-matrimony

# Check ingress
kubectl get ingress -n aurum-matrimony

# View logs
kubectl logs -f deployment/aurum-api -n aurum-matrimony
kubectl logs -f deployment/celery-worker -n aurum-matrimony
```

## Monitoring

```bash
# Watch pod scaling
kubectl get hpa -n aurum-matrimony -w

# Watch KEDA scaling
kubectl get scaledobject -n aurum-matrimony -w

# Check RabbitMQ queue length
kubectl port-forward svc/rabbitmq-service 15672:15672 -n aurum-matrimony
# Visit http://localhost:15672
```

## Environment Variables

Production `.env`:

```env
ENV=production
POSTGRES_URL=postgresql+asyncpg://aurum_user:SECURE_PASSWORD@postgres-service:5432/aurum_db
REDIS_HOST=redis-service
REDIS_PASSWORD=SECURE_REDIS_PASSWORD
MINIO_ENDPOINT=minio-service:9000
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=SECURE_MINIO_PASSWORD
RABBITMQ_URL=amqp://aurum_user:SECURE_RABBITMQ_PASSWORD@rabbitmq-service:5672/
SECRET_KEY=SECURE_JWT_SECRET_KEY_64_CHARS
```

## Scaling Configuration

### API Pods
- **Min**: 3 replicas
- **Max**: 10 replicas
- **Trigger**: CPU > 70%, Memory > 80%

### Celery Workers
- **Min**: 2 replicas
- **Max**: 20 replicas
- **Trigger**: RabbitMQ queue length > 10 messages

### KEDA Benefits
- Event-driven autoscaling based on RabbitMQ queue depth
- Scale to zero when no tasks (optional)
- Faster response to load spikes

## Session Management

Sessions are stored in PostgreSQL with automatic cleanup:
- **Session Duration**: 60 minutes
- **Cleanup**: Hourly via Celery Beat
- **Tracking**: IP address, user agent, last activity

## Celery Tasks

### Queues
- **celery**: Default queue for general tasks
- **notifications**: High-priority notifications
- **matching**: Match calculations
- **media**: Image processing

### Periodic Tasks
- **Daily matches**: Send recommendations (daily)
- **Session cleanup**: Remove expired sessions (hourly)
- **Analytics**: Generate reports (every 6 hours)

## Security Checklist

- [ ] Update all secrets in `k8s/secrets.yaml`
- [ ] Enable SSL/TLS with cert-manager
- [ ] Configure firewall rules
- [ ] Enable pod security policies
- [ ] Set up network policies
- [ ] Configure backup strategy
- [ ] Enable audit logging
- [ ] Set resource limits on all pods
- [ ] Use private container registry
- [ ] Enable RBAC

## Backup Strategy

```bash
# PostgreSQL backup
kubectl exec -it postgres-0 -n aurum-matrimony -- pg_dump -U aurum_user aurum_db > backup.sql

# MinIO backup
kubectl exec -it minio-pod -n aurum-matrimony -- mc mirror /data /backup
```

## Rollback

```bash
# Rollback API deployment
kubectl rollout undo deployment/aurum-api -n aurum-matrimony

# Rollback to specific revision
kubectl rollout undo deployment/aurum-api --to-revision=2 -n aurum-matrimony
```

## Performance Tuning

### PostgreSQL
- Connection pooling: 20 connections
- Shared buffers: 25% of RAM
- Effective cache size: 75% of RAM

### Redis
- Max memory: 1GB
- Eviction policy: allkeys-lru

### Celery
- Concurrency: 4 workers per pod
- Prefetch multiplier: 1
- Max tasks per child: 1000

## Cost Optimization

1. **Use spot instances** for Celery workers
2. **Enable cluster autoscaler**
3. **Set appropriate resource requests/limits**
4. **Use KEDA** to scale to zero during low traffic
5. **Implement caching** aggressively

## Troubleshooting

### Pods not starting
```bash
kubectl describe pod <pod-name> -n aurum-matrimony
kubectl logs <pod-name> -n aurum-matrimony
```

### Database connection issues
```bash
kubectl exec -it postgres-0 -n aurum-matrimony -- psql -U aurum_user -d aurum_db
```

### Celery tasks not processing
```bash
kubectl logs -f deployment/celery-worker -n aurum-matrimony
kubectl exec -it rabbitmq-0 -n aurum-matrimony -- rabbitmqctl list_queues
```

## Production Checklist

- [ ] All services deployed and healthy
- [ ] Database initialized with schema
- [ ] SSL certificates configured
- [ ] Monitoring and alerting set up
- [ ] Backup strategy implemented
- [ ] Load testing completed
- [ ] Security audit passed
- [ ] Documentation updated
- [ ] Team trained on operations
- [ ] Incident response plan ready

## Support

For production issues:
1. Check pod logs
2. Review metrics in monitoring dashboard
3. Check RabbitMQ management console
4. Review application logs
5. Contact DevOps team

---

**Your premium matrimony platform is now production-ready with enterprise-grade infrastructure!** 🎉
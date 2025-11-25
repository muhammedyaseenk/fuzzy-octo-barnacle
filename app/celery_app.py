# app/celery_app.py
from celery import Celery
from app.core.config import settings

# Create Celery instance
celery_app = Celery(
    "aurum_matrimony",
    broker=settings.RABBITMQ_URL,
    backend=f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/1",
    include=[
        "app.tasks.notifications",
        "app.tasks.matching",
        "app.tasks.media",
        "app.tasks.analytics",
        "app.tasks.engagement"
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Periodic tasks
celery_app.conf.beat_schedule = {
    "send-daily-matches": {
        "task": "app.tasks.matching.send_daily_matches",
        "schedule": 60.0 * 60.0 * 24.0,  # Daily
    },
    "cleanup-expired-sessions": {
        "task": "app.tasks.analytics.cleanup_expired_sessions",
        "schedule": 60.0 * 60.0,  # Hourly
    },
    "generate-analytics": {
        "task": "app.tasks.analytics.generate_daily_analytics",
        "schedule": 60.0 * 60.0 * 6.0,  # Every 6 hours
    },
    "notify-new-users": {
        "task": "notify_new_users_joined",
        "schedule": 60.0 * 60.0 * 24.0,  # Daily at midnight
    },
    "process-engagement-events": {
        "task": "process_engagement_events",
        "schedule": 60.0,  # Every minute
    },
    "send-inactive-reminders": {
        "task": "send_inactive_user_reminders",
        "schedule": 60.0 * 60.0 * 24.0,  # Daily
    },
    "profile-completion-reminders": {
        "task": "send_profile_completion_reminders",
        "schedule": 60.0 * 60.0 * 12.0,  # Twice daily
    },
}
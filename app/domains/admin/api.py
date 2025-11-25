# app/domains/admin/api.py
from fastapi import APIRouter, Depends
from app.core.security import require_roles
from app.core.cache import redis_client
import json

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/alerts")
async def get_admin_alerts(
    current_user: dict = Depends(require_roles(["admin"]))
):
    """Get recent admin alerts for notification failures"""
    alerts = await redis_client.lrange("admin_alerts", 0, 49)
    
    return {
        "alerts": [json.loads(alert) for alert in alerts],
        "count": len(alerts)
    }

@router.get("/notification-failures")
async def get_notification_failures(
    limit: int = 50,
    current_user: dict = Depends(require_roles(["admin"]))
):
    """Get recent notification failures"""
    from app.core.db import AsyncSessionLocal
    from sqlalchemy import text
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text("""
                SELECT user_id, channel, error_message, created_at
                FROM notification_failures
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"limit": limit}
        )
        
        failures = [
            {
                "user_id": row[0],
                "channel": row[1],
                "error": row[2],
                "timestamp": row[3].isoformat()
            }
            for row in result.fetchall()
        ]
    
    return {"failures": failures, "count": len(failures)}

@router.post("/retry-failed-notifications")
async def retry_failed_notifications(
    current_user: dict = Depends(require_roles(["admin"]))
):
    """Retry notifications in retry queue"""
    from app.tasks.notifications import send_push_notification_task
    
    count = 0
    while True:
        notification = await redis_client.rpop("notification_retry_queue")
        if not notification:
            break
        
        data = json.loads(notification)
        send_push_notification_task.delay(
            data["user_id"],
            data["title"],
            data["body"],
            data.get("data")
        )
        count += 1
    
    return {"status": "queued", "count": count}

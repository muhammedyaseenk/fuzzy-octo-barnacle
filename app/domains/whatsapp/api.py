# app/domains/whatsapp/api.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.core.security import get_current_user, require_roles
from app.core.whatsapp_sender import whatsapp_sender
from app.core.cache import redis_client
from pydantic import BaseModel
import json

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

class WhatsAppMessage(BaseModel):
    recipient_id: int
    message: str

class AdminReviewDecision(BaseModel):
    review_id: str
    decision: str  # approve, reject
    admin_notes: str = None

@router.post("/send")
async def send_whatsapp_message(
    msg: WhatsAppMessage,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send WhatsApp message (Premium/Elite only)
    - Automatic AI content moderation
    - Admin review for suspicious content
    - Full audit trail
    """
    
    result = await whatsapp_sender.send_message(
        current_user["id"],
        msg.recipient_id,
        msg.message,
        db
    )
    
    if result["status"] == "forbidden":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=result["error"]
        )
    
    if result["status"] == "blocked":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message blocked for policy violation"
        )
    
    return result

@router.get("/admin/pending-reviews")
async def get_pending_reviews(
    current_user: dict = Depends(require_roles(["admin"]))
):
    """Admin: Get messages pending review"""
    
    reviews = await redis_client.lrange("whatsapp_admin_review_queue", 0, 49)
    
    return {
        "pending_reviews": [json.loads(r) for r in reviews],
        "count": len(reviews)
    }

@router.post("/admin/review")
async def review_message(
    decision: AdminReviewDecision,
    current_user: dict = Depends(require_roles(["admin"])),
    db: AsyncSession = Depends(get_db)
):
    """Admin: Approve or reject flagged message"""
    
    # Get review from queue
    reviews = await redis_client.lrange("whatsapp_admin_review_queue", 0, -1)
    
    review_data = None
    for idx, review in enumerate(reviews):
        data = json.loads(review)
        if str(idx) == decision.review_id:
            review_data = data
            await redis_client.lrem("whatsapp_admin_review_queue", 1, review)
            break
    
    if not review_data:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Log admin decision
    from sqlalchemy import text
    await db.execute(
        text("""
            INSERT INTO whatsapp_admin_reviews 
            (sender_id, recipient_id, message_content, decision, admin_id, admin_notes, created_at)
            VALUES (:sender, :recipient, :message, :decision, :admin, :notes, NOW())
        """),
        {
            "sender": review_data["sender_id"],
            "recipient": review_data["recipient_id"],
            "message": review_data["message"],
            "decision": decision.decision,
            "admin": current_user["id"],
            "notes": decision.admin_notes
        }
    )
    await db.commit()
    
    # If approved, send the message
    if decision.decision == "approve":
        result = await whatsapp_sender._send_whatsapp_api(
            await whatsapp_sender._get_user_whatsapp(review_data["recipient_id"], db),
            review_data["message"]
        )
        
        # Notify sender
        from app.tasks.notifications import send_push_notification_task
        send_push_notification_task.delay(
            review_data["sender_id"],
            "Message Approved",
            "Your WhatsApp message has been approved and sent",
            {"type": "whatsapp_approved"}
        )
        
        return {"status": "approved_and_sent", "message_id": result.get("message_id")}
    
    else:
        # Notify sender of rejection
        from app.tasks.notifications import send_push_notification_task
        send_push_notification_task.delay(
            review_data["sender_id"],
            "Message Rejected",
            "Your WhatsApp message was rejected for policy violation",
            {"type": "whatsapp_rejected"}
        )
        
        return {"status": "rejected"}

@router.get("/admin/violations")
async def get_content_violations(
    limit: int = 50,
    current_user: dict = Depends(require_roles(["admin"]))
):
    """Admin: Get content violations"""
    from sqlalchemy import text
    
    async with get_db() as db:
        result = await db.execute(
            text("""
                SELECT sender_id, recipient_id, message_content, violation_reason, severity, created_at
                FROM content_violations
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"limit": limit}
        )
        
        violations = [
            {
                "sender_id": row[0],
                "recipient_id": row[1],
                "message": row[2],
                "reason": row[3],
                "severity": row[4],
                "timestamp": row[5].isoformat()
            }
            for row in result.fetchall()
        ]
    
    return {"violations": violations, "count": len(violations)}

@router.get("/admin/costs")
async def get_whatsapp_costs(
    current_user: dict = Depends(require_roles(["admin"]))
):
    """Admin: Get WhatsApp usage costs"""
    
    # Get all user costs for current month
    month_pattern = f"whatsapp_cost:*:{datetime.now().strftime('%Y%m')}"
    keys = await redis_client.keys(month_pattern)
    
    total_cost = 0
    user_costs = []
    
    for key in keys:
        cost = float(await redis_client.get(key) or 0)
        user_id = int(key.split(":")[1])
        total_cost += cost
        user_costs.append({"user_id": user_id, "cost": cost})
    
    user_costs.sort(key=lambda x: x["cost"], reverse=True)
    
    return {
        "total_cost": round(total_cost, 2),
        "top_users": user_costs[:20],
        "month": datetime.now().strftime('%Y-%m')
    }

@router.post("/admin/block-user/{user_id}")
async def block_user_whatsapp(
    user_id: int,
    current_user: dict = Depends(require_roles(["admin"]))
):
    """Admin: Block user from WhatsApp messaging"""
    
    await redis_client.setex(f"blocked_user:{user_id}", 86400 * 30, "1")  # 30 days
    
    return {"status": "blocked", "user_id": user_id, "duration_days": 30}

@router.delete("/admin/unblock-user/{user_id}")
async def unblock_user_whatsapp(
    user_id: int,
    current_user: dict = Depends(require_roles(["admin"]))
):
    """Admin: Unblock user from WhatsApp messaging"""
    
    await redis_client.delete(f"blocked_user:{user_id}")
    
    return {"status": "unblocked", "user_id": user_id}

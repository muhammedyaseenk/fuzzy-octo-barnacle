# app/domains/engagement/api.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.core.db import get_db
from app.core.security import get_current_user, require_roles
from app.core.rule_engine import rule_engine
from app.domains.engagement.models import ContactApproval
from app.domains.engagement.service import EngagementService
from app.domains.engagement.models import EventType
from pydantic import BaseModel

router = APIRouter(prefix="/engagement", tags=["engagement"])

class ContactRequest(BaseModel):
    target_user_id: int

class ContactApprovalUpdate(BaseModel):
    approval_id: int
    status: str
    admin_notes: str = None

@router.post("/contact/request")
async def request_contact_access(
    request: ContactRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Request access to view contact details (for free users)"""
    
    # Check if already requested
    result = await db.execute(
        select(ContactApproval).where(
            and_(
                ContactApproval.requester_id == current_user["id"],
                ContactApproval.target_id == request.target_user_id
            )
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        return {"status": existing.status, "message": "Request already exists"}
    
    # Create approval request
    approval = ContactApproval(
        requester_id=current_user["id"],
        target_id=request.target_user_id,
        status="pending"
    )
    db.add(approval)
    await db.commit()
    
    return {"status": "pending", "message": "Request submitted for admin review"}

@router.get("/contact/check/{target_user_id}")
async def check_contact_access(
    target_user_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Check if user can view contact details"""
    can_view, reason = await rule_engine.can_view_contact(current_user["id"], target_user_id, db)
    
    features = await rule_engine.get_user_features(current_user["id"], db)
    
    return {
        "can_view": can_view,
        "reason": reason,
        "user_tier": features,
        "requires_upgrade": not can_view and reason == "requires_mutual_interest"
    }

@router.get("/limits")
async def get_user_limits(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's daily limits and remaining quota"""
    
    profile_views_ok, profile_views_left = await rule_engine.check_daily_limit(current_user["id"], "profile_views", db)
    interests_ok, interests_left = await rule_engine.check_daily_limit(current_user["id"], "interests", db)
    
    features = await rule_engine.get_user_features(current_user["id"], db)
    
    return {
        "profile_views": {
            "remaining": profile_views_left,
            "unlimited": profile_views_left == -1
        },
        "interests": {
            "remaining": interests_left,
            "unlimited": interests_left == -1
        },
        "features": features
    }

@router.post("/admin/contact/approve")
async def approve_contact_request(
    update: ContactApprovalUpdate,
    current_user: dict = Depends(require_roles(["admin"])),
    db: AsyncSession = Depends(get_db)
):
    """Admin: Approve or reject contact access request"""
    
    result = await db.execute(
        select(ContactApproval).where(ContactApproval.id == update.approval_id)
    )
    approval = result.scalar_one_or_none()
    
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    approval.status = update.status
    approval.admin_notes = update.admin_notes
    await db.commit()
    
    # Track event and notify user
    if update.status == "approved":
        await EngagementService.track_event(
            approval.requester_id,
            EventType.CONTACT_APPROVED,
            approval.target_id,
            db=db
        )
    
    return {"status": "success", "approval_status": update.status}

@router.get("/admin/contact/pending")
async def get_pending_approvals(
    current_user: dict = Depends(require_roles(["admin"])),
    db: AsyncSession = Depends(get_db)
):
    """Admin: Get pending contact approval requests"""
    
    result = await db.execute(
        select(ContactApproval).where(ContactApproval.status == "pending").limit(100)
    )
    approvals = result.scalars().all()
    
    return {
        "pending_requests": [
            {
                "id": a.id,
                "requester_id": a.requester_id,
                "target_id": a.target_id,
                "created_at": a.created_at.isoformat()
            } for a in approvals
        ]
    }

@router.post("/track/profile-view/{target_user_id}")
async def track_profile_view(
    target_user_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Track profile view and check limits"""
    
    # Check daily limit
    can_view, remaining = await rule_engine.check_daily_limit(current_user["id"], "profile_views", db)
    
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily profile view limit reached. Upgrade to Premium for unlimited views."
        )
    
    # Track event
    await EngagementService.track_event(
        target_user_id,
        EventType.PROFILE_VIEWED,
        current_user["id"],
        db=db
    )
    
    return {"status": "tracked", "remaining_views": remaining}

@router.post("/track/interest/{target_user_id}")
async def track_interest_sent(
    target_user_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Track interest sent and check limits"""
    
    # Check daily limit
    can_send, remaining = await rule_engine.check_daily_limit(current_user["id"], "interests", db)
    
    if not can_send:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily interest limit reached. Upgrade to Premium for more."
        )
    
    # Track event for both users
    await EngagementService.track_event(
        current_user["id"],
        EventType.INTEREST_RECEIVED,
        target_user_id,
        db=db
    )
    
    await EngagementService.track_event(
        target_user_id,
        EventType.INTEREST_RECEIVED,
        current_user["id"],
        db=db
    )
    
    return {"status": "tracked", "remaining_interests": remaining}

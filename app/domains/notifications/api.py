# app/domains/notifications/api.py
from fastapi import APIRouter, Depends, Request
from typing import List
from app.core.security import get_current_user
from app.core.rate_limit import api_rate_limit
from app.domains.identity.models import User
from app.domains.notifications.schemas import NotificationResponse
from app.domains.notifications.service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=List[NotificationResponse])
@api_rate_limit()
async def get_notifications(
    request: Request,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    """Get user notifications"""
    return await NotificationService.get_user_notifications(current_user.id, skip, limit)


@router.post("/mark-read")
@api_rate_limit()
async def mark_notifications_read(
    request: Request,
    notification_ids: List[int],
    current_user: User = Depends(get_current_user)
):
    """Mark notifications as read"""
    await NotificationService.mark_as_read(current_user.id, notification_ids)
    return {"message": "Notifications marked as read"}


@router.get("/unread-count")
@api_rate_limit()
async def get_unread_count(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get unread notification count"""
    count = await NotificationService.get_unread_count(current_user.id)
    return {"unread_count": count}
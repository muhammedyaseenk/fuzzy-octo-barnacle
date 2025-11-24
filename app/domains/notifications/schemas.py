# app/domains/notifications/schemas.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class NotificationType(str, Enum):
    MESSAGE = "message"
    PROFILE_VIEW = "profile_view"
    SHORTLIST = "shortlist"
    INTEREST = "interest"
    VERIFICATION = "verification"
    SYSTEM = "system"


class NotificationCreate(BaseModel):
    user_id: int
    type: NotificationType
    title: str
    message: str
    data: Optional[dict] = None


class NotificationResponse(BaseModel):
    id: int
    type: str
    title: str
    message: str
    data: Optional[dict]
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
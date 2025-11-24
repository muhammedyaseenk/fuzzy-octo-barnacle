# app/domains/moderation/schemas.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class ReportReason(str, Enum):
    INAPPROPRIATE_CONTENT = "inappropriate_content"
    FAKE_PROFILE = "fake_profile"
    HARASSMENT = "harassment"
    SPAM = "spam"
    INAPPROPRIATE_BEHAVIOR = "inappropriate_behavior"
    OTHER = "other"


class ReportStatus(str, Enum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class ReportUserRequest(BaseModel):
    reported_user_id: int
    reason: ReportReason
    details: Optional[str] = None


class BlockUserRequest(BaseModel):
    blocked_user_id: int
    reason: Optional[str] = None


class ReportResponse(BaseModel):
    id: int
    reporter_id: int
    reported_user_id: int
    reason: str
    details: Optional[str]
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class BlockResponse(BaseModel):
    id: int
    blocker_id: int
    blocked_user_id: int
    reason: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AdminReportView(BaseModel):
    id: int
    reporter_name: str
    reported_user_name: str
    reason: str
    details: Optional[str]
    status: str
    created_at: datetime
    reviewed_at: Optional[datetime]
    admin_notes: Optional[str]


class AdminResolveRequest(BaseModel):
    status: ReportStatus
    admin_notes: Optional[str] = None
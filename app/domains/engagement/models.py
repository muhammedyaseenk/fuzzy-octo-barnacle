# app/domains/engagement/models.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.sql import func
from app.core.db import Base
import enum

class EventType(str, enum.Enum):
    NEW_USER_JOINED = "new_user_joined"
    PROFILE_VIEWED = "profile_viewed"
    INTEREST_RECEIVED = "interest_received"
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_REPLY = "message_reply"
    CONTACT_APPROVED = "contact_approved"
    MATCH_SUGGESTION = "match_suggestion"
    PROFILE_INCOMPLETE = "profile_incomplete"
    SUBSCRIPTION_EXPIRING = "subscription_expiring"

class EngagementEvent(Base):
    __tablename__ = "engagement_events"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event_type = Column(SQLEnum(EventType), nullable=False, index=True)
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    metadata = Column(Text)
    processed = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

class ContactApproval(Base):
    __tablename__ = "contact_approvals"
    
    id = Column(Integer, primary_key=True)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    target_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), default="pending", index=True)
    admin_notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class UserEngagementScore(Base):
    __tablename__ = "user_engagement_scores"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    profile_views = Column(Integer, default=0)
    interests_sent = Column(Integer, default=0)
    interests_received = Column(Integer, default=0)
    messages_sent = Column(Integer, default=0)
    messages_received = Column(Integer, default=0)
    response_rate = Column(Integer, default=0)
    last_active = Column(DateTime(timezone=True))
    engagement_score = Column(Integer, default=0, index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

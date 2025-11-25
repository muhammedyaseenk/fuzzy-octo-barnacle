# app/domains/matching/models.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from app.core.db import Base


class UserShortlist(Base):
    __tablename__ = "user_shortlists"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    shortlisted_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Status
    status = Column(String(20), default="active")  # active, removed
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
# app/domains/identity/models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum
from sqlalchemy.sql import func
from app.core.db import Base
import enum


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(15), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    whatsapp = Column(String(15), nullable=True)
    
    hashed_password = Column(String(255), nullable=False)
    
    is_active = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    admin_approved = Column(Boolean, default=False)
    
    role = Column(Enum(UserRole), default=UserRole.USER)
    
    # MFA
    mfa_secret = Column(String(32), nullable=True)
    mfa_enabled = Column(Boolean, default=False)
    
    # Verification
    verification_token = Column(String(255), nullable=True)
    
    # Subscription
    subscription_tier = Column(String(20), default="free")  # free, premium, elite
    subscription_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)  # Can be null for system actions
    action = Column(String(100), nullable=False)  # login, logout, approve, reject, etc.
    details = Column(Text, nullable=True)  # JSON string with additional details
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6
    user_agent = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
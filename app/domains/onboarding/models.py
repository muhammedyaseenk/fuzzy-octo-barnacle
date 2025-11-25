# app/domains/onboarding/models.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Date, ForeignKey
from sqlalchemy.sql import func
from app.core.db import Base


class Profile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    
    # Basic Info
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(String(10), nullable=False)
    
    # Contact
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), default="India")
    
    # Background
    religion = Column(String(50), nullable=True)
    caste = Column(String(100), nullable=True)
    education_level = Column(String(100), nullable=True)
    occupation = Column(String(100), nullable=True)
    
    # Profile
    bio = Column(Text, nullable=True)
    height = Column(Integer, nullable=True)  # in cm
    
    # Status
    verification_status = Column(String(20), default="pending")  # pending, approved, rejected
    profile_complete = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
# app/domains/profiles/schemas.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ProfileSummary(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    age: int
    height: int
    occupation: str
    location: str
    profile_image: Optional[str] = None


class FullProfile(BaseModel):
    # Basic info
    user_id: int
    first_name: str
    last_name: str
    age: int
    gender: str
    marital_status: str
    height: int
    weight: Optional[int]
    complexion: str
    body_type: str
    blood_group: Optional[str]
    
    # Location
    location: str
    native_place: Optional[str]
    
    # Religion
    religion: str
    caste: Optional[str]
    mother_tongue: str
    
    # Lifestyle
    diet: str
    smoking: str
    drinking: str
    
    # Education & Career
    education: str
    occupation: str
    company: Optional[str]
    annual_income: Optional[int]
    
    # Family
    family_type: str
    family_status: str
    
    # Images
    profile_images: List[str] = []
    
    # Status
    is_verified: bool
    last_active: Optional[datetime]


class DashboardData(BaseModel):
    profile_summary: ProfileSummary
    profile_completion: int  # percentage
    recent_views: int
    shortlisted_count: int
    messages_count: int
    suggestions_count: int
    verification_status: str


class ProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    height: Optional[int] = None
    weight: Optional[int] = None
    occupation: Optional[str] = None
    company: Optional[str] = None
    annual_income: Optional[int] = None


class ProfileVisibility(BaseModel):
    show_contact_info: bool = False
    show_income: bool = True
    show_family_details: bool = True
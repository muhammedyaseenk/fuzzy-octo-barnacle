from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
import asyncpg
import bcrypt
import secrets
from datetime import datetime, date
from enum import Enum

# Pydantic Models
class Gender(str, Enum):
    MALE = "Male"
    FEMALE = "Female"

class MaritalStatus(str, Enum):
    NEVER_MARRIED = "Never Married"
    DIVORCED = "Divorced"
    WIDOWED = "Widowed"
    SEPARATED = "Separated"

class UserSignupRequest(BaseModel):
    phone: str
    email: Optional[EmailStr] = None
    whatsapp_number: Optional[str] = None
    first_name: str
    last_name: str
    password: str

    @validator('phone', 'whatsapp_number')
    def validate_phone(cls, v):
        if v and not v.startswith('+'):
            raise ValueError('Phone number must include country code')
        return v

class UserProfileRequest(BaseModel):
    # Basic Details
    display_name: Optional[str] = None
    date_of_birth: date
    gender: Gender
    marital_status: MaritalStatus
    
    # Physical Attributes
    height_cm: int
    weight_kg: Optional[int] = None
    complexion: Optional[str] = None
    body_type: Optional[str] = None
    blood_group: Optional[str] = None
    
    # Location
    country_id: int
    state_id: int
    district_id: Optional[int] = None
    city_id: Optional[int] = None
    current_location: Optional[str] = None
    native_place: Optional[str] = None
    
    # Religion & Community
    religion_id: int
    caste_id: Optional[int] = None
    sub_caste: Optional[str] = None
    mother_tongue_id: int
    
    # Lifestyle
    diet: Optional[str] = None
    smoking: Optional[str] = None
    drinking: Optional[str] = None

class UserEducationRequest(BaseModel):
    degree_level: str
    degree_name: str
    specialization: Optional[str] = None
    university: Optional[str] = None
    graduation_year: Optional[int] = None
    is_highest: bool = False

class UserCareerRequest(BaseModel):
    occupation: str
    company_name: Optional[str] = None
    designation: Optional[str] = None
    annual_income: Optional[int] = None
    employment_type: Optional[str] = None
    is_current: bool = True

class UserFamilyRequest(BaseModel):
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    family_type: Optional[str] = None
    family_status: Optional[str] = None
    total_siblings: int = 0
    family_contact_person: Optional[str] = None
    family_contact_phone: Optional[str] = None

class UserPreferencesRequest(BaseModel):
    preferred_age_min: int
    preferred_age_max: int
    preferred_height_min: Optional[int] = None
    preferred_height_max: Optional[int] = None
    preferred_religions: Optional[List[int]] = None
    preferred_castes: Optional[List[int]] = None
    preferred_income_min: Optional[int] = None
    willing_to_relocate: bool = True
    partner_expectations: Optional[str] = None

class CompleteOnboardingRequest(BaseModel):
    profile: UserProfileRequest
    education: UserEducationRequest
    career: UserCareerRequest
    family: UserFamilyRequest
    preferences: UserPreferencesRequest

# app/domains/onboarding/schemas.py
from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import date
from enum import Enum


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"


class MaritalStatus(str, Enum):
    NEVER_MARRIED = "never_married"
    DIVORCED = "divorced"
    WIDOWED = "widowed"
    SEPARATED = "separated"


class Complexion(str, Enum):
    VERY_FAIR = "very_fair"
    FAIR = "fair"
    WHEATISH = "wheatish"
    DARK = "dark"


class BodyType(str, Enum):
    SLIM = "slim"
    AVERAGE = "average"
    ATHLETIC = "athletic"
    HEAVY = "heavy"


class Diet(str, Enum):
    VEGETARIAN = "vegetarian"
    NON_VEGETARIAN = "non_vegetarian"
    VEGAN = "vegan"


class Smoking(str, Enum):
    NO = "no"
    OCCASIONALLY = "occasionally"
    REGULARLY = "regularly"


class Drinking(str, Enum):
    NO = "no"
    OCCASIONALLY = "occasionally"
    REGULARLY = "regularly"


class EmploymentType(str, Enum):
    PRIVATE = "private"
    GOVERNMENT = "government"
    BUSINESS = "business"
    SELF_EMPLOYED = "self_employed"
    NOT_WORKING = "not_working"


class FamilyType(str, Enum):
    JOINT = "joint"
    NUCLEAR = "nuclear"


class FamilyStatus(str, Enum):
    MIDDLE_CLASS = "middle_class"
    UPPER_MIDDLE_CLASS = "upper_middle_class"
    RICH = "rich"
    AFFLUENT = "affluent"


class VerificationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# Profile schemas
class ProfileBasics(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date
    gender: Gender
    marital_status: MaritalStatus
    height: int  # in cm
    weight: Optional[int] = None  # in kg
    complexion: Complexion
    body_type: BodyType
    blood_group: Optional[str] = None


class LocationInfo(BaseModel):
    country: str
    state: str
    district: str
    city: str
    current_location: Optional[str] = None
    native_place: Optional[str] = None


class ReligionInfo(BaseModel):
    religion: str
    caste: Optional[str] = None
    sub_caste: Optional[str] = None
    mother_tongue: str


class LifestyleInfo(BaseModel):
    diet: Diet
    smoking: Smoking
    drinking: Drinking


class EducationInfo(BaseModel):
    highest_education: str
    institution: Optional[str] = None
    year_of_completion: Optional[int] = None


class CareerInfo(BaseModel):
    occupation: str
    company: Optional[str] = None
    designation: Optional[str] = None
    annual_income: Optional[int] = None  # in currency units
    employment_type: EmploymentType


class FamilyInfo(BaseModel):
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    family_type: FamilyType
    family_status: FamilyStatus
    siblings: Optional[int] = None
    family_contact: Optional[str] = None


class PreferencesInfo(BaseModel):
    min_age: int
    max_age: int
    min_height: int  # in cm
    max_height: int  # in cm
    preferred_religions: List[str]
    preferred_castes: Optional[List[str]] = None
    min_income: Optional[int] = None
    willing_to_relocate: bool = True
    expectations: Optional[str] = None


# Request schemas
class UserSignupRequest(BaseModel):
    phone: str
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    password: str
    first_name: str
    last_name: str


class CompleteOnboardingRequest(BaseModel):
    profile: ProfileBasics
    location: LocationInfo
    religion: ReligionInfo
    lifestyle: LifestyleInfo
    education: EducationInfo
    career: CareerInfo
    family: FamilyInfo
    preferences: PreferencesInfo


# Response schemas
class SignupResponse(BaseModel):
    user_id: int
    message: str
    next_step: str


class VerificationStatusResponse(BaseModel):
    user_id: int
    admin_approved: bool
    verification_status: VerificationStatus
    admin_notes: Optional[str] = None
    submitted_at: Optional[str] = None
    reviewed_at: Optional[str] = None


class PendingVerification(BaseModel):
    user_id: int
    phone: str
    first_name: str
    last_name: str
    submitted_at: str
    profile_complete: bool


class AdminVerifyRequest(BaseModel):
    approved: bool
    notes: Optional[str] = None
# app/domains/identity/schemas.py
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime
from app.domains.identity.models import UserRole


class UserCreate(BaseModel):
    phone: str
    email: Optional[EmailStr] = None
    whatsapp: Optional[str] = None
    password: str
    
    @validator('phone')
    def validate_phone(cls, v):
        # Basic phone validation - should be 10-15 digits
        if not v.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise ValueError('Phone number must contain only digits, +, -, and spaces')
        return v


class UserLogin(BaseModel):
    phone: str
    password: str
    mfa_code: Optional[str] = None


class UserRead(BaseModel):
    id: int
    phone: str
    email: Optional[str]
    whatsapp: Optional[str]
    is_active: bool
    is_verified: bool
    admin_approved: bool
    role: UserRole
    profile_status: str = "pending_profile"
    mfa_enabled: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True


class AuthMeResponse(BaseModel):
    """Response for /auth/me endpoint"""
    id: int
    phone: str
    email: Optional[str]
    profile_status: str
    profile_complete: bool
    admin_approved: bool
    role: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class MFASetupResponse(BaseModel):
    secret: str
    qr_code_url: str
    backup_codes: list[str]


class MFAVerifyRequest(BaseModel):
    secret: str
    code: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class PasswordResetRequest(BaseModel):
    phone: str


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
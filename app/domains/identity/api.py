# app/domains/identity/api.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user, require_roles
from app.core.rate_limit import auth_rate_limit, api_rate_limit
from app.domains.identity.models import User
from app.domains.identity.schemas import (
    UserCreate, UserLogin, UserRead, Token, RefreshTokenRequest,
    MFASetupResponse, MFAVerifyRequest
)
from app.domains.identity.service import IdentityService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserRead)
@auth_rate_limit()
async def register(
    request: Request,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user"""
    user = await IdentityService.create_user(db, user_data)
    return user


@router.post("/login", response_model=Token)
@auth_rate_limit()
async def login(
    request: Request,
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Login user and return JWT tokens"""
    user, token = await IdentityService.authenticate_user(db, login_data)
    return token


@router.post("/refresh", response_model=Token)
@api_rate_limit()
async def refresh_token(
    request: Request,
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token"""
    token = await IdentityService.refresh_tokens(db, refresh_data.refresh_token)
    return token


@router.get("/me", response_model=UserRead)
@api_rate_limit()
async def get_current_user_info(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return current_user


@router.get("/mfa/setup", response_model=MFASetupResponse)
@api_rate_limit()
async def setup_mfa(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Setup MFA for current user"""
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled"
        )
    
    mfa_data = IdentityService.setup_mfa(current_user)
    return MFASetupResponse(**mfa_data)


@router.post("/mfa/enable")
@api_rate_limit()
async def enable_mfa(
    request: Request,
    mfa_data: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Enable MFA after verification"""
    await IdentityService.enable_mfa(db, current_user, mfa_data.secret, mfa_data.code)
    return {"message": "MFA enabled successfully"}


@router.post("/logout")
@api_rate_limit()
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Logout user (for audit logging)"""
    await IdentityService.log_action(
        db, current_user.id, "logout", "User logged out"
    )
    return {"message": "Logged out successfully"}


# Admin endpoints
@router.get("/admin/users", response_model=list[UserRead])
@api_rate_limit()
async def list_users(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db)
):
    """List all users (admin only)"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(User).offset(skip).limit(limit)
    )
    users = result.scalars().all()
    return users


@router.patch("/admin/users/{user_id}/activate")
@api_rate_limit()
async def activate_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db)
):
    """Activate a user account (admin only)"""
    from sqlalchemy import select
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = True
    await db.commit()
    
    await IdentityService.log_action(
        db, current_user.id, "user_activated", 
        f"Admin activated user {user.phone}"
    )
    
    return {"message": "User activated successfully"}
# app/domains/onboarding/api.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List

from app.core.security import get_current_user, require_roles
from app.core.rate_limit import auth_rate_limit, api_rate_limit
from app.domains.identity.models import User
from app.domains.onboarding.schemas import (
    UserSignupRequest, CompleteOnboardingRequest, SignupResponse,
    VerificationStatusResponse, PendingVerification, AdminVerifyRequest
)
from app.domains.onboarding.service import OnboardingService

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


@router.post("/signup", response_model=SignupResponse)
@auth_rate_limit()
async def signup_user(
    request: Request,
    signup_data: UserSignupRequest
):
    """User signup with basic profile creation"""
    result = await OnboardingService.signup_user(signup_data)
    return SignupResponse(**result)


@router.post("/complete-profile/{user_id}")
@api_rate_limit()
async def complete_profile(
    request: Request,
    user_id: int,
    onboarding_data: CompleteOnboardingRequest
):
    """Complete user profile and submit for admin verification"""
    await OnboardingService.complete_onboarding(user_id, onboarding_data)
    return {
        "message": "Profile completed successfully. Submitted for admin verification.",
        "user_id": user_id,
        "status": "pending_verification"
    }


@router.get("/verification-status/{user_id}", response_model=VerificationStatusResponse)
@api_rate_limit()
async def get_verification_status(
    request: Request,
    user_id: int
):
    """Get user verification status"""
    return await OnboardingService.get_verification_status(user_id)


# Admin endpoints
@router.get("/admin/pending-verifications", response_model=List[PendingVerification])
@api_rate_limit()
async def get_pending_verifications(
    request: Request,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(require_roles("admin", "moderator"))
):
    """Get list of pending user verifications (admin/moderator only)"""
    return await OnboardingService.get_pending_verifications(skip, limit)


@router.post("/admin/verify-user/{user_id}")
@api_rate_limit()
async def verify_user(
    request: Request,
    user_id: int,
    verify_data: AdminVerifyRequest,
    current_user: User = Depends(require_roles("admin", "moderator"))
):
    """Approve or reject user verification (admin/moderator only)"""
    await OnboardingService.verify_user(user_id, current_user.id, verify_data)
    
    action = "approved" if verify_data.approved else "rejected"
    return {
        "message": f"User {action} successfully",
        "user_id": user_id,
        "action": action
    }
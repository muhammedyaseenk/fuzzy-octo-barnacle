# app/domains/profiles/api.py
from fastapi import APIRouter, Depends, Request
from typing import List

from app.core.security import get_current_user
from app.core.rate_limit import api_rate_limit
from app.domains.identity.models import User
from app.domains.profiles.schemas import (
    ProfileSummary, FullProfile, DashboardData, ProfileUpdateRequest
)
from app.domains.profiles.service import ProfileService

router = APIRouter(prefix="/profiles", tags=["Profiles"])


@router.get("/me", response_model=FullProfile)
@api_rate_limit()
async def get_my_profile(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get current user's full profile"""
    return await ProfileService.get_full_profile(current_user.id)


@router.get("/me/summary", response_model=ProfileSummary)
@api_rate_limit()
async def get_my_profile_summary(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get current user's profile summary"""
    return await ProfileService.get_profile_summary(current_user.id)


@router.get("/dashboard", response_model=DashboardData)
@api_rate_limit()
async def get_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get user dashboard data"""
    return await ProfileService.get_dashboard_data(current_user.id)


@router.patch("/me")
@api_rate_limit()
async def update_my_profile(
    request: Request,
    update_data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user)
):
    """Update current user's profile"""
    await ProfileService.update_profile(current_user.id, update_data)
    return {"message": "Profile updated successfully"}


@router.get("/{user_id}", response_model=FullProfile)
@api_rate_limit()
async def get_user_profile(
    request: Request,
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get another user's profile (for viewing matches)"""
    # TODO: Add privacy checks and view logging
    return await ProfileService.get_full_profile(user_id)


@router.get("/{user_id}/summary", response_model=ProfileSummary)
@api_rate_limit()
async def get_user_profile_summary(
    request: Request,
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get another user's profile summary"""
    return await ProfileService.get_profile_summary(user_id)
# app/domains/moderation/api.py
from fastapi import APIRouter, Depends, Request
from typing import List

from app.core.security import get_current_user, require_roles
from app.core.rate_limit import api_rate_limit
from app.domains.identity.models import User
from app.domains.moderation.schemas import (
    ReportUserRequest, BlockUserRequest, AdminReportView, AdminResolveRequest
)
from app.domains.moderation.service import ModerationService

router = APIRouter(prefix="/moderation", tags=["Moderation"])


@router.post("/report")
@api_rate_limit()
async def report_user(
    request: Request,
    report_data: ReportUserRequest,
    current_user: User = Depends(get_current_user)
):
    """Report a user for inappropriate behavior"""
    report_id = await ModerationService.report_user(current_user.id, report_data)
    return {
        "message": "User reported successfully",
        "report_id": report_id
    }


@router.post("/block")
@api_rate_limit()
async def block_user(
    request: Request,
    block_data: BlockUserRequest,
    current_user: User = Depends(get_current_user)
):
    """Block a user"""
    block_id = await ModerationService.block_user(current_user.id, block_data)
    return {
        "message": "User blocked successfully",
        "block_id": block_id
    }


@router.delete("/block/{user_id}")
@api_rate_limit()
async def unblock_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """Unblock a user"""
    await ModerationService.unblock_user(current_user.id, user_id)
    return {"message": "User unblocked successfully"}


@router.get("/my-reports")
@api_rate_limit()
async def get_my_reports(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get reports made by current user"""
    reports = await ModerationService.get_my_reports(current_user.id)
    return {"reports": reports}


@router.get("/my-blocks")
@api_rate_limit()
async def get_my_blocks(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get users blocked by current user"""
    blocks = await ModerationService.get_my_blocks(current_user.id)
    return {"blocked_users": blocks}


# Admin endpoints
@router.get("/admin/reports", response_model=List[AdminReportView])
@api_rate_limit()
async def get_pending_reports(
    request: Request,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(require_roles("admin", "moderator"))
):
    """Get pending reports for admin review"""
    return await ModerationService.get_pending_reports(skip, limit)


@router.post("/admin/reports/{report_id}/resolve")
@api_rate_limit()
async def resolve_report(
    request: Request,
    report_id: int,
    resolve_data: AdminResolveRequest,
    current_user: User = Depends(require_roles("admin", "moderator"))
):
    """Resolve a report (admin/moderator only)"""
    await ModerationService.resolve_report(report_id, current_user.id, resolve_data)
    return {
        "message": "Report resolved successfully",
        "report_id": report_id,
        "status": resolve_data.status.value
    }
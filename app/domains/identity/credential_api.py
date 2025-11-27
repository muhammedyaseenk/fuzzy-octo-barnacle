# app/domains/identity/credential_api.py
"""
Admin endpoints for credential management and export.
Allows admins to export user credentials as JSON for manual sharing via WhatsApp.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user, require_roles
from app.core.rate_limit import api_rate_limit
from app.domains.identity.models import User
from app.domains.identity.credential_service import CredentialService
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/admin/credentials", tags=["Admin Credentials"])


class CredentialExportRequest(BaseModel):
    """Request body for credential export"""
    user_id: int
    original_password: str
    delivery_method: str = "whatsapp"  # whatsapp, email, manual
    delivery_note: Optional[str] = None


class CredentialExportResponse(BaseModel):
    """Response for credential export"""
    success: bool
    download_token: str
    credentials: dict
    export_file_name: str
    expires_in_hours: int


class CredentialDeliveryMarkRequest(BaseModel):
    """Mark credentials as delivered to user"""
    export_id: int
    delivery_note: Optional[str] = None


@router.post("/export", response_model=CredentialExportResponse)
@api_rate_limit()
async def export_user_credentials(
    request: Request,
    export_request: CredentialExportRequest,
    current_admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Export user credentials for admin to send via WhatsApp.
    
    Admin flow:
    1. After approving user profile, admin calls this endpoint with user_id and original_password
    2. Backend generates encrypted credentials file
    3. Admin downloads the file and manually sends it via WhatsApp to user
    4. Admin marks credentials as delivered via /mark-delivered endpoint
    
    Security notes:
    - Only admins can export credentials
    - Credentials are encrypted in transit
    - Export is logged with admin IP and user agent
    - File expires after 24 hours
    - Download limit: 3 times max
    """
    # Verify admin role
    if current_admin.role.value not in ['admin', 'moderator']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can export credentials"
        )

    # Verify user exists
    result = await db.execute(
        db.select(User).where(User.id == export_request.user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {export_request.user_id} not found"
        )

    try:
        # Export credentials
        export_result = await CredentialService.export_credentials_for_admin(
            db=db,
            user_id=export_request.user_id,
            admin_id=current_admin.id,
            original_password=export_request.original_password,
            delivery_method=export_request.delivery_method,
            admin_ip_address=request.client.host if request.client else None,
            admin_user_agent=request.headers.get("user-agent"),
        )

        return CredentialExportResponse(**export_result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export credentials: {str(e)}"
        )


@router.post("/mark-delivered")
@api_rate_limit()
async def mark_credentials_delivered(
    request: Request,
    delivery_request: CredentialDeliveryMarkRequest,
    current_admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark credentials as delivered to user via WhatsApp."""
    # Verify admin role
    if current_admin.role.value not in ['admin', 'moderator']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can mark deliveries"
        )

    try:
        result = await CredentialService.mark_credentials_delivered(
            db=db,
            export_id=delivery_request.export_id,
            delivery_note=delivery_request.delivery_note,
        )
        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark delivery: {str(e)}"
        )


@router.get("/export/{user_id}/history")
@api_rate_limit()
async def get_credential_export_history(
    user_id: int,
    current_admin: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get credential export history for a user (admin view)."""
    # Verify admin role
    if current_admin.role.value not in ['admin', 'moderator']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view export history"
        )

    try:
        history = await CredentialService.get_export_history(db, user_id)
        return {
            "success": True,
            "user_id": user_id,
            "export_history": history,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve history: {str(e)}"
        )


@router.get("/download/{download_token}")
@api_rate_limit()
async def download_exported_credentials(
    download_token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Download exported credentials using a one-time token.
    Admin can share this token link via WhatsApp to user.
    Token expires after 24 hours or 3 downloads.
    """
    try:
        credentials = await CredentialService.generate_credentials_json_file(
            db, download_token
        )

        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid or expired download token"
            )

        return credentials

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download credentials: {str(e)}"
        )

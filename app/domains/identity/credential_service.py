# app/domains/identity/credential_service.py
"""
Service for credential export and management.
Handles secure credential export for admin to share via WhatsApp.
"""
import json
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from cryptography.fernet import Fernet
import os

from app.domains.identity.models import User
from app.domains.identity.credential_models import CredentialAudit, CredentialExport


class CredentialService:
    """
    Service for managing user credentials.
    - Export credentials for admin to send via WhatsApp
    - Track credential exports in audit log
    - Generate temporary download tokens
    """

    # Encryption key for credential storage (should be in environment)
    # In production, use AWS KMS or similar
    _cipher_key = os.environ.get('CREDENTIAL_CIPHER_KEY', Fernet.generate_key())
    _cipher = Fernet(_cipher_key)

    @staticmethod
    def _encrypt_credential(value: str) -> str:
        """Encrypt a credential value."""
        return CredentialService._cipher.encrypt(value.encode()).decode()

    @staticmethod
    def _decrypt_credential(encrypted_value: str) -> str:
        """Decrypt a credential value."""
        try:
            return CredentialService._cipher.decrypt(encrypted_value.encode()).decode()
        except Exception:
            return ""

    @staticmethod
    async def export_credentials_for_admin(
        db: AsyncSession,
        user_id: int,
        admin_id: int,
        original_password: str,
        delivery_method: str = "whatsapp",
        admin_ip_address: Optional[str] = None,
        admin_user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Export user credentials for admin to share via WhatsApp."""
        # Get user
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Create audit log entry
        audit = CredentialAudit(
            user_id=user_id,
            admin_id=admin_id,
            delivery_method=delivery_method,
            admin_ip_address=admin_ip_address,
            admin_user_agent=admin_user_agent,
        )
        db.add(audit)
        await db.flush()  # Get the audit ID

        # Encrypt credentials
        encrypted_phone = CredentialService._encrypt_credential(user.phone)
        encrypted_password = CredentialService._encrypt_credential(original_password)

        # Create export record
        download_token = secrets.token_urlsafe(32)
        export = CredentialExport(
            audit_id=audit.id,
            encrypted_phone=encrypted_phone,
            encrypted_password=encrypted_password,
            export_format="json",
            download_token=download_token,
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        db.add(export)
        await db.commit()

        # Prepare JSON export
        credentials_json = {
            "app_name": "Aurum - Matrimony Platform",
            "user_info": {
                "id": user.id,
                "name": user.phone,  # Or full name if available
                "phone": user.phone,
            },
            "login_credentials": {
                "phone": user.phone,
                "password": original_password,
            },
            "instructions": {
                "how_to_use": "Share these credentials with the user via WhatsApp or secure method",
                "security_notice": "Treat this as sensitive information. Delete after delivery.",
                "storage": "User should save credentials in their device for future login",
            },
            "export_details": {
                "exported_at": audit.created_at.isoformat(),
                "exported_by": f"Admin #{admin_id}",
                "delivery_method": delivery_method,
                "token": download_token,
            }
        }

        return {
            "success": True,
            "download_token": download_token,
            "credentials": credentials_json,
            "export_file_name": f"aurum_credentials_{user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "expires_in_hours": 24,
        }

    @staticmethod
    async def mark_credentials_delivered(
        db: AsyncSession,
        export_id: int,
        delivery_note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mark credentials as delivered to user."""
        result = await db.execute(
            select(CredentialAudit).where(CredentialAudit.id == export_id)
        )
        audit = result.scalar_one_or_none()

        if not audit:
            raise ValueError(f"Credential export {export_id} not found")

        audit.marked_delivered = True
        audit.delivery_timestamp = datetime.utcnow()
        audit.delivery_note = delivery_note

        await db.commit()

        return {
            "success": True,
            "message": f"Credentials for user {audit.user_id} marked as delivered",
            "delivered_at": audit.delivery_timestamp.isoformat(),
        }

    @staticmethod
    async def get_export_history(
        db: AsyncSession,
        user_id: int,
    ) -> list:
        """Get credential export history for a user."""
        result = await db.execute(
            select(CredentialAudit)
            .where(CredentialAudit.user_id == user_id)
            .order_by(CredentialAudit.created_at.desc())
        )
        exports = result.scalars().all()

        return [
            {
                "id": export.id,
                "exported_at": export.created_at.isoformat(),
                "admin_id": export.admin_id,
                "delivery_method": export.delivery_method,
                "marked_delivered": export.marked_delivered,
                "delivery_timestamp": export.delivery_timestamp.isoformat() if export.delivery_timestamp else None,
                "delivery_note": export.delivery_note,
            }
            for export in exports
        ]

    @staticmethod
    async def generate_credentials_json_file(
        db: AsyncSession,
        download_token: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate the JSON file content for credential download.
        Validates token and returns encrypted credentials.
        """
        result = await db.execute(
            select(CredentialExport)
            .where(CredentialExport.download_token == download_token)
        )
        export = result.scalar_one_or_none()

        if not export:
            raise ValueError("Invalid or expired download token")

        # Check expiration
        if datetime.utcnow() > export.expires_at:
            raise ValueError("Credentials link has expired (24 hours)")

        # Check if already downloaded too many times
        if export.download_count >= 3:
            raise ValueError("Download limit exceeded for this export")

        # Get audit and user info
        audit = export.audit
        result = await db.execute(select(User).where(User.id == audit.user_id))
        user = result.scalar_one_or_none()

        # Decrypt credentials
        phone = CredentialService._decrypt_credential(export.encrypted_phone)
        password = CredentialService._decrypt_credential(export.encrypted_password)

        # Increment download count
        export.download_count += 1
        export.downloaded = True
        await db.commit()

        return {
            "app_name": "Aurum - Matrimony Platform",
            "user_id": user.id,
            "phone": phone,
            "password": password,
            "exported_at": audit.created_at.isoformat(),
            "delivery_method": audit.delivery_method,
            "security_notice": "These credentials should be kept confidential. Do not share with unauthorized persons.",
        }

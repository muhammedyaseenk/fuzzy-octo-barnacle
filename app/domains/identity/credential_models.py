# app/domains/identity/credential_models.py
"""
Credential management models for admin credential export and tracking.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, Integer, Boolean, ForeignKey, func, Index
from sqlalchemy.orm import relationship
from app.core.db import Base


class CredentialAudit(Base):
    """
    Track credential exports and access for security audit.
    Admin can export credentials as JSON to send via WhatsApp.
    """
    __tablename__ = "credential_audit"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    admin_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Export details
    export_timestamp = Column(DateTime, server_default=func.now(), nullable=False)
    delivery_method = Column(String(50), default="whatsapp", nullable=False)  # whatsapp, email, manual
    export_file_hash = Column(String(256), nullable=True)  # SHA256 hash of exported credentials
    
    # Delivery tracking
    marked_delivered = Column(Boolean, default=False)
    delivery_timestamp = Column(DateTime, nullable=True)
    delivery_note = Column(String(500), nullable=True)
    
    # IP tracking for security
    admin_ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    admin_user_agent = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="credential_exports")
    admin = relationship("User", foreign_keys=[admin_id], backref="credential_exports_created")

    __table_args__ = (
        Index("idx_credential_audit_user_timestamp", user_id, export_timestamp),
        Index("idx_credential_audit_admin_timestamp", admin_id, export_timestamp),
    )


class CredentialExport(Base):
    """
    Store exported credentials (encrypted) temporarily for admin download.
    Automatically deleted after 24 hours.
    """
    __tablename__ = "credential_exports"

    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(Integer, ForeignKey("credential_audit.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Encrypted credentials (phone + password)
    encrypted_phone = Column(String(255), nullable=False)
    encrypted_password = Column(String(255), nullable=False)
    
    # Export format
    export_format = Column(String(20), default="json", nullable=False)  # json, csv, txt
    
    # Access control
    download_token = Column(String(256), unique=True, nullable=True)  # One-time download token
    downloaded = Column(Boolean, default=False)
    download_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=False)  # 24 hours from creation
    
    # Relationships
    audit = relationship("CredentialAudit", backref="credential_export")

    __table_args__ = (
        Index("idx_credential_export_audit", audit_id),
        Index("idx_credential_export_token", download_token),
    )

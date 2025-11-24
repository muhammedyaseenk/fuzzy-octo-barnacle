# app/domains/identity/service.py
import pyotp
import qrcode
import uuid
from io import BytesIO
from base64 import b64encode
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token
from app.core.config import settings
from app.domains.identity.models import User, AuditLog, UserRole
from app.domains.identity.schemas import UserCreate, UserLogin, Token


class IdentityService:
    
    @staticmethod
    async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
        """Create a new user"""
        # Check if phone already exists
        result = await db.execute(select(User).where(User.phone == user_data.phone))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )
        
        # Check if email already exists (if provided)
        if user_data.email:
            result = await db.execute(select(User).where(User.email == user_data.email))
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
        
        # Create user
        hashed_password = get_password_hash(user_data.password)
        verification_token = str(uuid.uuid4())
        
        user = User(
            phone=user_data.phone,
            email=user_data.email,
            whatsapp=user_data.whatsapp,
            hashed_password=hashed_password,
            verification_token=verification_token,
            role=UserRole.USER
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Log user creation
        await IdentityService.log_action(
            db, user.id, "user_created", f"User created with phone: {user.phone}"
        )
        
        return user
    
    @staticmethod
    async def authenticate_user(db: AsyncSession, login_data: UserLogin) -> Tuple[User, Token]:
        """Authenticate user and return tokens"""
        # Get user by phone
        result = await db.execute(select(User).where(User.phone == login_data.phone))
        user = result.scalar_one_or_none()
        
        if not user or not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid phone or password"
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is not active"
            )
        
        # Check MFA if enabled
        if user.mfa_enabled:
            if not login_data.mfa_code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="MFA code required"
                )
            
            if not IdentityService.verify_mfa_code(user.mfa_secret, login_data.mfa_code):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid MFA code"
                )
        
        # Create tokens
        token_data = {"sub": str(user.id), "role": user.role.value}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        # Update last login
        user.last_login = datetime.utcnow()
        await db.commit()
        
        # Log login
        await IdentityService.log_action(db, user.id, "login", "User logged in")
        
        token = Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
        return user, token
    
    @staticmethod
    async def refresh_tokens(db: AsyncSession, refresh_token: str) -> Token:
        """Refresh access and refresh tokens"""
        from app.core.security import verify_token
        
        payload = verify_token(refresh_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Get user
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new tokens
        token_data = {"sub": str(user.id), "role": user.role.value}
        access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token(token_data)
        
        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    @staticmethod
    def setup_mfa(user: User) -> dict:
        """Setup MFA for user and return QR code"""
        secret = pyotp.random_base32()
        
        # Create TOTP URI
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.phone,
            issuer_name="Aurum Matrimony"
        )
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_code_data = b64encode(buffer.getvalue()).decode()
        
        return {
            "secret": secret,
            "qr_code_url": f"data:image/png;base64,{qr_code_data}",
            "backup_codes": []  # TODO: Generate backup codes
        }
    
    @staticmethod
    def verify_mfa_code(secret: str, code: str) -> bool:
        """Verify MFA TOTP code"""
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)
    
    @staticmethod
    async def enable_mfa(db: AsyncSession, user: User, secret: str, code: str):
        """Enable MFA for user after verification"""
        if not IdentityService.verify_mfa_code(secret, code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid MFA code"
            )
        
        user.mfa_secret = secret
        user.mfa_enabled = True
        await db.commit()
        
        await IdentityService.log_action(db, user.id, "mfa_enabled", "MFA enabled for user")
    
    @staticmethod
    async def log_action(db: AsyncSession, user_id: Optional[int], action: str, details: str, ip_address: str = None, user_agent: str = None):
        """Log user action for audit trail"""
        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.add(log_entry)
        await db.commit()
# app/domains/onboarding/service.py
import asyncpg
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status

from app.core.db import get_pg_connection
from app.core.security import get_password_hash
from app.domains.onboarding.schemas import (
    UserSignupRequest, CompleteOnboardingRequest, VerificationStatus,
    AdminVerifyRequest, PendingVerification, VerificationStatusResponse
)


class OnboardingService:
    
    @staticmethod
    async def signup_user(signup_data: UserSignupRequest) -> Dict[str, Any]:
        """Create user and initial profile using asyncpg"""
        async with get_pg_connection() as conn:
            async with conn.transaction():
                # Check if phone exists
                existing_user = await conn.fetchrow(
                    "SELECT id FROM users WHERE phone = $1", signup_data.phone
                )
                if existing_user:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Phone number already registered"
                    )
                
                # Check if email exists (if provided)
                if signup_data.email:
                    existing_email = await conn.fetchrow(
                        "SELECT id FROM users WHERE email = $1", signup_data.email
                    )
                    if existing_email:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Email already registered"
                        )
                
                # Create user
                hashed_password = get_password_hash(signup_data.password)
                user_id = await conn.fetchval("""
                    INSERT INTO users (phone, email, whatsapp, hashed_password, role, is_active, admin_approved)
                    VALUES ($1, $2, $3, $4, 'user', false, false)
                    RETURNING id
                """, signup_data.phone, signup_data.email, signup_data.whatsapp, hashed_password)
                
                # Create initial profile
                await conn.execute("""
                    INSERT INTO user_profiles (user_id, first_name, last_name)
                    VALUES ($1, $2, $3)
                """, user_id, signup_data.first_name, signup_data.last_name)
                
                return {
                    "user_id": user_id,
                    "message": "User created successfully. Please complete your profile.",
                    "next_step": f"/api/v1/onboarding/complete-profile/{user_id}"
                }
    
    @staticmethod
    async def complete_onboarding(user_id: int, onboarding_data: CompleteOnboardingRequest):
        """Complete user onboarding with all profile data"""
        async with get_pg_connection() as conn:
            async with conn.transaction():
                # Check if user exists
                user = await conn.fetchrow("SELECT id FROM users WHERE id = $1", user_id)
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="User not found"
                    )
                
                # Update user_profiles
                await conn.execute("""
                    UPDATE user_profiles SET
                        first_name = $2, last_name = $3, date_of_birth = $4,
                        gender = $5, marital_status = $6, height = $7, weight = $8,
                        complexion = $9, body_type = $10, blood_group = $11,
                        country = $12, state = $13, district = $14, city = $15,
                        current_location = $16, native_place = $17,
                        religion = $18, caste = $19, sub_caste = $20, mother_tongue = $21,
                        diet = $22, smoking = $23, drinking = $24,
                        updated_at = NOW()
                    WHERE user_id = $1
                """, 
                    user_id, onboarding_data.profile.first_name, onboarding_data.profile.last_name,
                    onboarding_data.profile.date_of_birth, onboarding_data.profile.gender.value,
                    onboarding_data.profile.marital_status.value, onboarding_data.profile.height,
                    onboarding_data.profile.weight, onboarding_data.profile.complexion.value,
                    onboarding_data.profile.body_type.value, onboarding_data.profile.blood_group,
                    onboarding_data.location.country, onboarding_data.location.state,
                    onboarding_data.location.district, onboarding_data.location.city,
                    onboarding_data.location.current_location, onboarding_data.location.native_place,
                    onboarding_data.religion.religion, onboarding_data.religion.caste,
                    onboarding_data.religion.sub_caste, onboarding_data.religion.mother_tongue,
                    onboarding_data.lifestyle.diet.value, onboarding_data.lifestyle.smoking.value,
                    onboarding_data.lifestyle.drinking.value
                )
                
                # Insert education
                await conn.execute("""
                    INSERT INTO user_education (user_id, highest_education, institution, year_of_completion)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id) DO UPDATE SET
                        highest_education = EXCLUDED.highest_education,
                        institution = EXCLUDED.institution,
                        year_of_completion = EXCLUDED.year_of_completion
                """, 
                    user_id, onboarding_data.education.highest_education,
                    onboarding_data.education.institution, onboarding_data.education.year_of_completion
                )
                
                # Insert career
                await conn.execute("""
                    INSERT INTO user_career (user_id, occupation, company, designation, annual_income, employment_type)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (user_id) DO UPDATE SET
                        occupation = EXCLUDED.occupation,
                        company = EXCLUDED.company,
                        designation = EXCLUDED.designation,
                        annual_income = EXCLUDED.annual_income,
                        employment_type = EXCLUDED.employment_type
                """, 
                    user_id, onboarding_data.career.occupation, onboarding_data.career.company,
                    onboarding_data.career.designation, onboarding_data.career.annual_income,
                    onboarding_data.career.employment_type.value
                )
                
                # Insert family
                await conn.execute("""
                    INSERT INTO user_family (user_id, father_name, mother_name, family_type, family_status, siblings, family_contact)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (user_id) DO UPDATE SET
                        father_name = EXCLUDED.father_name,
                        mother_name = EXCLUDED.mother_name,
                        family_type = EXCLUDED.family_type,
                        family_status = EXCLUDED.family_status,
                        siblings = EXCLUDED.siblings,
                        family_contact = EXCLUDED.family_contact
                """, 
                    user_id, onboarding_data.family.father_name, onboarding_data.family.mother_name,
                    onboarding_data.family.family_type.value, onboarding_data.family.family_status.value,
                    onboarding_data.family.siblings, onboarding_data.family.family_contact
                )
                
                # Insert preferences
                await conn.execute("""
                    INSERT INTO user_preferences (user_id, min_age, max_age, min_height, max_height, 
                                                preferred_religions, preferred_castes, min_income, 
                                                willing_to_relocate, expectations)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (user_id) DO UPDATE SET
                        min_age = EXCLUDED.min_age,
                        max_age = EXCLUDED.max_age,
                        min_height = EXCLUDED.min_height,
                        max_height = EXCLUDED.max_height,
                        preferred_religions = EXCLUDED.preferred_religions,
                        preferred_castes = EXCLUDED.preferred_castes,
                        min_income = EXCLUDED.min_income,
                        willing_to_relocate = EXCLUDED.willing_to_relocate,
                        expectations = EXCLUDED.expectations
                """, 
                    user_id, onboarding_data.preferences.min_age, onboarding_data.preferences.max_age,
                    onboarding_data.preferences.min_height, onboarding_data.preferences.max_height,
                    onboarding_data.preferences.preferred_religions, onboarding_data.preferences.preferred_castes,
                    onboarding_data.preferences.min_income, onboarding_data.preferences.willing_to_relocate,
                    onboarding_data.preferences.expectations
                )
                
                # Add to admin verification queue
                await conn.execute("""
                    INSERT INTO admin_verification_queue (user_id, status, submitted_at)
                    VALUES ($1, 'pending', NOW())
                    ON CONFLICT (user_id) DO UPDATE SET
                        status = 'pending',
                        submitted_at = NOW()
                """, user_id)
    
    @staticmethod
    async def get_verification_status(user_id: int) -> VerificationStatusResponse:
        """Get user verification status"""
        async with get_pg_connection() as conn:
            result = await conn.fetchrow("""
                SELECT u.admin_approved, q.status, q.admin_notes, q.submitted_at, q.reviewed_at
                FROM users u
                LEFT JOIN admin_verification_queue q ON u.id = q.user_id
                WHERE u.id = $1
            """, user_id)
            
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            return VerificationStatusResponse(
                user_id=user_id,
                admin_approved=result['admin_approved'],
                verification_status=result['status'] or VerificationStatus.PENDING,
                admin_notes=result['admin_notes'],
                submitted_at=result['submitted_at'].isoformat() if result['submitted_at'] else None,
                reviewed_at=result['reviewed_at'].isoformat() if result['reviewed_at'] else None
            )
    
    @staticmethod
    async def get_pending_verifications(skip: int = 0, limit: int = 50) -> List[PendingVerification]:
        """Get pending verifications for admin"""
        async with get_pg_connection() as conn:
            results = await conn.fetch("""
                SELECT q.user_id, u.phone, p.first_name, p.last_name, q.submitted_at,
                       CASE WHEN p.date_of_birth IS NOT NULL THEN true ELSE false END as profile_complete
                FROM admin_verification_queue q
                JOIN users u ON q.user_id = u.id
                JOIN user_profiles p ON u.id = p.user_id
                WHERE q.status = 'pending'
                ORDER BY q.submitted_at ASC
                OFFSET $1 LIMIT $2
            """, skip, limit)
            
            return [
                PendingVerification(
                    user_id=row['user_id'],
                    phone=row['phone'],
                    first_name=row['first_name'],
                    last_name=row['last_name'],
                    submitted_at=row['submitted_at'].isoformat(),
                    profile_complete=row['profile_complete']
                )
                for row in results
            ]
    
    @staticmethod
    async def verify_user(user_id: int, admin_id: int, verify_data: AdminVerifyRequest):
        """Admin verify/reject user"""
        async with get_pg_connection() as conn:
            async with conn.transaction():
                # Check if user exists
                user = await conn.fetchrow("SELECT id FROM users WHERE id = $1", user_id)
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="User not found"
                    )
                
                # Update user approval status
                await conn.execute("""
                    UPDATE users SET admin_approved = $2, is_active = $2
                    WHERE id = $1
                """, user_id, verify_data.approved)
                
                # Update verification queue
                status_value = "approved" if verify_data.approved else "rejected"
                await conn.execute("""
                    UPDATE admin_verification_queue SET
                        status = $2, admin_notes = $3, reviewed_at = NOW(), reviewed_by = $4
                    WHERE user_id = $1
                """, user_id, status_value, verify_data.notes, admin_id)
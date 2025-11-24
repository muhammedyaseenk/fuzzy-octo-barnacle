
from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
import asyncpg
import bcrypt
import secrets
from fastapi import HTTPException
from app.services.user_profile_creation.user_onboarding_schema import (
    UserSignupRequest, CompleteOnboardingRequest,
)
# User Onboarding Service
class UserOnboardingService:
    
    @staticmethod
    async def signup_user(signup_data: UserSignupRequest, db: asyncpg.Connection):
        """Initial user signup - creates user account"""
        
        # Check if phone already exists
        existing = await db.fetchrow("SELECT user_id FROM users WHERE phone = $1", signup_data.phone)
        if existing:
            raise HTTPException(status_code=400, detail="Phone number already registered")
        
        # Hash password
        password_hash = bcrypt.hashpw(signup_data.password.encode(), bcrypt.gensalt()).decode()
        
        # Create user
        user_id = await db.fetchval("""
            INSERT INTO users (email, phone, whatsapp_number, password_hash, verification_token)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING user_id
        """, signup_data.email, signup_data.phone, signup_data.whatsapp_number, 
            password_hash, secrets.token_urlsafe(32))
        
        # Create basic profile entry
        await db.execute("""
            INSERT INTO user_profiles (user_id, first_name, last_name)
            VALUES ($1, $2, $3)
        """, user_id, signup_data.first_name, signup_data.last_name)
        
        return {"user_id": user_id, "message": "Account created. Complete your profile to proceed."}
    
    @staticmethod
    async def complete_profile(user_id: int, onboarding_data: CompleteOnboardingRequest, db: asyncpg.Connection):
        """Complete user profile and submit for admin verification"""
        
        async with db.transaction():
            # Update user profile
            await db.execute("""
                UPDATE user_profiles SET
                    display_name = $2, date_of_birth = $3, gender = $4, marital_status = $5,
                    height_cm = $6, weight_kg = $7, complexion = $8, body_type = $9, blood_group = $10,
                    country_id = $11, state_id = $12, district_id = $13, city_id = $14,
                    current_location = $15, native_place = $16, religion_id = $17, caste_id = $18,
                    sub_caste = $19, mother_tongue_id = $20, diet = $21, smoking = $22, drinking = $23,
                    profile_completion_percentage = 85, updated_at = NOW()
                WHERE user_id = $1
            """, user_id, onboarding_data.profile.display_name, onboarding_data.profile.date_of_birth,
                onboarding_data.profile.gender, onboarding_data.profile.marital_status,
                onboarding_data.profile.height_cm, onboarding_data.profile.weight_kg,
                onboarding_data.profile.complexion, onboarding_data.profile.body_type,
                onboarding_data.profile.blood_group, onboarding_data.profile.country_id,
                onboarding_data.profile.state_id, onboarding_data.profile.district_id,
                onboarding_data.profile.city_id, onboarding_data.profile.current_location,
                onboarding_data.profile.native_place, onboarding_data.profile.religion_id,
                onboarding_data.profile.caste_id, onboarding_data.profile.sub_caste,
                onboarding_data.profile.mother_tongue_id, onboarding_data.profile.diet,
                onboarding_data.profile.smoking, onboarding_data.profile.drinking)
            
            # Insert education
            await db.execute("""
                INSERT INTO user_education (user_id, degree_level, degree_name, specialization, university, graduation_year, is_highest)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, user_id, onboarding_data.education.degree_level, onboarding_data.education.degree_name,
                onboarding_data.education.specialization, onboarding_data.education.university,
                onboarding_data.education.graduation_year, onboarding_data.education.is_highest)
            
            # Insert career
            await db.execute("""
                INSERT INTO user_career (user_id, occupation, company_name, designation, annual_income, employment_type, is_current)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, user_id, onboarding_data.career.occupation, onboarding_data.career.company_name,
                onboarding_data.career.designation, onboarding_data.career.annual_income,
                onboarding_data.career.employment_type, onboarding_data.career.is_current)
            
            # Insert family
            await db.execute("""
                INSERT INTO user_family (user_id, father_name, mother_name, family_type, family_status, total_siblings, family_contact_person, family_contact_phone)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, user_id, onboarding_data.family.father_name, onboarding_data.family.mother_name,
                onboarding_data.family.family_type, onboarding_data.family.family_status,
                onboarding_data.family.total_siblings, onboarding_data.family.family_contact_person,
                onboarding_data.family.family_contact_phone)
            
            # Insert preferences
            await db.execute("""
                INSERT INTO user_preferences (user_id, preferred_age_min, preferred_age_max, preferred_height_min, preferred_height_max, preferred_religions, preferred_castes, preferred_income_min, willing_to_relocate, partner_expectations)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """, user_id, onboarding_data.preferences.preferred_age_min, onboarding_data.preferences.preferred_age_max,
                onboarding_data.preferences.preferred_height_min, onboarding_data.preferences.preferred_height_max,
                onboarding_data.preferences.preferred_religions, onboarding_data.preferences.preferred_castes,
                onboarding_data.preferences.preferred_income_min, onboarding_data.preferences.willing_to_relocate,
                onboarding_data.preferences.partner_expectations)
            
            # Submit for admin verification
            await db.execute("""
                INSERT INTO admin_verification_queue (user_id, status)
                VALUES ($1, 'Pending')
            """, user_id)
        
        return {"message": "Profile completed. Submitted for admin verification."}
    
    @staticmethod
    async def get_verification_status(user_id: int, db: asyncpg.Connection):
        """Check user verification status"""
        
        status = await db.fetchrow("""
            SELECT u.admin_approved, avq.status, avq.admin_notes, avq.submitted_at, avq.reviewed_at
            FROM users u
            LEFT JOIN admin_verification_queue avq ON u.user_id = avq.user_id
            WHERE u.user_id = $1
        """, user_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "admin_approved": status['admin_approved'],
            "verification_status": status['status'],
            "admin_notes": status['admin_notes'],
            "submitted_at": status['submitted_at'],
            "reviewed_at": status['reviewed_at']
        }

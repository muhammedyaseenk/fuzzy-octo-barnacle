# app/domains/profiles/service.py
from datetime import datetime, date
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.core.cache import cache_get, cache_set, get_user_profile_cache_key
from app.core.db import get_pg_connection
from app.domains.profiles.schemas import (
    ProfileSummary, FullProfile, DashboardData, ProfileUpdateRequest
)


class ProfileService:
    
    @staticmethod
    def calculate_age(birth_date: date) -> int:
        """Calculate age from birth date"""
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
    @staticmethod
    async def get_profile_summary(user_id: int) -> ProfileSummary:
        """Get profile summary for cards/lists"""
        cache_key = get_user_profile_cache_key(user_id)
        cached = await cache_get(cache_key)
        
        if cached:
            return ProfileSummary(**cached)
        
        async with get_pg_connection() as conn:
            result = await conn.fetchrow("""
                SELECT p.user_id, p.first_name, p.last_name, p.date_of_birth, p.height,
                       c.occupation, CONCAT(p.city, ', ', p.state) as location
                FROM user_profiles p
                LEFT JOIN user_career c ON p.user_id = c.user_id
                WHERE p.user_id = $1
            """, user_id)
            
            if not result:
                raise HTTPException(status_code=404, detail="Profile not found")
            
            age = ProfileService.calculate_age(result['date_of_birth']) if result['date_of_birth'] else 0
            
            profile = ProfileSummary(
                user_id=result['user_id'],
                first_name=result['first_name'],
                last_name=result['last_name'],
                age=age,
                height=result['height'] or 0,
                occupation=result['occupation'] or "Not specified",
                location=result['location'] or "Not specified"
            )
            
            # Cache for 1 hour
            await cache_set(cache_key, profile.dict(), 3600)
            return profile
    
    @staticmethod
    async def get_full_profile(user_id: int) -> FullProfile:
        """Get complete profile details"""
        async with get_pg_connection() as conn:
            result = await conn.fetchrow("""
                SELECT p.*, e.highest_education, c.occupation, c.company, c.annual_income,
                       f.family_type, f.family_status, u.is_verified, u.last_login
                FROM user_profiles p
                LEFT JOIN user_education e ON p.user_id = e.user_id
                LEFT JOIN user_career c ON p.user_id = c.user_id
                LEFT JOIN user_family f ON p.user_id = f.user_id
                LEFT JOIN users u ON p.user_id = u.id
                WHERE p.user_id = $1
            """, user_id)
            
            if not result:
                raise HTTPException(status_code=404, detail="Profile not found")
            
            age = ProfileService.calculate_age(result['date_of_birth']) if result['date_of_birth'] else 0
            location = f"{result['city']}, {result['state']}" if result['city'] and result['state'] else "Not specified"
            
            return FullProfile(
                user_id=result['user_id'],
                first_name=result['first_name'] or "",
                last_name=result['last_name'] or "",
                age=age,
                gender=result['gender'] or "",
                marital_status=result['marital_status'] or "",
                height=result['height'] or 0,
                weight=result['weight'],
                complexion=result['complexion'] or "",
                body_type=result['body_type'] or "",
                blood_group=result['blood_group'],
                location=location,
                native_place=result['native_place'],
                religion=result['religion'] or "",
                caste=result['caste'],
                mother_tongue=result['mother_tongue'] or "",
                diet=result['diet'] or "",
                smoking=result['smoking'] or "",
                drinking=result['drinking'] or "",
                education=result['highest_education'] or "",
                occupation=result['occupation'] or "",
                company=result['company'],
                annual_income=result['annual_income'],
                family_type=result['family_type'] or "",
                family_status=result['family_status'] or "",
                is_verified=result['is_verified'] or False,
                last_active=result['last_login']
            )
    
    @staticmethod
    async def get_dashboard_data(user_id: int) -> DashboardData:
        """Get dashboard data for user"""
        async with get_pg_connection() as conn:
            # Get profile summary
            profile_summary = await ProfileService.get_profile_summary(user_id)
            
            # Calculate profile completion
            completion = await conn.fetchval("""
                SELECT CASE 
                    WHEN p.date_of_birth IS NOT NULL AND p.height IS NOT NULL 
                         AND e.highest_education IS NOT NULL AND c.occupation IS NOT NULL
                         AND f.family_type IS NOT NULL THEN 100
                    WHEN p.date_of_birth IS NOT NULL AND p.height IS NOT NULL THEN 60
                    WHEN p.first_name IS NOT NULL THEN 20
                    ELSE 0
                END as completion
                FROM user_profiles p
                LEFT JOIN user_education e ON p.user_id = e.user_id
                LEFT JOIN user_career c ON p.user_id = c.user_id
                LEFT JOIN user_family f ON p.user_id = f.user_id
                WHERE p.user_id = $1
            """, user_id)
            
            # Get verification status
            verification = await conn.fetchval("""
                SELECT CASE 
                    WHEN u.admin_approved = true THEN 'approved'
                    WHEN q.status = 'rejected' THEN 'rejected'
                    WHEN q.status = 'pending' THEN 'pending'
                    ELSE 'not_submitted'
                END
                FROM users u
                LEFT JOIN admin_verification_queue q ON u.id = q.user_id
                WHERE u.id = $1
            """, user_id)
            
            return DashboardData(
                profile_summary=profile_summary,
                profile_completion=completion or 0,
                recent_views=0,  # TODO: Implement view tracking
                shortlisted_count=0,  # TODO: Implement shortlisting
                messages_count=0,  # TODO: Implement messaging
                suggestions_count=0,  # TODO: Implement matching
                verification_status=verification or "not_submitted"
            )
    
    @staticmethod
    async def update_profile(user_id: int, update_data: ProfileUpdateRequest):
        """Update profile fields"""
        async with get_pg_connection() as conn:
            async with conn.transaction():
                # Update user_profiles
                profile_updates = []
                profile_values = []
                param_count = 1
                
                if update_data.first_name is not None:
                    profile_updates.append(f"first_name = ${param_count + 1}")
                    profile_values.append(update_data.first_name)
                    param_count += 1
                
                if update_data.last_name is not None:
                    profile_updates.append(f"last_name = ${param_count + 1}")
                    profile_values.append(update_data.last_name)
                    param_count += 1
                
                if update_data.height is not None:
                    profile_updates.append(f"height = ${param_count + 1}")
                    profile_values.append(update_data.height)
                    param_count += 1
                
                if update_data.weight is not None:
                    profile_updates.append(f"weight = ${param_count + 1}")
                    profile_values.append(update_data.weight)
                    param_count += 1
                
                if profile_updates:
                    query = f"""
                        UPDATE user_profiles SET {', '.join(profile_updates)}, updated_at = NOW()
                        WHERE user_id = $1
                    """
                    await conn.execute(query, user_id, *profile_values)
                
                # Update career info
                career_updates = []
                career_values = []
                param_count = 1
                
                if update_data.occupation is not None:
                    career_updates.append(f"occupation = ${param_count + 1}")
                    career_values.append(update_data.occupation)
                    param_count += 1
                
                if update_data.company is not None:
                    career_updates.append(f"company = ${param_count + 1}")
                    career_values.append(update_data.company)
                    param_count += 1
                
                if update_data.annual_income is not None:
                    career_updates.append(f"annual_income = ${param_count + 1}")
                    career_values.append(update_data.annual_income)
                    param_count += 1
                
                if career_updates:
                    query = f"""
                        UPDATE user_career SET {', '.join(career_updates)}
                        WHERE user_id = $1
                    """
                    await conn.execute(query, user_id, *career_values)
                
                # Clear cache
                cache_key = get_user_profile_cache_key(user_id)
                from app.core.cache import cache_delete
                await cache_delete(cache_key)
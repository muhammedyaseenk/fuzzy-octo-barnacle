# app/domains/matching/service.py
import math
from datetime import date, datetime
from typing import List, Dict, Any, Set
from fastapi import HTTPException, status

from app.core.db import get_pg_connection
from app.core.cache import cache_get, cache_set, get_matching_feed_cache_key, get_search_results_cache_key
from app.domains.matching.schemas import SearchFilters, MatchCard, SearchResponse, SortBy
from app.domains.moderation.service import ModerationService


class MatchingService:
    
    @staticmethod
    def calculate_age(birth_date: date) -> int:
        """Calculate age from birth date"""
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
    @staticmethod
    async def get_user_preferences(user_id: int) -> Dict[str, Any]:
        """Get user's matching preferences"""
        async with get_pg_connection() as conn:
            result = await conn.fetchrow("""
                SELECT min_age, max_age, min_height, max_height, 
                       preferred_religions, preferred_castes, min_income
                FROM user_preferences WHERE user_id = $1
            """, user_id)
            
            return dict(result) if result else {}
    
    @staticmethod
    async def build_search_query(filters: SearchFilters, user_id: int, blocked_users: Set[int]) -> tuple:
        """Build SQL query based on search filters"""
        conditions = []
        params = []
        param_count = 0
        
        # Base query
        base_query = """
            SELECT DISTINCT p.user_id, p.first_name, p.last_name, p.date_of_birth, 
                   p.height, p.religion, CONCAT(p.city, ', ', p.state) as location,
                   c.occupation, c.annual_income, e.highest_education,
                   u.last_login
            FROM user_profiles p
            LEFT JOIN user_career c ON p.user_id = c.user_id
            LEFT JOIN user_education e ON p.user_id = e.user_id
            LEFT JOIN users u ON p.user_id = u.id
            WHERE u.admin_approved = true AND u.is_active = true
        """
        
        # Exclude current user and blocked users
        excluded_users = {user_id} | blocked_users
        if excluded_users:
            param_count += 1
            conditions.append(f"p.user_id != ALL(${param_count})")
            params.append(list(excluded_users))
        
        # Age filter
        if filters.min_age or filters.max_age:
            if filters.min_age:
                param_count += 1
                conditions.append(f"EXTRACT(YEAR FROM AGE(p.date_of_birth)) >= ${param_count}")
                params.append(filters.min_age)
            if filters.max_age:
                param_count += 1
                conditions.append(f"EXTRACT(YEAR FROM AGE(p.date_of_birth)) <= ${param_count}")
                params.append(filters.max_age)
        
        # Height filter
        if filters.min_height:
            param_count += 1
            conditions.append(f"p.height >= ${param_count}")
            params.append(filters.min_height)
        if filters.max_height:
            param_count += 1
            conditions.append(f"p.height <= ${param_count}")
            params.append(filters.max_height)
        
        # String array filters
        if filters.marital_status:
            param_count += 1
            conditions.append(f"p.marital_status = ANY(${param_count})")
            params.append(filters.marital_status)
        
        if filters.religion:
            param_count += 1
            conditions.append(f"p.religion = ANY(${param_count})")
            params.append(filters.religion)
        
        if filters.caste:
            param_count += 1
            conditions.append(f"p.caste = ANY(${param_count})")
            params.append(filters.caste)
        
        if filters.mother_tongue:
            param_count += 1
            conditions.append(f"p.mother_tongue = ANY(${param_count})")
            params.append(filters.mother_tongue)
        
        # Location filters
        if filters.country:
            param_count += 1
            conditions.append(f"p.country = ${param_count}")
            params.append(filters.country)
        
        if filters.state:
            param_count += 1
            conditions.append(f"p.state = ${param_count}")
            params.append(filters.state)
        
        if filters.district:
            param_count += 1
            conditions.append(f"p.district = ${param_count}")
            params.append(filters.district)
        
        if filters.city:
            param_count += 1
            conditions.append(f"p.city = ${param_count}")
            params.append(filters.city)
        
        # Career filters
        if filters.occupation:
            param_count += 1
            conditions.append(f"c.occupation = ANY(${param_count})")
            params.append(filters.occupation)
        
        if filters.min_income:
            param_count += 1
            conditions.append(f"c.annual_income >= ${param_count}")
            params.append(filters.min_income)
        
        if filters.max_income:
            param_count += 1
            conditions.append(f"c.annual_income <= ${param_count}")
            params.append(filters.max_income)
        
        # Lifestyle filters
        if filters.diet:
            param_count += 1
            conditions.append(f"p.diet = ANY(${param_count})")
            params.append(filters.diet)
        
        if filters.smoking:
            param_count += 1
            conditions.append(f"p.smoking = ANY(${param_count})")
            params.append(filters.smoking)
        
        if filters.drinking:
            param_count += 1
            conditions.append(f"p.drinking = ANY(${param_count})")
            params.append(filters.drinking)
        
        if filters.education:
            param_count += 1
            conditions.append(f"e.highest_education = ANY(${param_count})")
            params.append(filters.education)
        
        # Build final query
        if conditions:
            query = base_query + " AND " + " AND ".join(conditions)
        else:
            query = base_query
        
        return query, params
    
    @staticmethod
    async def search_matches(user_id: int, filters: SearchFilters, sort_by: SortBy, page: int, limit: int) -> SearchResponse:
        """Search for matches based on filters"""
        # Get blocked users
        blocked_users = await ModerationService.get_blocked_users(user_id)
        users_who_blocked = await ModerationService.get_users_who_blocked(user_id)
        all_blocked = blocked_users | users_who_blocked
        
        # Check cache
        cache_key = get_search_results_cache_key({
            "user_id": user_id,
            "filters": filters.dict(),
            "sort_by": sort_by.value,
            "page": page,
            "limit": limit
        })
        cached = await cache_get(cache_key)
        if cached:
            return SearchResponse(**cached)
        
        async with get_pg_connection() as conn:
            # Build query
            base_query, params = await MatchingService.build_search_query(filters, user_id, all_blocked)
            
            # Add sorting
            if sort_by == SortBy.AGE:
                order_clause = "ORDER BY p.date_of_birth DESC"
            elif sort_by == SortBy.HEIGHT:
                order_clause = "ORDER BY p.height DESC"
            elif sort_by == SortBy.INCOME:
                order_clause = "ORDER BY c.annual_income DESC NULLS LAST"
            elif sort_by == SortBy.LAST_ACTIVE:
                order_clause = "ORDER BY u.last_login DESC NULLS LAST"
            else:  # RELEVANCE
                order_clause = "ORDER BY p.user_id"
            
            # Count total results
            count_query = f"SELECT COUNT(*) FROM ({base_query}) as subq"
            total_count = await conn.fetchval(count_query, *params)
            
            # Get paginated results
            offset = (page - 1) * limit
            paginated_query = f"{base_query} {order_clause} LIMIT {limit} OFFSET {offset}"
            
            results = await conn.fetch(paginated_query, *params)
            
            # Convert to MatchCard objects
            matches = []
            for row in results:
                age = MatchingService.calculate_age(row['date_of_birth']) if row['date_of_birth'] else 0
                
                match_card = MatchCard(
                    user_id=row['user_id'],
                    first_name=row['first_name'] or "",
                    last_name=row['last_name'] or "",
                    age=age,
                    height=row['height'] or 0,
                    occupation=row['occupation'] or "Not specified",
                    location=row['location'] or "Not specified",
                    education=row['highest_education'] or "Not specified",
                    religion=row['religion'] or "Not specified"
                )
                matches.append(match_card)
            
            # Calculate pagination
            total_pages = math.ceil(total_count / limit) if total_count > 0 else 1
            has_next = page < total_pages
            
            response = SearchResponse(
                matches=matches,
                total_count=total_count,
                page=page,
                total_pages=total_pages,
                has_next=has_next
            )
            
            # Cache for 10 minutes
            await cache_set(cache_key, response.dict(), 600)
            return response
    
    @staticmethod
    async def get_recommendations(user_id: int, page: int = 1, limit: int = 20) -> SearchResponse:
        """Get personalized recommendations based on user preferences"""
        # Get user preferences
        preferences = await MatchingService.get_user_preferences(user_id)
        
        if not preferences:
            # No preferences set, return empty results
            return SearchResponse(
                matches=[],
                total_count=0,
                page=page,
                total_pages=1,
                has_next=False
            )
        
        # Build filters from preferences
        filters = SearchFilters(
            min_age=preferences.get('min_age'),
            max_age=preferences.get('max_age'),
            min_height=preferences.get('min_height'),
            max_height=preferences.get('max_height'),
            religion=preferences.get('preferred_religions'),
            caste=preferences.get('preferred_castes'),
            min_income=preferences.get('min_income')
        )
        
        return await MatchingService.search_matches(user_id, filters, SortBy.RELEVANCE, page, limit)
    
    @staticmethod
    async def shortlist_user(user_id: int, target_user_id: int) -> int:
        """Add user to shortlist"""
        if user_id == target_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot shortlist yourself"
            )
        
        # Check if blocked
        is_blocked = await ModerationService.is_blocked(user_id, target_user_id)
        if is_blocked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot shortlist blocked user"
            )
        
        async with get_pg_connection() as conn:
            # Check if already shortlisted
            existing = await conn.fetchval("""
                SELECT id FROM user_shortlists 
                WHERE user_id = $1 AND shortlisted_user_id = $2
            """, user_id, target_user_id)
            
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User already shortlisted"
                )
            
            # Add to shortlist
            shortlist_id = await conn.fetchval("""
                INSERT INTO user_shortlists (user_id, shortlisted_user_id)
                VALUES ($1, $2) RETURNING id
            """, user_id, target_user_id)
            
            return shortlist_id
    
    @staticmethod
    async def remove_shortlist(user_id: int, target_user_id: int):
        """Remove user from shortlist"""
        async with get_pg_connection() as conn:
            result = await conn.execute("""
                DELETE FROM user_shortlists 
                WHERE user_id = $1 AND shortlisted_user_id = $2
            """, user_id, target_user_id)
            
            if result == "DELETE 0":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Shortlist entry not found"
                )
    
    @staticmethod
    async def get_shortlisted_users(user_id: int, page: int = 1, limit: int = 20) -> SearchResponse:
        """Get user's shortlisted profiles"""
        async with get_pg_connection() as conn:
            # Count total
            total_count = await conn.fetchval("""
                SELECT COUNT(*) FROM user_shortlists WHERE user_id = $1
            """, user_id)
            
            # Get paginated results
            offset = (page - 1) * limit
            results = await conn.fetch("""
                SELECT p.user_id, p.first_name, p.last_name, p.date_of_birth, 
                       p.height, p.religion, CONCAT(p.city, ', ', p.state) as location,
                       c.occupation, e.highest_education
                FROM user_shortlists s
                JOIN user_profiles p ON s.shortlisted_user_id = p.user_id
                LEFT JOIN user_career c ON p.user_id = c.user_id
                LEFT JOIN user_education e ON p.user_id = e.user_id
                WHERE s.user_id = $1
                ORDER BY s.created_at DESC
                LIMIT $2 OFFSET $3
            """, user_id, limit, offset)
            
            # Convert to MatchCard objects
            matches = []
            for row in results:
                age = MatchingService.calculate_age(row['date_of_birth']) if row['date_of_birth'] else 0
                
                match_card = MatchCard(
                    user_id=row['user_id'],
                    first_name=row['first_name'] or "",
                    last_name=row['last_name'] or "",
                    age=age,
                    height=row['height'] or 0,
                    occupation=row['occupation'] or "Not specified",
                    location=row['location'] or "Not specified",
                    education=row['highest_education'] or "Not specified",
                    religion=row['religion'] or "Not specified",
                    is_shortlisted=True
                )
                matches.append(match_card)
            
            # Calculate pagination
            total_pages = math.ceil(total_count / limit) if total_count > 0 else 1
            has_next = page < total_pages
            
            return SearchResponse(
                matches=matches,
                total_count=total_count,
                page=page,
                total_pages=total_pages,
                has_next=has_next
            )
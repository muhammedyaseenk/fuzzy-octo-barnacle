# app/domains/matching/api_optimized.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.core.db import get_db
from app.core.security import get_current_user
from app.core.cache import redis_client
from app.core.pagination import paginate_cursor, CursorPage
from app.domains.onboarding.models import Profile
from app.domains.matching.models import UserShortlist
from typing import Optional
import json

router = APIRouter(prefix="/api/v1/matching", tags=["matching"])

@router.get("/profiles/scroll")
async def scroll_profiles(
    cursor: Optional[str] = None,
    limit: int = Query(20, le=50),
    gender: Optional[str] = None,
    min_age: Optional[int] = None,
    max_age: Optional[int] = None,
    religion: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Optimized infinite scroll with cursor pagination
    - No offset/limit (O(1) seek time)
    - Redis caching per cursor
    - Batch loading
    """
    
    # Build cache key
    cache_key = f"scroll:{current_user['id']}:{cursor or 'start'}:{gender}:{min_age}:{max_age}:{religion}"
    
    # Check cache
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Build query
    query = select(Profile).where(
        and_(
            Profile.user_id != current_user['id'],
            Profile.verification_status == 'approved'
        )
    )
    
    if gender:
        query = query.where(Profile.gender == gender)
    if min_age:
        query = query.where(func.extract('year', func.age(Profile.date_of_birth)) >= min_age)
    if max_age:
        query = query.where(func.extract('year', func.age(Profile.date_of_birth)) <= max_age)
    if religion:
        query = query.where(Profile.religion == religion)
    
    # Paginate with cursor
    result = await paginate_cursor(
        db, query, cursor=cursor, limit=limit, 
        order_by_field="created_at", order_desc=True
    )
    
    # Convert to dict
    response = {
        "items": [
            {
                "id": p.id,
                "user_id": p.user_id,
                "first_name": p.first_name,
                "age": p.date_of_birth,
                "religion": p.religion,
                "education": p.education_level,
                "occupation": p.occupation,
                "city": p.city
            } for p in result.items
        ],
        "next_cursor": result.next_cursor,
        "has_more": result.has_more
    }
    
    # Cache for 2 minutes
    await redis_client.setex(cache_key, 120, json.dumps(response))
    
    return response

@router.get("/profiles/batch")
async def get_profiles_batch(
    profile_ids: str = Query(..., description="Comma-separated IDs"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Batch load profiles for visible viewport
    Reduces N+1 queries when scrolling
    """
    ids = [int(x) for x in profile_ids.split(',')[:50]]  # Max 50
    
    # Try cache first
    cache_keys = [f"profile:{pid}" for pid in ids]
    cached_profiles = await redis_client.mget(cache_keys)
    
    profiles = []
    missing_ids = []
    
    for i, cached in enumerate(cached_profiles):
        if cached:
            profiles.append(json.loads(cached))
        else:
            missing_ids.append(ids[i])
    
    # Fetch missing from DB in single query
    if missing_ids:
        result = await db.execute(
            select(Profile).where(Profile.id.in_(missing_ids))
        )
        db_profiles = result.scalars().all()
        
        for p in db_profiles:
            profile_data = {
                "id": p.id,
                "user_id": p.user_id,
                "first_name": p.first_name,
                "age": p.date_of_birth,
                "religion": p.religion,
                "education": p.education_level,
                "occupation": p.occupation,
                "city": p.city
            }
            profiles.append(profile_data)
            
            # Cache individual profile
            await redis_client.setex(
                f"profile:{p.id}", 
                3600, 
                json.dumps(profile_data)
            )
    
    return {"profiles": profiles}

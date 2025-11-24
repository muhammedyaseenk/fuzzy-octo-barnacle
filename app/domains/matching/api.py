# app/domains/matching/api.py
from fastapi import APIRouter, Depends, Request, Query
from typing import Optional, List

from app.core.security import get_current_user
from app.core.rate_limit import api_rate_limit
from app.domains.identity.models import User
from app.domains.matching.schemas import (
    SearchFilters, SearchResponse, SortBy, ShortlistAction
)
from app.domains.matching.service import MatchingService

router = APIRouter(prefix="/matching", tags=["Matching"])


@router.get("/recommendations", response_model=SearchResponse)
@api_rate_limit()
async def get_recommendations(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Get personalized match recommendations"""
    return await MatchingService.get_recommendations(current_user.id, page, limit)


@router.post("/search", response_model=SearchResponse)
@api_rate_limit()
async def search_matches(
    request: Request,
    filters: SearchFilters,
    sort_by: SortBy = SortBy.RELEVANCE,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Search for matches with filters"""
    return await MatchingService.search_matches(current_user.id, filters, sort_by, page, limit)


@router.get("/search", response_model=SearchResponse)
@api_rate_limit()
async def search_matches_get(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    # Age filters
    min_age: Optional[int] = Query(None, ge=18, le=100),
    max_age: Optional[int] = Query(None, ge=18, le=100),
    # Height filters
    min_height: Optional[int] = Query(None, ge=100, le=250),
    max_height: Optional[int] = Query(None, ge=100, le=250),
    # Location filters
    country: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    # Other filters
    religion: Optional[List[str]] = Query(None),
    caste: Optional[List[str]] = Query(None),
    mother_tongue: Optional[List[str]] = Query(None),
    marital_status: Optional[List[str]] = Query(None),
    occupation: Optional[List[str]] = Query(None),
    min_income: Optional[int] = Query(None, ge=0),
    max_income: Optional[int] = Query(None, ge=0),
    diet: Optional[List[str]] = Query(None),
    smoking: Optional[List[str]] = Query(None),
    drinking: Optional[List[str]] = Query(None),
    education: Optional[List[str]] = Query(None),
    sort_by: SortBy = SortBy.RELEVANCE,
    current_user: User = Depends(get_current_user)
):
    """Search for matches with GET parameters (for easy URL sharing)"""
    filters = SearchFilters(
        min_age=min_age,
        max_age=max_age,
        min_height=min_height,
        max_height=max_height,
        country=country,
        state=state,
        district=district,
        city=city,
        religion=religion,
        caste=caste,
        mother_tongue=mother_tongue,
        marital_status=marital_status,
        occupation=occupation,
        min_income=min_income,
        max_income=max_income,
        diet=diet,
        smoking=smoking,
        drinking=drinking,
        education=education
    )
    
    return await MatchingService.search_matches(current_user.id, filters, sort_by, page, limit)


@router.post("/shortlist")
@api_rate_limit()
async def add_to_shortlist(
    request: Request,
    action: ShortlistAction,
    current_user: User = Depends(get_current_user)
):
    """Add user to shortlist"""
    shortlist_id = await MatchingService.shortlist_user(current_user.id, action.target_user_id)
    return {
        "message": "User added to shortlist",
        "shortlist_id": shortlist_id
    }


@router.delete("/shortlist/{user_id}")
@api_rate_limit()
async def remove_from_shortlist(
    request: Request,
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """Remove user from shortlist"""
    await MatchingService.remove_shortlist(current_user.id, user_id)
    return {"message": "User removed from shortlist"}


@router.get("/shortlisted", response_model=SearchResponse)
@api_rate_limit()
async def get_shortlisted_users(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Get shortlisted users"""
    return await MatchingService.get_shortlisted_users(current_user.id, page, limit)
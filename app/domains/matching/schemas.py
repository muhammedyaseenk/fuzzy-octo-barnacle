# app/domains/matching/schemas.py
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class SortBy(str, Enum):
    RELEVANCE = "relevance"
    AGE = "age"
    HEIGHT = "height"
    INCOME = "income"
    LAST_ACTIVE = "last_active"


class SearchFilters(BaseModel):
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    min_height: Optional[int] = None
    max_height: Optional[int] = None
    marital_status: Optional[List[str]] = None
    religion: Optional[List[str]] = None
    caste: Optional[List[str]] = None
    mother_tongue: Optional[List[str]] = None
    country: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    occupation: Optional[List[str]] = None
    min_income: Optional[int] = None
    max_income: Optional[int] = None
    diet: Optional[List[str]] = None
    smoking: Optional[List[str]] = None
    drinking: Optional[List[str]] = None
    education: Optional[List[str]] = None


class MatchCard(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    age: int
    height: int
    occupation: str
    location: str
    education: str
    religion: str
    match_score: Optional[int] = None
    is_shortlisted: bool = False
    profile_image: Optional[str] = None


class SearchRequest(BaseModel):
    filters: SearchFilters
    sort_by: SortBy = SortBy.RELEVANCE
    page: int = 1
    limit: int = 20


class SearchResponse(BaseModel):
    matches: List[MatchCard]
    total_count: int
    page: int
    total_pages: int
    has_next: bool


class ShortlistAction(BaseModel):
    target_user_id: int


class InterestAction(BaseModel):
    target_user_id: int
    message: Optional[str] = None
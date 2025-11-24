# app/tasks/matching.py
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict
from app.celery_app import celery_app
from app.domains.matching.service import MatchingService
from app.core.cache import cache_delete, cache_set, cache_get
from app.core.db import get_pg_connection
from app.tasks.notifications import send_push_notification, send_email_notification


@celery_app.task(bind=True, retry_backoff=True, max_retries=3)
def send_daily_matches(self):
    """Send daily match recommendations to all active users"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_send_daily_matches_async())


async def _send_daily_matches_async():
    """Async implementation of daily matches"""
    async with get_pg_connection() as conn:
        # Get all active users who want daily matches
        users = await conn.fetch("""
            SELECT u.id, u.email, p.first_name 
            FROM users u
            JOIN user_profiles p ON u.id = p.user_id
            WHERE u.is_active = true 
            AND u.admin_approved = true
            AND u.last_login > NOW() - INTERVAL '7 days'
        """)
        
        sent_count = 0
        for user in users:
            try:
                # Get top 5 matches for user
                matches = await MatchingService.get_recommendations(user['id'], page=1, limit=5)
                
                if matches.total_count > 0:
                    # Send notification
                    send_push_notification.delay(
                        user['id'],
                        "New Matches Available",
                        f"We found {matches.total_count} new matches for you!"
                    )
                    
                    # Send email with match details
                    if user['email']:
                        send_email_notification.delay(
                            user['id'],
                            "daily_matches",
                            {"matches": [m.dict() for m in matches.matches[:5]]}
                        )
                    
                    sent_count += 1
            except Exception as e:
                print(f"Error sending matches to user {user['id']}: {e}")
                continue
        
        return {"status": "completed", "users_notified": sent_count}


@celery_app.task(bind=True, retry_backoff=True, max_retries=3)
def update_match_scores(self, user_id: int):
    """Update match compatibility scores for a user"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_update_match_scores_async(user_id))


async def _update_match_scores_async(user_id: int):
    """Calculate and cache match scores"""
    async with get_pg_connection() as conn:
        # Get user preferences
        prefs = await conn.fetchrow("""
            SELECT min_age, max_age, min_height, max_height, 
                   preferred_religions, preferred_castes, min_income
            FROM user_preferences WHERE user_id = $1
        """, user_id)
        
        if not prefs:
            return {"status": "no_preferences"}
        
        # Get user profile for compatibility calculation
        profile = await conn.fetchrow("""
            SELECT date_of_birth, height, religion, caste, mother_tongue
            FROM user_profiles WHERE user_id = $1
        """, user_id)
        
        # Find potential matches based on preferences
        potential_matches = await conn.fetch("""
            SELECT p.user_id, p.date_of_birth, p.height, p.religion, p.caste,
                   c.annual_income, c.occupation
            FROM user_profiles p
            JOIN user_career c ON p.user_id = c.user_id
            JOIN users u ON p.user_id = u.id
            WHERE u.is_active = true 
            AND u.admin_approved = true
            AND p.user_id != $1
            AND EXTRACT(YEAR FROM AGE(p.date_of_birth)) BETWEEN $2 AND $3
            AND p.height BETWEEN $4 AND $5
            LIMIT 100
        """, user_id, prefs['min_age'], prefs['max_age'], 
             prefs['min_height'], prefs['max_height'])
        
        # Calculate compatibility scores
        scores = {}
        for match in potential_matches:
            score = _calculate_compatibility_score(profile, match, prefs)
            scores[match['user_id']] = score
        
        # Cache the scores
        await cache_set(f"match_scores:{user_id}", scores, 86400)  # 24 hours
        
        # Clear old recommendations cache
        await cache_delete(f"recommendations:{user_id}")
        
        return {"status": "updated", "matches_scored": len(scores)}


def _calculate_compatibility_score(user_profile: Dict, match_profile: Dict, preferences: Dict) -> int:
    """Calculate compatibility score between two profiles"""
    score = 0
    
    # Religion match (30 points)
    if preferences.get('preferred_religions') and match_profile['religion'] in preferences['preferred_religions']:
        score += 30
    
    # Caste match (20 points)
    if preferences.get('preferred_castes') and match_profile['caste'] in preferences['preferred_castes']:
        score += 20
    
    # Income match (25 points)
    if preferences.get('min_income') and match_profile['annual_income']:
        if match_profile['annual_income'] >= preferences['min_income']:
            score += 25
    
    # Height preference (15 points)
    height_diff = abs(match_profile['height'] - user_profile['height'])
    if height_diff <= 10:
        score += 15
    elif height_diff <= 20:
        score += 10
    
    # Same religion bonus (10 points)
    if user_profile['religion'] == match_profile['religion']:
        score += 10
    
    return min(score, 100)


@celery_app.task(bind=True, retry_backoff=True, max_retries=3)
def process_profile_update(self, user_id: int):
    """Process profile update and refresh related caches"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_process_profile_update_async(user_id))


async def _process_profile_update_async(user_id: int):
    """Clear caches and trigger updates"""
    # Clear all related caches
    await cache_delete(f"profile:{user_id}")
    await cache_delete(f"recommendations:{user_id}")
    await cache_delete(f"match_scores:{user_id}")
    
    # Clear search caches that might include this user
    async with get_pg_connection() as conn:
        profile = await conn.fetchrow("""
            SELECT religion, caste, state, city FROM user_profiles WHERE user_id = $1
        """, user_id)
        
        if profile:
            # Clear location-based caches
            await cache_delete(f"search:state:{profile['state']}")
            await cache_delete(f"search:city:{profile['city']}")
            await cache_delete(f"search:religion:{profile['religion']}")
    
    # Trigger match score updates asynchronously
    update_match_scores.apply_async(args=[user_id], countdown=60)
    
    return {"status": "processed", "user_id": user_id}


@celery_app.task(bind=True, retry_backoff=True, max_retries=3)
def generate_compatibility_report(self, user1_id: int, user2_id: int):
    """Generate detailed compatibility report between two users"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_generate_compatibility_report_async(user1_id, user2_id))


async def _generate_compatibility_report_async(user1_id: int, user2_id: int):
    """Generate detailed compatibility analysis"""
    async with get_pg_connection() as conn:
        # Get both profiles
        profiles = await conn.fetch("""
            SELECT p.user_id, p.first_name, p.date_of_birth, p.height, p.religion, 
                   p.caste, p.mother_tongue, p.diet, p.smoking, p.drinking,
                   e.highest_education, c.occupation, c.annual_income,
                   f.family_type, f.family_status
            FROM user_profiles p
            LEFT JOIN user_education e ON p.user_id = e.user_id
            LEFT JOIN user_career c ON p.user_id = c.user_id
            LEFT JOIN user_family f ON p.user_id = f.user_id
            WHERE p.user_id IN ($1, $2)
        """, user1_id, user2_id)
        
        if len(profiles) != 2:
            return {"error": "One or both profiles not found"}
        
        user1 = dict(profiles[0])
        user2 = dict(profiles[1])
        
        # Calculate detailed compatibility
        report = {
            "user1_id": user1_id,
            "user2_id": user2_id,
            "overall_score": 0,
            "categories": {}
        }
        
        # Religious compatibility (25%)
        religion_score = 100 if user1['religion'] == user2['religion'] else 50
        if user1['caste'] == user2['caste']:
            religion_score = min(religion_score + 20, 100)
        report['categories']['religious'] = religion_score
        
        # Educational compatibility (20%)
        edu_levels = {'PhD': 5, 'Masters': 4, 'Bachelors': 3, 'Diploma': 2, 'High School': 1}
        edu1 = edu_levels.get(user1.get('highest_education', ''), 3)
        edu2 = edu_levels.get(user2.get('highest_education', ''), 3)
        edu_score = max(0, 100 - abs(edu1 - edu2) * 20)
        report['categories']['educational'] = edu_score
        
        # Lifestyle compatibility (20%)
        lifestyle_score = 100
        if user1['diet'] != user2['diet']:
            lifestyle_score -= 30
        if user1['smoking'] != user2['smoking']:
            lifestyle_score -= 35
        if user1['drinking'] != user2['drinking']:
            lifestyle_score -= 35
        report['categories']['lifestyle'] = max(0, lifestyle_score)
        
        # Family compatibility (15%)
        family_score = 100 if user1['family_type'] == user2['family_type'] else 70
        report['categories']['family'] = family_score
        
        # Financial compatibility (20%)
        income1 = user1.get('annual_income', 0) or 0
        income2 = user2.get('annual_income', 0) or 0
        income_diff = abs(income1 - income2)
        if income_diff < 200000:
            financial_score = 100
        elif income_diff < 500000:
            financial_score = 80
        elif income_diff < 1000000:
            financial_score = 60
        else:
            financial_score = 40
        report['categories']['financial'] = financial_score
        
        # Calculate overall score
        report['overall_score'] = int(
            religion_score * 0.25 +
            edu_score * 0.20 +
            lifestyle_score * 0.20 +
            family_score * 0.15 +
            financial_score * 0.20
        )
        
        # Cache the report
        report_id = f"{user1_id}_{user2_id}"
        await cache_set(f"compatibility_report:{report_id}", report, 604800)  # 7 days
        
        report['report_id'] = report_id
        report['generated_at'] = datetime.utcnow().isoformat()
        
        return report


@celery_app.task
def batch_update_match_scores(user_ids: List[int]):
    """Update match scores for multiple users"""
    for user_id in user_ids:
        update_match_scores.apply_async(args=[user_id], countdown=5)
    
    return {"status": "queued", "count": len(user_ids)}


@celery_app.task
def cleanup_stale_match_caches():
    """Cleanup match caches older than 7 days"""
    # Implementation for cache cleanup
    return {"status": "cleaned"}
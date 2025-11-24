# app/domains/moderation/service.py
from datetime import datetime
from typing import List, Set
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.db import get_pg_connection
from app.domains.moderation.models import UserReport, UserBlock
from app.domains.moderation.schemas import (
    ReportUserRequest, BlockUserRequest, AdminReportView, AdminResolveRequest
)


class ModerationService:
    
    @staticmethod
    async def report_user(reporter_id: int, report_data: ReportUserRequest) -> int:
        """Report a user for inappropriate behavior"""
        if reporter_id == report_data.reported_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot report yourself"
            )
        
        async with get_pg_connection() as conn:
            # Check if already reported recently (within 24 hours)
            existing = await conn.fetchval("""
                SELECT id FROM user_reports 
                WHERE reporter_id = $1 AND reported_user_id = $2 
                AND created_at > NOW() - INTERVAL '24 hours'
            """, reporter_id, report_data.reported_user_id)
            
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You have already reported this user recently"
                )
            
            # Create report
            report_id = await conn.fetchval("""
                INSERT INTO user_reports (reporter_id, reported_user_id, reason, details)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            """, reporter_id, report_data.reported_user_id, report_data.reason.value, report_data.details)
            
            return report_id
    
    @staticmethod
    async def block_user(blocker_id: int, block_data: BlockUserRequest) -> int:
        """Block a user"""
        if blocker_id == block_data.blocked_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot block yourself"
            )
        
        async with get_pg_connection() as conn:
            # Check if already blocked
            existing = await conn.fetchval("""
                SELECT id FROM user_blocks 
                WHERE blocker_id = $1 AND blocked_user_id = $2
            """, blocker_id, block_data.blocked_user_id)
            
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User is already blocked"
                )
            
            # Create block
            block_id = await conn.fetchval("""
                INSERT INTO user_blocks (blocker_id, blocked_user_id, reason)
                VALUES ($1, $2, $3)
                RETURNING id
            """, blocker_id, block_data.blocked_user_id, block_data.reason)
            
            return block_id
    
    @staticmethod
    async def unblock_user(blocker_id: int, blocked_user_id: int):
        """Unblock a user"""
        async with get_pg_connection() as conn:
            result = await conn.execute("""
                DELETE FROM user_blocks 
                WHERE blocker_id = $1 AND blocked_user_id = $2
            """, blocker_id, blocked_user_id)
            
            if result == "DELETE 0":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Block relationship not found"
                )
    
    @staticmethod
    async def get_blocked_users(user_id: int) -> Set[int]:
        """Get set of user IDs that are blocked by the user"""
        async with get_pg_connection() as conn:
            results = await conn.fetch("""
                SELECT blocked_user_id FROM user_blocks WHERE blocker_id = $1
            """, user_id)
            
            return {row['blocked_user_id'] for row in results}
    
    @staticmethod
    async def get_users_who_blocked(user_id: int) -> Set[int]:
        """Get set of user IDs who have blocked this user"""
        async with get_pg_connection() as conn:
            results = await conn.fetch("""
                SELECT blocker_id FROM user_blocks WHERE blocked_user_id = $1
            """, user_id)
            
            return {row['blocker_id'] for row in results}
    
    @staticmethod
    async def is_blocked(user1_id: int, user2_id: int) -> bool:
        """Check if either user has blocked the other"""
        async with get_pg_connection() as conn:
            result = await conn.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM user_blocks 
                    WHERE (blocker_id = $1 AND blocked_user_id = $2)
                       OR (blocker_id = $2 AND blocked_user_id = $1)
                )
            """, user1_id, user2_id)
            
            return result
    
    @staticmethod
    async def get_my_reports(user_id: int) -> List[dict]:
        """Get reports made by the user"""
        async with get_pg_connection() as conn:
            results = await conn.fetch("""
                SELECT r.id, r.reported_user_id, r.reason, r.status, r.created_at,
                       p.first_name, p.last_name
                FROM user_reports r
                JOIN user_profiles p ON r.reported_user_id = p.user_id
                WHERE r.reporter_id = $1
                ORDER BY r.created_at DESC
            """, user_id)
            
            return [dict(row) for row in results]
    
    @staticmethod
    async def get_my_blocks(user_id: int) -> List[dict]:
        """Get users blocked by the user"""
        async with get_pg_connection() as conn:
            results = await conn.fetch("""
                SELECT b.id, b.blocked_user_id, b.reason, b.created_at,
                       p.first_name, p.last_name
                FROM user_blocks b
                JOIN user_profiles p ON b.blocked_user_id = p.user_id
                WHERE b.blocker_id = $1
                ORDER BY b.created_at DESC
            """, user_id)
            
            return [dict(row) for row in results]
    
    # Admin functions
    @staticmethod
    async def get_pending_reports(skip: int = 0, limit: int = 50) -> List[AdminReportView]:
        """Get pending reports for admin review"""
        async with get_pg_connection() as conn:
            results = await conn.fetch("""
                SELECT r.id, r.reason, r.details, r.status, r.created_at, 
                       r.reviewed_at, r.admin_notes,
                       rp.first_name || ' ' || rp.last_name as reporter_name,
                       up.first_name || ' ' || up.last_name as reported_user_name
                FROM user_reports r
                JOIN user_profiles rp ON r.reporter_id = rp.user_id
                JOIN user_profiles up ON r.reported_user_id = up.user_id
                WHERE r.status = 'pending'
                ORDER BY r.created_at ASC
                OFFSET $1 LIMIT $2
            """, skip, limit)
            
            return [
                AdminReportView(
                    id=row['id'],
                    reporter_name=row['reporter_name'],
                    reported_user_name=row['reported_user_name'],
                    reason=row['reason'],
                    details=row['details'],
                    status=row['status'],
                    created_at=row['created_at'],
                    reviewed_at=row['reviewed_at'],
                    admin_notes=row['admin_notes']
                )
                for row in results
            ]
    
    @staticmethod
    async def resolve_report(report_id: int, admin_id: int, resolve_data: AdminResolveRequest):
        """Resolve a report (admin action)"""
        async with get_pg_connection() as conn:
            result = await conn.execute("""
                UPDATE user_reports 
                SET status = $2, admin_notes = $3, reviewed_at = NOW(), reviewed_by = $4
                WHERE id = $1
            """, report_id, resolve_data.status.value, resolve_data.admin_notes, admin_id)
            
            if result == "UPDATE 0":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Report not found"
                )
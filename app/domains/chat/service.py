# app/domains/chat/service.py
from typing import List, Optional
from fastapi import HTTPException, status
from app.core.db import get_pg_connection
from app.domains.moderation.service import ModerationService
from app.domains.chat.schemas import MessageResponse, ConversationResponse


class ChatService:
    
    @staticmethod
    async def get_or_create_conversation(user1_id: int, user2_id: int) -> int:
        """Get existing conversation or create new one"""
        # Check if blocked
        is_blocked = await ModerationService.is_blocked(user1_id, user2_id)
        if is_blocked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot message blocked user"
            )
        
        async with get_pg_connection() as conn:
            # Check existing conversation
            conversation_id = await conn.fetchval("""
                SELECT id FROM conversations
                WHERE (user1_id = $1 AND user2_id = $2)
                   OR (user1_id = $2 AND user2_id = $1)
            """, user1_id, user2_id)
            
            if conversation_id:
                return conversation_id
            
            # Create new conversation
            conversation_id = await conn.fetchval("""
                INSERT INTO conversations (user1_id, user2_id)
                VALUES ($1, $2) RETURNING id
            """, min(user1_id, user2_id), max(user1_id, user2_id))
            
            return conversation_id
    
    @staticmethod
    async def send_message(sender_id: int, conversation_id: int, content: str) -> MessageResponse:
        """Send a message"""
        async with get_pg_connection() as conn:
            # Verify user is part of conversation
            participant = await conn.fetchval("""
                SELECT 1 FROM conversations
                WHERE id = $1 AND (user1_id = $2 OR user2_id = $2)
            """, conversation_id, sender_id)
            
            if not participant:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized for this conversation"
                )
            
            # Insert message
            message_id = await conn.fetchval("""
                INSERT INTO messages (conversation_id, sender_id, content)
                VALUES ($1, $2, $3) RETURNING id
            """, conversation_id, sender_id, content)
            
            # Update conversation last_message_at
            await conn.execute("""
                UPDATE conversations SET last_message_at = NOW()
                WHERE id = $1
            """, conversation_id)
            
            # Get the created message
            result = await conn.fetchrow("""
                SELECT id, conversation_id, sender_id, content, is_read, created_at
                FROM messages WHERE id = $1
            """, message_id)
            
            return MessageResponse(**dict(result))
    
    @staticmethod
    async def get_conversations(user_id: int) -> List[ConversationResponse]:
        """Get user's conversations"""
        async with get_pg_connection() as conn:
            results = await conn.fetch("""
                SELECT c.id, 
                       CASE WHEN c.user1_id = $1 THEN c.user2_id ELSE c.user1_id END as participant_id,
                       CASE WHEN c.user1_id = $1 THEN p2.first_name || ' ' || p2.last_name 
                            ELSE p1.first_name || ' ' || p1.last_name END as participant_name,
                       c.last_message_at,
                       (SELECT content FROM messages WHERE conversation_id = c.id 
                        ORDER BY created_at DESC LIMIT 1) as last_message,
                       (SELECT COUNT(*) FROM messages 
                        WHERE conversation_id = c.id AND sender_id != $1 AND is_read = false) as unread_count
                FROM conversations c
                JOIN user_profiles p1 ON c.user1_id = p1.user_id
                JOIN user_profiles p2 ON c.user2_id = p2.user_id
                WHERE c.user1_id = $1 OR c.user2_id = $1
                ORDER BY c.last_message_at DESC NULLS LAST
            """, user_id)
            
            return [
                ConversationResponse(
                    id=row['id'],
                    participant_id=row['participant_id'],
                    participant_name=row['participant_name'],
                    last_message=row['last_message'],
                    last_message_at=row['last_message_at'],
                    unread_count=row['unread_count']
                )
                for row in results
            ]
    
    @staticmethod
    async def get_messages(user_id: int, conversation_id: int, skip: int = 0, limit: int = 50) -> List[MessageResponse]:
        """Get messages in a conversation"""
        async with get_pg_connection() as conn:
            # Verify user is part of conversation
            participant = await conn.fetchval("""
                SELECT 1 FROM conversations
                WHERE id = $1 AND (user1_id = $2 OR user2_id = $2)
            """, conversation_id, user_id)
            
            if not participant:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized for this conversation"
                )
            
            results = await conn.fetch("""
                SELECT id, conversation_id, sender_id, content, is_read, created_at
                FROM messages
                WHERE conversation_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """, conversation_id, limit, skip)
            
            return [MessageResponse(**dict(row)) for row in results]
    
    @staticmethod
    async def mark_messages_read(user_id: int, conversation_id: int):
        """Mark messages as read"""
        async with get_pg_connection() as conn:
            await conn.execute("""
                UPDATE messages SET is_read = true
                WHERE conversation_id = $1 AND sender_id != $2 AND is_read = false
            """, conversation_id, user_id)
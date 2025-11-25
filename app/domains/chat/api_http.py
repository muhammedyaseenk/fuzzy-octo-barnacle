# app/domains/chat/api_http.py
from fastapi import APIRouter, Depends, Request
from typing import List
from app.core.security import get_current_user
from app.core.rate_limit import api_rate_limit
from app.domains.identity.models import User
from app.domains.chat.schemas import MessageCreate, MessageResponse, ConversationResponse
from app.domains.chat.service import ChatService

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get("/conversations", response_model=List[ConversationResponse])
@api_rate_limit()
async def get_conversations(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get user's conversations"""
    return await ChatService.get_conversations(current_user.id)


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
@api_rate_limit()
async def get_messages(
    request: Request,
    conversation_id: int,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    """Get messages in a conversation"""
    return await ChatService.get_messages(current_user.id, conversation_id, skip, limit)


@router.post("/conversations/{user_id}")
@api_rate_limit()
async def start_conversation(
    request: Request,
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """Start conversation with a user"""
    conversation_id = await ChatService.get_or_create_conversation(current_user.id, user_id)
    return {"conversation_id": conversation_id}


@router.post("/messages", response_model=MessageResponse)
@api_rate_limit()
async def send_message(
    request: Request,
    message: MessageCreate,
    current_user: User = Depends(get_current_user)
):
    """Send a message with AI content moderation"""
    from app.core.content_moderator import content_moderator
    from fastapi import HTTPException, status
    
    # Get recipient from conversation
    conversation = await ChatService.get_conversation(message.conversation_id)
    recipient_id = conversation.user2_id if conversation.user1_id == current_user.id else conversation.user1_id
    
    # AI moderation for ALL messages
    moderation_result = await content_moderator.moderate_message(
        current_user.id,
        recipient_id,
        message.content
    )
    
    if not moderation_result["approved"]:
        if moderation_result["requires_admin"]:
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail="Your message is under review by our team for safety compliance"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message blocked for policy violation"
            )
    
    return await ChatService.send_message(current_user.id, message.conversation_id, message.content)


@router.post("/conversations/{conversation_id}/read")
@api_rate_limit()
async def mark_messages_read(
    request: Request,
    conversation_id: int,
    current_user: User = Depends(get_current_user)
):
    """Mark messages as read"""
    await ChatService.mark_messages_read(current_user.id, conversation_id)
    return {"message": "Messages marked as read"}
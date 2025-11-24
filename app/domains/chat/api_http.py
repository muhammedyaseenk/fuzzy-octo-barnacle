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
    """Send a message"""
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
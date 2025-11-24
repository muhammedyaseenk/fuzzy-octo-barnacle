# app/domains/chat/schemas.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class MessageCreate(BaseModel):
    conversation_id: int
    content: str


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    content: str
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: int
    participant_id: int
    participant_name: str
    last_message: Optional[str]
    last_message_at: Optional[datetime]
    unread_count: int
    
    class Config:
        from_attributes = True


class WSMessage(BaseModel):
    type: str  # "message", "typing", "read"
    conversation_id: Optional[int] = None
    content: Optional[str] = None
    message_id: Optional[int] = None
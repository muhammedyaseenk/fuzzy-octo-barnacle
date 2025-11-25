# app/domains/chat/api_ws.py
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set
from app.core.security import verify_token
from app.domains.chat.service import ChatService
from app.domains.chat.schemas import WSMessage

router = APIRouter()

# Store active connections
active_connections: Dict[int, Set[WebSocket]] = {}


async def get_user_from_token(websocket: WebSocket, token: str) -> int:
    """Get user ID from WebSocket token"""
    payload = verify_token(token)
    if not payload:
        await websocket.close(code=1008, reason="Invalid token")
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=1008, reason="Invalid token payload")
        return None
    
    return int(user_id)


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket, token: str):
    """WebSocket endpoint for real-time chat"""
    await websocket.accept()
    
    # Authenticate user
    user_id = await get_user_from_token(websocket, token)
    if not user_id:
        return
    
    # Add to active connections
    if user_id not in active_connections:
        active_connections[user_id] = set()
    active_connections[user_id].add(websocket)
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message_data = json.loads(data)
            ws_message = WSMessage(**message_data)
            
            if ws_message.type == "message":
                # AI moderation for ALL WebSocket messages
                from app.core.content_moderator import content_moderator
                
                # Get recipient from conversation
                conversation = await ChatService.get_conversation(ws_message.conversation_id)
                recipient_id = conversation['user2_id'] if conversation['user1_id'] == user_id else conversation['user1_id']
                
                # Moderate message
                moderation_result = await content_moderator.moderate_message(
                    user_id,
                    recipient_id,
                    ws_message.content
                )
                
                if not moderation_result["approved"]:
                    # Send error back to sender
                    error_data = {
                        "type": "error",
                        "message": "Message blocked" if not moderation_result["requires_admin"] else "Message under review"
                    }
                    await websocket.send_text(json.dumps(error_data))
                    continue
                
                # Send message
                message_response = await ChatService.send_message(
                    user_id, ws_message.conversation_id, ws_message.content
                )
                
                # Get recipient user ID
                # (This would need conversation participant lookup)
                # For now, broadcast to all connections
                broadcast_data = {
                    "type": "new_message",
                    "message": message_response.dict()
                }
                
                # Broadcast to all active connections
                for uid, connections in active_connections.items():
                    if uid != user_id:  # Don't send back to sender
                        for conn in connections.copy():
                            try:
                                await conn.send_text(json.dumps(broadcast_data))
                            except:
                                connections.discard(conn)
            
            elif ws_message.type == "typing":
                # Handle typing indicator
                typing_data = {
                    "type": "typing",
                    "conversation_id": ws_message.conversation_id,
                    "user_id": user_id
                }
                
                # Broadcast typing to conversation participants
                for uid, connections in active_connections.items():
                    if uid != user_id:
                        for conn in connections.copy():
                            try:
                                await conn.send_text(json.dumps(typing_data))
                            except:
                                connections.discard(conn)
            
            elif ws_message.type == "read":
                # Mark messages as read
                await ChatService.mark_messages_read(user_id, ws_message.conversation_id)
                
                read_data = {
                    "type": "messages_read",
                    "conversation_id": ws_message.conversation_id,
                    "user_id": user_id
                }
                
                # Notify other participants
                for uid, connections in active_connections.items():
                    if uid != user_id:
                        for conn in connections.copy():
                            try:
                                await conn.send_text(json.dumps(read_data))
                            except:
                                connections.discard(conn)
    
    except WebSocketDisconnect:
        pass
    finally:
        # Remove from active connections
        if user_id in active_connections:
            active_connections[user_id].discard(websocket)
            if not active_connections[user_id]:
                del active_connections[user_id]
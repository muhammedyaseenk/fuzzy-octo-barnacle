# app/domains/calls/api_ws.py
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
from app.core.security import verify_token

router = APIRouter()

# Store active call connections
call_connections: Dict[int, WebSocket] = {}
call_rooms: Dict[str, Set[int]] = {}


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


@router.websocket("/ws/call")
async def call_websocket(websocket: WebSocket, token: str):
    """WebSocket endpoint for WebRTC call signalling"""
    await websocket.accept()
    
    # Authenticate user
    user_id = await get_user_from_token(websocket, token)
    if not user_id:
        return
    
    # Add to call connections
    call_connections[user_id] = websocket
    
    try:
        while True:
            # Receive signalling message
            data = await websocket.receive_text()
            message = json.loads(data)
            
            message_type = message.get("type")
            target_user_id = message.get("target_user_id")
            room_id = message.get("room_id")
            
            if message_type == "call_offer":
                # Send call offer to target user
                if target_user_id in call_connections:
                    offer_message = {
                        "type": "incoming_call",
                        "caller_id": user_id,
                        "room_id": room_id,
                        "offer": message.get("offer")
                    }
                    await call_connections[target_user_id].send_text(json.dumps(offer_message))
            
            elif message_type == "call_answer":
                # Send call answer back to caller
                caller_id = message.get("caller_id")
                if caller_id in call_connections:
                    answer_message = {
                        "type": "call_answered",
                        "answerer_id": user_id,
                        "room_id": room_id,
                        "answer": message.get("answer")
                    }
                    await call_connections[caller_id].send_text(json.dumps(answer_message))
                    
                    # Add both users to call room
                    if room_id not in call_rooms:
                        call_rooms[room_id] = set()
                    call_rooms[room_id].add(user_id)
                    call_rooms[room_id].add(caller_id)
            
            elif message_type == "ice_candidate":
                # Forward ICE candidate to other participants in room
                if room_id in call_rooms:
                    ice_message = {
                        "type": "ice_candidate",
                        "sender_id": user_id,
                        "candidate": message.get("candidate")
                    }
                    
                    for participant_id in call_rooms[room_id]:
                        if participant_id != user_id and participant_id in call_connections:
                            await call_connections[participant_id].send_text(json.dumps(ice_message))
            
            elif message_type == "call_reject":
                # Notify caller of rejection
                caller_id = message.get("caller_id")
                if caller_id in call_connections:
                    reject_message = {
                        "type": "call_rejected",
                        "rejector_id": user_id
                    }
                    await call_connections[caller_id].send_text(json.dumps(reject_message))
            
            elif message_type == "call_end":
                # End call and notify participants
                if room_id in call_rooms:
                    end_message = {
                        "type": "call_ended",
                        "ender_id": user_id
                    }
                    
                    for participant_id in call_rooms[room_id]:
                        if participant_id != user_id and participant_id in call_connections:
                            await call_connections[participant_id].send_text(json.dumps(end_message))
                    
                    # Remove room
                    del call_rooms[room_id]
    
    except WebSocketDisconnect:
        pass
    finally:
        # Clean up on disconnect
        if user_id in call_connections:
            del call_connections[user_id]
        
        # Remove from any active call rooms
        for room_id, participants in list(call_rooms.items()):
            if user_id in participants:
                participants.discard(user_id)
                
                # Notify other participants
                disconnect_message = {
                    "type": "participant_disconnected",
                    "user_id": user_id
                }
                
                for participant_id in participants:
                    if participant_id in call_connections:
                        await call_connections[participant_id].send_text(json.dumps(disconnect_message))
                
                # Remove empty rooms
                if not participants:
                    del call_rooms[room_id]
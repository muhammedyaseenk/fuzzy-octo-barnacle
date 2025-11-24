# app/core/socketio_server.py
import socketio
from app.core.config import settings
from app.core.cache import redis_client
import jwt

# Socket.IO server with Redis adapter for horizontal scaling
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=False,
    engineio_logger=False,
    client_manager=socketio.AsyncRedisManager(settings.REDIS_URL),
    max_http_buffer_size=1024 * 100,  # 100KB limit
    ping_timeout=20,
    ping_interval=25
)

# Connection tracking
active_connections = {}

@sio.event
async def connect(sid, environ, auth):
    """Authenticate and track connections"""
    try:
        token = auth.get('token') if auth else None
        if not token:
            return False
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        
        active_connections[sid] = user_id
        await sio.enter_room(sid, f"user_{user_id}")
        await redis_client.sadd(f"online_users", user_id)
        
        return True
    except:
        return False

@sio.event
async def disconnect(sid):
    """Cleanup on disconnect"""
    user_id = active_connections.pop(sid, None)
    if user_id:
        await redis_client.srem(f"online_users", user_id)

@sio.event
async def chat_message(sid, data):
    """Handle chat messages"""
    user_id = active_connections.get(sid)
    if not user_id:
        return
    
    recipient_id = data.get('recipient_id')
    message = data.get('message', '')[:1000]  # Limit message size
    
    await sio.emit('new_message', {
        'sender_id': user_id,
        'message': message,
        'timestamp': data.get('timestamp')
    }, room=f"user_{recipient_id}")

@sio.event
async def typing(sid, data):
    """Handle typing indicators"""
    user_id = active_connections.get(sid)
    if not user_id:
        return
    
    recipient_id = data.get('recipient_id')
    await sio.emit('user_typing', {'user_id': user_id}, room=f"user_{recipient_id}")

@sio.event
async def call_signal(sid, data):
    """WebRTC signaling"""
    user_id = active_connections.get(sid)
    if not user_id:
        return
    
    recipient_id = data.get('recipient_id')
    signal_type = data.get('type')
    signal_data = data.get('data')
    
    await sio.emit('call_signal', {
        'sender_id': user_id,
        'type': signal_type,
        'data': signal_data
    }, room=f"user_{recipient_id}")

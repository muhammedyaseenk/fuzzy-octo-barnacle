# app/core/pagination.py
from typing import Optional, List, Any
from pydantic import BaseModel
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
import base64
import json

class CursorPage(BaseModel):
    """Cursor-based pagination response"""
    items: List[Any]
    next_cursor: Optional[str] = None
    has_more: bool = False

def encode_cursor(data: dict) -> str:
    """Encode cursor data"""
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()

def decode_cursor(cursor: str) -> dict:
    """Decode cursor data"""
    try:
        return json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
    except:
        return {}

async def paginate_cursor(
    session: AsyncSession,
    query,
    cursor: Optional[str] = None,
    limit: int = 20,
    order_by_field: str = "id",
    order_desc: bool = True
):
    """
    Fast cursor-based pagination for infinite scroll
    Uses indexed fields for O(1) seek performance
    """
    limit = min(limit, 100)  # Max 100 items per page
    
    # Decode cursor
    cursor_data = decode_cursor(cursor) if cursor else {}
    last_value = cursor_data.get('last_value')
    last_id = cursor_data.get('last_id')
    
    # Build query with cursor
    if last_value is not None and last_id is not None:
        if order_desc:
            query = query.where(
                or_(
                    getattr(query.column_descriptions[0]['entity'], order_by_field) < last_value,
                    and_(
                        getattr(query.column_descriptions[0]['entity'], order_by_field) == last_value,
                        getattr(query.column_descriptions[0]['entity'], 'id') < last_id
                    )
                )
            )
        else:
            query = query.where(
                or_(
                    getattr(query.column_descriptions[0]['entity'], order_by_field) > last_value,
                    and_(
                        getattr(query.column_descriptions[0]['entity'], order_by_field) == last_value,
                        getattr(query.column_descriptions[0]['entity'], 'id') > last_id
                    )
                )
            )
    
    # Order and limit
    order_field = getattr(query.column_descriptions[0]['entity'], order_by_field)
    if order_desc:
        query = query.order_by(order_field.desc(), query.column_descriptions[0]['entity'].id.desc())
    else:
        query = query.order_by(order_field.asc(), query.column_descriptions[0]['entity'].id.asc())
    
    query = query.limit(limit + 1)
    
    # Execute
    result = await session.execute(query)
    items = result.scalars().all()
    
    # Check if more items exist
    has_more = len(items) > limit
    if has_more:
        items = items[:limit]
    
    # Generate next cursor
    next_cursor = None
    if has_more and items:
        last_item = items[-1]
        next_cursor = encode_cursor({
            'last_value': getattr(last_item, order_by_field),
            'last_id': last_item.id
        })
    
    return CursorPage(items=items, next_cursor=next_cursor, has_more=has_more)

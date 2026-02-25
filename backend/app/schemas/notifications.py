from typing import Dict, Any, Optional
from datetime import datetime
from sqlmodel import SQLModel

class NotificationRead(SQLModel):
    id: int
    type: str
    data: Dict[str, Any]
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None

class UnreadCount(SQLModel):
    unread_count: int

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, JSON
from app.models.user import User

class NotificationChannel(str, Enum):
    EMAIL = "email"
    PUSH = "push"
    IN_APP = "in_app"

class NotificationBase(SQLModel):
    type: str # Could also be enum but often dynamic
    data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    is_read: bool = False
    
class Notification(NotificationBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    read_at: Optional[datetime] = None
    
    user: "User" = Relationship()

class NotificationPreference(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    notification_type: str
    channel: NotificationChannel
    enabled: bool = True
    
    # user relation could be added but id is enough for now

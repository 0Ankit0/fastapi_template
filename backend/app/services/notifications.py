from datetime import datetime
from typing import Any, Dict
from sqlmodel import select
from app.db.session import AsyncSession
from app.models.notifications import Notification
from app.api.v1.endpoints.websockets import manager
import json

class NotificationService:
    @staticmethod
    async def create_and_notify(
        db: AsyncSession,
        user_id: int,
        type: str,
        data: Dict[str, Any]
    ) -> Notification:
        # 1. Create Notification
        notification = Notification(
            user_id=user_id,
            type=type,
            data=data,
            created_at=datetime.utcnow()
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        
        # 2. Broadcast via WebSocket
        # We use the updated ConnectionManager to target the specific user.
        msg = {
            "type": "notification",
            "message": {
                "id": str(notification.id), # serialization safely
                "type": notification.type,
                "data": notification.data,
                "is_read": notification.is_read,
                "created_at": notification.created_at.isoformat()
            }
        }
        await manager.send_to_user(user_id, json.dumps(msg))
        
        return notification

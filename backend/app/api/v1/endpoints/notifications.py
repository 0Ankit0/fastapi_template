from typing import Any, List, Dict
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select, func
from app.api import deps
from app.models.user import User
from app.models.notifications import Notification
from app.schemas.notifications import NotificationRead, UnreadCount
from app.db.session import AsyncSession

router = APIRouter()

@router.get("/", response_model=Dict[str, Any])
async def read_notifications(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    query = select(Notification).where(Notification.user_id == current_user.id).order_by(Notification.created_at.desc())
    count_query = select(func.count()).select_from(Notification).where(Notification.user_id == current_user.id)
    
    total_count = (await db.execute(count_query)).scalar_one()
    
    # Apply limit/offset
    result_query = query.offset(skip).limit(limit)
    result = await db.execute(result_query)
    items = result.scalars().all()
    
    return {
        "results": items,
        "count": total_count,
        "next": None, # Todo: generate next link
        "previous": None
    }

@router.get("/unread_count/", response_model=UnreadCount)
async def unread_count(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    query = select(func.count()).select_from(Notification).where(Notification.user_id == current_user.id, Notification.is_read == False)
    result = await db.execute(query)
    count = result.scalar_one()
    return {"unread_count": count}

@router.post("/{id}/mark_read/", response_model=NotificationRead)
async def mark_read(
    id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    result = await db.execute(select(Notification).where(Notification.id == id, Notification.user_id == current_user.id))
    notification = result.scalars().first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return notification

@router.post("/mark_all_read/")
async def mark_all_read(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    from sqlmodel import update
    stmt = (
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read == False)
        .values(is_read=True, read_at=datetime.utcnow())
    )
    await db.execute(stmt)
    await db.commit()
    return {"message": "All notifications marked as read"}

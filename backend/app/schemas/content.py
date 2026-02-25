from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlmodel import SQLModel
from app.models.content import ContentItemBase, PageBase, DocumentBase

class ContentItemCreate(ContentItemBase):
    pass

class ContentItemRead(ContentItemBase):
    id: int
    created_at: datetime
    updated_at: datetime

class PageCreate(PageBase):
    pass

class PageRead(PageBase):
    id: int
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None

class PageList(SQLModel):
    id: int
    title: str
    slug: str
    is_published: bool
    # Omit content for list view

class DocumentCreate(SQLModel):
    title: str

class DocumentRead(DocumentBase):
    id: int
    user_id: int
    file_path: str
    thumbnail_path: Optional[str]
    created_at: datetime
    updated_at: datetime

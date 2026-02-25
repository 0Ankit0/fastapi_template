from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, JSON, Text
from app.models.user import User

class ContentItemBase(SQLModel):
    external_id: str = Field(unique=True, index=True)
    content_type: str = Field(index=True)
    slug: str = Field(index=True)
    fields: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    is_published: bool = Field(default=True, index=True)

class ContentItem(ContentItemBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})

class PageBase(SQLModel):
    slug: str = Field(unique=True, index=True)
    title: str
    content: str = Field(sa_column=Column(Text))
    meta_description: Optional[str] = None
    is_published: bool = True

class Page(PageBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})
    published_at: Optional[datetime] = None

class DocumentBase(SQLModel):
    title: str
    file_type: Optional[str] = None
    file_size: int = 0
    is_processed: bool = False
    extracted_text: Optional[str] = Field(default=None, sa_column=Column(Text))

class Document(DocumentBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    file_path: str # Store path to file on disk/s3
    thumbnail_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})
    
    user: "User" = Relationship()

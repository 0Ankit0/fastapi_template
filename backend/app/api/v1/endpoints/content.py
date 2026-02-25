from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import select
from app.api import deps
from app.models.user import User
from app.models.content import ContentItem, Page, Document
from app.schemas.content import (
    ContentItemRead, ContentItemCreate, 
    PageRead, PageCreate, PageList,
    DocumentRead, DocumentCreate
)
from app.db.session import AsyncSession
import shutil
import os
import uuid

router = APIRouter()

from app.services.content_sync import ContentSyncService
from fastapi import BackgroundTasks

@router.post("/sync/")
async def sync_content(background_tasks: BackgroundTasks):
    # Retrieve content from external CMS
    # Use background task to avoid blocking
    background_tasks.add_task(ContentSyncService.sync_content)
    return {"message": "Sync started"}

@router.post("/sitemap/")
async def generate_sitemap(background_tasks: BackgroundTasks):
    background_tasks.add_task(ContentSyncService.generate_sitemap)
    return {"message": "Sitemap generation started"}

# --- Content Items ---

@router.get("/", response_model=List[ContentItemRead])
async def read_content_items(
    db: AsyncSession = Depends(deps.get_db),
    content_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    query = select(ContentItem).where(ContentItem.is_published == True)
    if content_type:
        query = query.where(ContentItem.content_type == content_type)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/items/{slug}", response_model=ContentItemRead)
async def read_content_item(
    slug: str,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    result = await db.execute(select(ContentItem).where(ContentItem.slug == slug))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Content item not found")
    return item

# --- Pages ---

@router.get("/pages/", response_model=List[PageList])
async def read_pages(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    # Public can see published
    query = select(Page).where(Page.is_published == True).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/pages/by-slug/{slug}", response_model=PageRead)
async def read_page_by_slug(
    slug: str,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    result = await db.execute(select(Page).where(Page.slug == slug, Page.is_published == True))
    page = result.scalars().first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return page

@router.post("/pages/", response_model=PageRead)
async def create_page(
    page_in: PageCreate,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    if not current_user.is_superuser: # Assuming simple permissions
        raise HTTPException(status_code=400, detail="Not enough permissions")
    
    page = Page(**page_in.dict())
    db.add(page)
    await db.commit()
    await db.refresh(page)
    return page

# --- Documents ---

@router.get("/documents/", response_model=List[DocumentRead])
async def read_documents(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    query = select(Document).where(Document.user_id == current_user.id).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/documents/", response_model=DocumentRead)
async def create_document(
    title: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    # Basic local file storage
    upload_dir = "uploads/documents"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_ext = file.filename.split(".")[-1] if "." in file.filename else ""
    filename = f"{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(upload_dir, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    db_obj = Document(
        title=title,
        user_id=current_user.id,
        file_path=file_path,
        file_type=file_ext,
        file_size=0, # Need to calculate size
        is_processed=False
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get download URL/file for document.
    """
    result = await db.execute(select(Document).where(Document.id == document_id, Document.user_id == current_user.id))
    document = result.scalars().first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # In a real app we might return a signed URL (S3) or stream the file.
    # For local, we can return the path or specific static URL.
    # Assuming we serve 'uploads' statically or using FileResponse
    from fastapi.responses import FileResponse
    
    if not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="File not found on server")
        
    return FileResponse(path=document.file_path, filename=f"{document.title}.{document.file_type}", media_type="application/octet-stream")

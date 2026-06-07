from core.config import settings

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

if not settings.DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the environment variables")

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQL_ECHO,
    future=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

async def get_db():
    """
    Dependency that provides a database session to the path operation functions.
    It ensures that the session is properly closed after use.
    """
    async with AsyncSessionLocal() as session:
        yield session
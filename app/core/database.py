from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

engine = create_async_engine(
    settings.async_database_uri,
    echo=True,
    future=True,
    connect_args={"check_same_thread": False} if "sqlite" in settings.async_database_uri else {}
)

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)

async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        yield session

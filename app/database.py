from app.models.base import Base
from app.config import POSTGRES_URL
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(POSTGRES_URL, echo=True)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

async def create_schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS wiki_documents (
                    id TEXT PRIMARY KEY,
                    rel_path TEXT UNIQUE NOT NULL,
                    title TEXT,
                    content TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_wiki_documents_updated_at
                ON wiki_documents(updated_at);
                """
            )
        )

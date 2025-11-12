from sqlalchemy import select, desc
from app.models.sync_log import SyncLog
from sqlalchemy.ext.asyncio import AsyncSession

async def get_latest_sync_log(session: AsyncSession):
    """取得最新一筆同步紀錄"""
    result = await session.execute(
        select(SyncLog).order_by(desc(SyncLog.finished_at)).limit(1)
    )
    return result.scalar_one_or_none()

async def get_all_sync_logs(session: AsyncSession):
    """取得所有同步紀錄"""
    result = await session.execute(
        select(SyncLog).order_by(desc(SyncLog.finished_at))
    )
    return result.scalars().all()

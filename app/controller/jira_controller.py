from http.client import HTTPException
import app
from app.database import get_session
from app.repository.jiraRepository import JiraRepository
from app.services.jira_service import JiraService
from app.Programs.Chroma import sync_chroma_from_db
from app.services.sync_log_service import get_latest_sync_log
from fastapi import APIRouter,Depends
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(prefix="/jira", tags=["jira"])


@router.post("/sync")
async def sync_jira(session: AsyncSession = Depends(get_session)):
    repo = JiraRepository(session)
    service = JiraService(repo, session)
    count = await service.sync_filtered_project()
    chroma_synced = await sync_chroma_from_db()
    return {"synced": count, "chroma_synced": chroma_synced}


@router.post("/synclog")
async def sync_jira_log(session:AsyncSession = Depends(get_session)):
    log = await get_latest_sync_log(session)
    if not log:
        return {"message": "No sync logs found."}
    
    return {
        "id": log.id,
        "status": log.status,
        "synced_count": log.synced_count,
        "finished_at": log.finished_at,
        "error_message": log.error_message,
    }

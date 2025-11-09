from http.client import HTTPException
import app
from app.database import get_session
from app.repository.jiraRepository import JiraRepository
from app.services.jira_service import JiraService
from fastapi import APIRouter,Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/jira", tags=["jira"])


@router.post("/sync")
async def sync_jira(session: AsyncSession = Depends(get_session)):
    repo = JiraRepository(session)
    service = JiraService(repo, session)
    count = await service.sync_filtered_project()
    return {"synced": count}
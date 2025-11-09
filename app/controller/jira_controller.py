from http.client import HTTPException
import app
from app.database import create_schema, get_session
from app.repository.jiraRepository import JiraRepository
from app.services.db_service import select_all_issues
from app.services.jira_service import JiraService, get_jira_client
from fastapi import APIRouter,Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/jira", tags=["jira"])


@router.put("/")
async def fetch_jira_issues():
    """
    Fetches issues from Jira and returns the count.
    """
    try:
        #await ingest_jira_data()
        return {"status": "success", "message": "Jira issues ingested successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest Jira issues: {str(e)}")

@router.put("/update")
async def update_jira_issues():
    try:
        #await update_jira_data()
        return {"status": "success", "message": "Jira issues updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update Jira issues: {str(e)}")
    
@router.put("/get_jira_client")
async def jira_client():
    try:
        await get_jira_client()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update Jira issues: {str(e)}")

@router.post("/sync")
async def sync_jira(session: AsyncSession = Depends(get_session)):
    repo = JiraRepository(session)
    service = JiraService(repo)
    count = await service.sync_filtered_project()
    return {"synced": count}
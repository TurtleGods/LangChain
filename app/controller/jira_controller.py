from http.client import HTTPException
from app.services.db_service import select_all_issues
from app.services.ingest_service import ingest_jira_data
from fastapi import APIRouter

router = APIRouter(prefix="/jira", tags=["jira"])

@router.get("/")
async def fetch_jira_issues():
    """
    Fetches issues from Jira and returns the count.
    """
    try:
        await ingest_jira_data()
        return {"status": "success", "message": "Jira issues ingested successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest Jira issues: {str(e)}")

@router.get("/jira/show")
async def show_jira_issues():
    """
    Fetches and displays all Jira issues from the database.
    """
    try:
        await select_all_issues()
        return {"status": "success", "message": "Jira issues displayed successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to display Jira issues: {str(e)}")
    
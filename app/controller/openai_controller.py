from fastapi import APIRouter, Depends
from app.services.db_service import select_all_issues

router = APIRouter(prefix="/googleAI", tags=["googleAI"])

@router.get("/issues")
async def list_issues():
    await select_all_issues()

from openaiLogs import OpenaiLogs
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

async def save_openai_log(
    session: AsyncSession,
    user_id: str,
    question: str,
    answer: str,
    intent: str,
    issue_key: str
):
    log = OpenaiLogs(
        user_id=user_id,
        question=question,
        answer=answer,
        intent=intent,
        issue_key=issue_key
    )
    session.add(log)
    await session.commit() 

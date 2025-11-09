from typing import Iterable, Optional, List
from app.models.jira_issue import JiraIssue
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class JiraRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_key(self, key: str) -> Optional[JiraIssue]:
        result = await self.session.execute(
            select(JiraIssue).where(JiraIssue.key == key)
        )
        return result.scalars().first()

    async def upsert(self, issue: JiraIssue) -> JiraIssue:
        existing = await self.get_by_key(issue.key)
        if existing:
            
            if issue.updated and existing.last_jira_updated == issue.updated:
                return None #沒有異動不用更新
            # 更新欄位
            existing.summary = issue.summary
            existing.description = issue.description
            existing.status = issue.status
            existing.assignee = issue.assignee
            existing.created = issue.created
            existing.updated = issue.updated
            existing.comment = issue.comment
            existing.data = issue.data
            
            existing.last_jira_updated = issue.updated
            existing.last_sync = issue.updated
            
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        
        issue.last_jira_updated = issue.updated
        issue.last_sync = issue.updated     
        self.session.add(issue)
        await self.session.commit()
        await self.session.refresh(issue)
        return issue

    async def upsert_many(self, issues: Iterable[JiraIssue]):
        count = 0
        for issue in issues:
            if await self.upsert(issue):
                count += 1
        return count

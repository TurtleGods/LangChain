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
            # 更新欄位
            existing.summary = issue.summary
            existing.description = issue.description
            existing.status = issue.status
            existing.assignee = issue.assignee
            existing.created = issue.created
            existing.updated = issue.updated
            existing.comment = issue.comment
            existing.data = issue.data
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        else:
            self.session.add(issue)
            await self.session.commit()
            await self.session.refresh(issue)
            return issue

    async def upsert_many(self, issues: Iterable[JiraIssue]) -> List[JiraIssue]:
        saved = []
        for i in issues:
            saved.append(await self.upsert(i))
        return saved

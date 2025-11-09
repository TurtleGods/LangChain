from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from app.config import POSTGRES_URL

import json
from datetime import datetime 
engine = create_async_engine(POSTGRES_URL)
Base = declarative_base()

async def load_jira_issues():
    print("Loading jira issues from DB")
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT data FROM jira_issues"))
        rows = result.fetchall()

        issues = []
        for row in rows:
            # row[0] 是 JSONB
            issue = row[0]
            if isinstance(issue, str):
                issue = json.loads(issue)
            issues.append(issue)

        print(f"✅ Loaded {len(issues)} issues from DB")
        return issues

async def get_issue_by_key(issue_key: str):
    print(f"Fetching issue {issue_key} from DB")
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT data FROM jira_issues WHERE key = :key"),
            {"key": issue_key}
        )
        row = result.fetchone()
        if row:
            return row[0]
        return None
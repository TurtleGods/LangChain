from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from app.config import POSTGRES_URL

import json
from datetime import datetime 
engine = create_async_engine(POSTGRES_URL)
Base = declarative_base()

async def seed_data():
    # 1. Read JSON file
    with open("app/seed/seed.json", "r", encoding="utf-8") as f:
        issues = json.load(f)
    await insert_issues_json(issues)
    
async def create_schema_and_table():
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS jira_issues (
                id SERIAL PRIMARY KEY,
                key TEXT,
                summary TEXT,
                description TEXT,
                status TEXT,
                assignee TEXT,
                created TIMESTAMPTZ,
                updated TIMESTAMPTZ,
                data JSONB
            );
        """))

async def select_all_issues():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT id, data FROM jira_issues"))
        rows = result.fetchall()
        for row in rows:
            print(f"ID: {row.id}")
            print(json.dumps(row.data, ensure_ascii=False, indent=2))
        print(f"✅ {len(rows)} rows selected.") 

async def insert_issues_json(issues):
    # Call before inserting
    await create_schema_and_table()
    done_issues = issues
    async with engine.begin() as conn:
        for issue in done_issues:
            json_data = json.dumps(issue, ensure_ascii=False)
            await conn.execute(
                text("""
                    INSERT INTO jira_issues 
                    (key, summary, description, status, assignee, created, updated,data) 
                    VALUES (:key, :summary, :description, :status, :assignee, :created,:updated, :data)
                """),
                {
                    "key": issue["key"],
                    "summary": issue.get("summary"),
                    "description": issue.get("description"),
                    "status": issue.get("status"),
                    "assignee": issue.get("assignee"),
                    "created": datetime.fromisoformat(issue.get("created")),
                    "updated": datetime.fromisoformat(issue.get("updated")),
                    "data": json_data
                }        
            )

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
from sqlalchemy import  text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from app.config import POSTGRES_URL
from langchain_community.utilities import SQLDatabase
import json
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
                issue_key TEXT UNIQUE NOT NULL,
                data JSONB NOT NULL
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
    done_issues = [i for i in issues if i["status"] == "完成"]
    async with engine.begin() as conn:
        for issue in done_issues:
            json_data = json.dumps(issue, ensure_ascii=False)
            await conn.execute(
                text("""
                    INSERT INTO jira_issues 
                    (key, summary, description, status, assignee, created, data) 
                    VALUES (:key, :summary, :description, :status, :assignee, :created, :data)
                """),
                {
                    "key": issue["key"],
                    "summary": issue.get("summary"),
                    "description": issue.get("description"),
                    "status": issue.get("status"),
                    "assignee": issue.get("assignee"),
                    "created": issue.get("created"),
                    "data": json_data
                }        
            )

async def load_jira_issues():
    print("Loading jira issues from DB")
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT data FROM jira_issues"))
        rows = result.fetchall()
        issues = [r[0] if isinstance(r[0], dict) else json.loads(r[0]) for r in rows]

        return issues  # return as Python list of dicts
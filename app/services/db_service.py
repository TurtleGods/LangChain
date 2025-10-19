from sqlalchemy import  text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from app.config import POSTGRES_URL
import json
engine = create_async_engine(POSTGRES_URL)
Base = declarative_base()


async def select_all_issues():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT id, data FROM jira_issues"))
        rows = result.fetchall()
        for row in rows:
            print(f"ID: {row.id}")
            print(json.dumps(row.data, ensure_ascii=False, indent=2))
        print(f"✅ {len(rows)} rows selected.") 

async def insert_issues_json(issues):
    print("insert_issues_json called")
    # Call before inserting
    done_issues = [i for i in issues if i["status"] == "Done"]
    async with engine.begin() as conn:
        for issue in done_issues:
            print(issue["key"])
            json_data = json.dumps(issue, ensure_ascii=False)
            await conn.execute(
                text("""
                        INSERT INTO jira_issues (issue_key, data)
                        VALUES (:key, CAST(:data AS jsonb))
                        ON CONFLICT (issue_key) DO NOTHING;
                    """),
                    {"key": issue["key"], "data": json_data} 
        )


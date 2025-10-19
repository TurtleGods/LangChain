from sqlalchemy import  text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from app.config import POSTGRES_URL
import json
engine = create_async_engine(POSTGRES_URL)
Base = declarative_base()
async def create_table_if_not_exists():
    with engine.begin() as conn:
        await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS jira_issues (
            id SERIAL PRIMARY KEY,
            data JSONB
        );
        """))

async def select_all_issues():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT id, data FROM data.jira_issues"))
        rows = result.fetchall()
        for row in rows:
            print(f"ID: {row.id}")
            print(json.dumps(row.data, ensure_ascii=False, indent=2))
        print(f"✅ {len(rows)} rows selected.") 

async def insert_issues_json(issues):
    print("insert_issues_json called")
    # Call before inserting
    
    if not await check_table_exists():
        await create_jira_issues_table()
    async with engine.begin() as conn:
        for issue in issues:
            print(issue)
            json_data = json.dumps(issue, ensure_ascii=False)
            await conn.execute(
                text("INSERT INTO data.jira_issues (data) VALUES (CAST(:data AS JSONB))"),
                {"data": json_data}
            )

async def check_table_exists():
    async with engine.begin() as conn:
        result = await conn.execute(
            text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'jira_issues'
                );
            """)
        )
        exists = result.scalar()
        print(f"Table jira_issues exists: {exists}")
        return exists

async def create_jira_issues_table():
    async with engine.begin() as conn:
        # Create schema if it doesn't exist
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS data"))
        
        # Create table if it doesn't exist
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS data.jira_issues (
                id SERIAL PRIMARY KEY,
                data JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        print("Table data.jira_issues created/verified")
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from app.config import POSTGRES_URL

import json
from typing import Dict, List

engine = create_async_engine(POSTGRES_URL)
Base = declarative_base()

WIKI_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS wiki_documents (
    id TEXT PRIMARY KEY,
    rel_path TEXT UNIQUE NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    checksum TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
"""

WIKI_TABLE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_wiki_documents_updated_at
ON wiki_documents(updated_at);
"""


async def ensure_wiki_table() -> None:
    async with engine.begin() as conn:
        await conn.execute(text(WIKI_TABLE_SQL))
        await conn.execute(text(WIKI_TABLE_INDEX_SQL))

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


async def get_wiki_checksums() -> Dict[str, str]:
    await ensure_wiki_table()
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT rel_path, checksum FROM wiki_documents"))
        rows = result.fetchall()
        return {row[0]: row[1] for row in rows}


async def upsert_wiki_document(doc: Dict[str, str]) -> None:
    await ensure_wiki_table()
    sql = text(
        """
        INSERT INTO wiki_documents (id, rel_path, title, content, checksum, updated_at)
        VALUES (:id, :rel_path, :title, :content, :checksum, NOW())
        ON CONFLICT (id) DO UPDATE
        SET
            rel_path = EXCLUDED.rel_path,
            title = EXCLUDED.title,
            content = EXCLUDED.content,
            checksum = EXCLUDED.checksum,
            updated_at = NOW()
        """
    )
    async with engine.begin() as conn:
        await conn.execute(sql, doc)


async def load_wiki_documents() -> List[Dict[str, str]]:
    await ensure_wiki_table()
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT id, rel_path, title, content, checksum, updated_at
                FROM wiki_documents
                ORDER BY rel_path
                """
            )
        )
        rows = result.fetchall()
        return [
            {
                "id": row[0],
                "rel_path": row[1],
                "title": row[2],
                "content": row[3],
                "checksum": row[4],
                "updated_at": row[5],
            }
            for row in rows
        ]

from sqlalchemy import create_engine, text
from app.config import POSTGRES_URL

print(POSTGRES_URL)
engine = create_engine(POSTGRES_URL)
def create_table_if_not_exists():
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS jira_issues (
            id SERIAL PRIMARY KEY,
            data JSONB
        );
        """))

def insert_issues_json(issues):
    with engine.begin() as conn:
        for issue in issues:
            conn.execute(
                text("INSERT INTO jira_issues (data) VALUES (:data::jsonb)"),
                {"data": str(issue).replace("'", '"')}  # ensure valid JSON
            )

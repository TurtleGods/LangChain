from app.Programs.Chroma import build_chroma, update_chroma
from app.services.jira_service import fetch_issues, update_issue
from app.services.db_service import insert_issues_json, load_jira_issues

async def ingest_jira_data():
    issues = fetch_issues()
    await insert_issues_json(issues)
    issues = load_jira_issues()
    build_chroma(issues)
    print(f"Ingested {len(issues)} issues.")

async def update_jira_data():
    issues = update_issue()
    await insert_issues_json(issues)
    update_chroma(issues)
    print(f"Updated {len(issues)} issues.")
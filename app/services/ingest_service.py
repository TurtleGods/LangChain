from app.services.jira_service import fetch_issues
from app.services.db_service import insert_issues_json

def ingest_jira_data():
    issues = fetch_issues()
    insert_issues_json(issues)
    print(f"Ingested {len(issues)} issues.")

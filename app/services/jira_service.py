from jira import JIRA
import os 
from app.config import JIRA_URL, JIRA_TOKEN, JIRA_EMAIL

def get_jira_client():
    try:
        return JIRA(
            server=JIRA_URL,
            basic_auth=(JIRA_EMAIL, JIRA_TOKEN)
        )
    except Exception as e:
        print(f"Error connecting to Jira: {e}")
        raise

def fetch_issues(jql="project = MYPROJECT ORDER BY created DESC", limit=50):
    print("Fetching issues from Jira...")
    jira = get_jira_client()
    issues = jira.search_issues(jql, maxResults=limit)
    issue_data = []
    for issue in issues:
        issue_data.append({
            "key": issue.key,
            "summary": issue.fields.summary,
            "description": issue.fields.description,
            "status": issue.fields.status.name,
            "assignee": issue.fields.assignee.displayName if issue.fields.assignee else None,
            "created": issue.fields.created,
        })
    print(f"Fetched {issue_data} issues from Jira.")
    return issue_data
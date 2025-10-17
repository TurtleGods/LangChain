from jira import JIRA
from app.config import JIRA_URL, JIRA_TOKEN, JIRA_EMAIL

def get_jira_client():
    print(JIRA_URL)
    return JIRA(
        server=JIRA_URL,
        basic_auth=(JIRA_EMAIL, JIRA_TOKEN)
    )

def fetch_issues(jql="project = MYPROJECT ORDER BY created DESC", limit=50):
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
    return issue_data
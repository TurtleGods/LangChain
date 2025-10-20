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

def fetch_issues(jql="project = 問題及需求回報區 ORDER BY created DESC", fields=None):
    print("Fetching issues from Jira...")
    jira = get_jira_client()
    if fields is None:
        # pick only the fields you need to reduce payload size
        fields = ["key", "summary", "description", "status", "assignee", "created"]

    # Ask the client to fetch ALL pages in batches by using maxResults=0
    # (the client uses a default batch internally).
    issues_result = jira.enhanced_search_issues(
        jql_str=jql,
        maxResults=0,           # 0/False -> fetch everything in batches
        fields=fields,
        json_result=False,      # returns a ResultList of Issue resources
        use_post=True           # optional: use POST if your JQL is long
    )

    # issues_result is an iterable (ResultList) of Issue resources.
    issues = []
    for issue in issues_result:
        issues.append({
            "key": issue.key,
            "summary": getattr(issue.fields, "summary", None),
            "description": getattr(issue.fields, "description", None),
            "status": getattr(issue.fields.status, "name", None) if issue.fields and getattr(issue.fields, "status", None) else None,
            "assignee": getattr(issue.fields.assignee, "displayName", None) if issue.fields and getattr(issue.fields, "assignee", None) else None,
            "created": getattr(issue.fields, "created", None),
        })

    return issues

def fetch_all_issues(jira, jql, batch_size=100):
    start_at = 0
    all_issues = []

    while True:
        batch = jira.search_issues(
            jql,
            startAt=start_at,
            maxResults=batch_size
        )
        if not batch:
            break

        all_issues.extend(batch)
        start_at += len(batch)

        print(f"Fetched {len(all_issues)} issues so far...")

        if len(batch) < batch_size:
            break  # no more issues

    return all_issues
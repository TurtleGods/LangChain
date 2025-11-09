from app.repository.jiraRepository import JiraRepository
from jira import JIRA
from app.config import JIRA_URL, JIRA_TOKEN, JIRA_EMAIL
from app.models.jira_issue import JiraIssue

def get_jira_client():
    jira = JIRA(
        server=JIRA_URL,
        basic_auth=(JIRA_EMAIL, JIRA_TOKEN)
    )
    return jira

def issue_list_to_dict(issues, jira):
    """Convert Jira Issue objects → pure dict, including comments."""
    result = []

    for issue in issues:
        fields = issue.raw.get("fields", {})

        comments = []
        if "comment" in fields and isinstance(fields["comment"], dict):
            items = fields["comment"].get("comments", [])
            for c in items:
                comments.append({
                    "author": c["author"]["displayName"],
                    "created": c["created"],
                    "body": c["body"]
                })

        result.append({
            "key": issue.key,
            "summary": fields.get("summary"),
            "description": fields.get("description"),
            "status": fields.get("status", {}).get("name"),
            "assignee": fields.get("assignee", {}).get("displayName")
                        if fields.get("assignee") else None,
            "created": fields.get("created"),
            "updated": fields.get("updated"),
            "comments": comments,
            "raw": issue.raw,              # 如果你要完整 JSON
        })

    return result


async def fetch_jira_issues(jql=None, fields=None):
    print("Fetching issues from Jira...")

    jira = get_jira_client()

    if jql is None:
        jql = 'project = "問題及需求回報區" ORDER BY created DESC'

    if fields is None:
        fields = [
            "key", "summary", "description",
            "status", "assignee",
            "created", "updated", "comment"
        ]

    issues_result = jira.enhanced_search_issues(
        jql_str=jql,
        maxResults=0,           # fetch ALL pages automatically
        fields=fields,
        json_result=False,
        use_post=True
    )

    issues = issue_list_to_dict(issues_result, jira)
    return issues
class JiraService:
    def __init__(self, repo: JiraRepository):
        self.repo = repo

    async def sync_filtered_project(self):
        issues_raw = await fetch_jira_issues(
            jql='project = "問題及需求回報區" ORDER BY created DESC'
        )

        mapped = []
        for raw in issues_raw:
            issue = JiraIssue(
                key=raw["key"],
                summary=raw["summary"],
                description=raw["description"],
                status=raw["status"],
                assignee=raw["assignee"],
                created=raw["created"],
                updated=raw["updated"],
                data=raw,                # ← 存完整 JSON
            )
            mapped.append(issue)

        saved = await self.repo.upsert_many(mapped)
        return len(saved)

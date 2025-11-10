from datetime import datetime
from app.repository.jiraRepository import JiraRepository
from jira import JIRA
from app.config import JIRA_URL, JIRA_TOKEN, JIRA_EMAIL
from app.models.jira_issue import JiraIssue
from dateutil import parser
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sync_log import SyncLog

def _parse_ts(val):
    if not val:
        return None
    dt = parser.parse(val)
    return dt.replace(tzinfo=None)

def get_jira_client():
    jira = JIRA(
        server=JIRA_URL,
        basic_auth=(JIRA_EMAIL, JIRA_TOKEN)
    )
    return jira


def issue_list_to_dict(issues):
    result = []
    for issue in issues:
        fields = issue.raw.get("fields", {})
        comments = []
        if "comment" in fields:
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
            "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
            "created": fields.get("created"),
            "updated": fields.get("updated"),
            "comments": comments
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
        maxResults=0,
        fields=fields,
        json_result=False,
        use_post=True
    )

    issues = issue_list_to_dict(issues_result)
    return issues


class JiraService:
    def __init__(self, repo: JiraRepository, session: AsyncSession):
        self.repo = repo
        self.session = session
    async def sync_filtered_project(self):
        
        log = SyncLog(started_at=datetime.now(), status="running")
        self.session.add(log)
        await self.session.commit()
        try:
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
                    created=_parse_ts(raw["created"]),
                    updated=_parse_ts(raw["updated"]),
                    comment=raw["comments"],   # ✅ 放 comment JSONB
                    data=raw,                  # ✅ 放 trimmed JSON
                )
                mapped.append(issue)

            count = await self.repo.upsert_many(mapped) 
            log.status = "success"
            log.synced_count = count
            log.finished_at = datetime.now()
            await self.session.commit()
            return count
        except Exception as ex:
            log.status = "fail"
            log.error_message = str(ex)
            log.finished_at = datetime.now()
            await self.session.commit()
            raise ex

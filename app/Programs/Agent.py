import re
from enum import Enum

from langchain_core.prompts.chat import PromptTemplate
from langchain_openai import ChatOpenAI

from app.config import OPENAI_API_KEY


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=OPENAI_API_KEY)
intent_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    max_tokens=5,
    openai_api_key=OPENAI_API_KEY,
)


class QueryIntent(str, Enum):
    DETAIL = "detail"
    SIMILARITY = "similarity"
    FILTER = "filter"
    LIST = "list"
    WIKI = "wiki"
    DEFAULT = "default"


ISSUE_KEY_RE = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")
WIKI_HINTS = ("wiki", "文件", "知識庫", "頁面", "章節", "規範", "sop", "教學", "手冊")

INTENT_PROMPT = PromptTemplate.from_template(
    """
你是查詢意圖分類器。只輸出一個標籤，不要任何解釋。
可選標籤: detail, similarity, filter, list, wiki, default

判斷規則:
- detail: 詢問單一 issue 細節
- similarity: 找與某 issue 相似的 issue
- filter: 依條件篩選 issue
- list: 列出 issue 清單
- wiki: 詢問 wiki/文件內容、頁面、章節、規範
- default: 無法明確判斷

問題: {question}
只輸出標籤:
""".strip()
)

ISSUE_PROMPT = PromptTemplate.from_template(
    """
請從以下問題中擷取 Jira Issue Key。
只輸出 key，例如 YTHG-830。
若沒有，輸出 none。

問題: {question}
""".strip()
)


def get_llm():
    return llm


async def classify_query_intent(question: str) -> QueryIntent:
    q = (question or "").strip()
    q_lower = q.lower()

    # Fast path: no LLM call.
    if any(h in q_lower for h in WIKI_HINTS):
        return QueryIntent.WIKI

    if ISSUE_KEY_RE.search(q):
        if any(k in q_lower for k in ("相似", "similar", "similarity")):
            return QueryIntent.SIMILARITY
        if any(k in q_lower for k in ("細節", "詳情", "detail", "狀態", "內容")):
            return QueryIntent.DETAIL

    chain = INTENT_PROMPT | intent_llm
    resp = await chain.ainvoke({"question": q})
    label = (getattr(resp, "content", "") or "").strip().lower()

    if label in QueryIntent._value2member_map_:
        return QueryIntent(label)
    return QueryIntent.DEFAULT


async def classify_issue(question: str):
    q = (question or "").strip()
    m = ISSUE_KEY_RE.search(q)
    if m:
        return m.group(0)

    chain = ISSUE_PROMPT | intent_llm
    resp = await chain.ainvoke({"question": q})
    content = (getattr(resp, "content", "") or "").strip()

    m = ISSUE_KEY_RE.search(content)
    if m:
        return m.group(0)
    return "none"


def get_system_prompt() -> str:
    prompt = """
        You are a Jira issue assistant. You have access to Jira issues with fields:
        key, summary, description, status.
        response answer in Traditional Chinese.
        Context:
        {context}

        Question:
        {question}
    """
    return prompt

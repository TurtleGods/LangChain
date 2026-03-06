import re
from enum import Enum

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from app.config import OPENAI_API_KEY


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=OPENAI_API_KEY)
intent_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    max_tokens=8,
    openai_api_key=OPENAI_API_KEY,
)


class QueryIntent(str, Enum):
    DETAIL = "detail"
    SIMILARITY = "similarity"
    FILTER = "filter"
    WIKI = "wiki"
    DEFAULT = "default"


ISSUE_KEY_RE = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")

WIKI_HINTS = (
    "wiki", "文件", "知識庫", "頁面", "章節", "規範", "sop", "教學", "手冊"
)

FILTER_HINTS = (
    "符合", "條件", "篩選", "狀態", "assignee", "priority", "標籤", "只要", "排除", "filter"
)

SIMILARITY_HINTS = (
    "相似", "類似", "same as", "similar", "similarity", "像"
)

DETAIL_HINTS = (
    "細節", "詳情", "內容", "進度", "狀態", "detail", "說明", "comment"
)

INTENT_PROMPT = PromptTemplate.from_template(
    """
你是查詢意圖分類器。
只輸出一個標籤，不要解釋。
可選標籤: detail, similarity, filter, wiki, default

規則:
- detail: 單一 issue 的細節
- similarity: 找相似 issue
- filter: 依條件篩選 issue
- wiki: 問 wiki 文件內容
- default: 無法判斷

Question: {question}
Label:
""".strip()
)

ISSUE_PROMPT = PromptTemplate.from_template(
    """
Extract Jira Issue Key from the question.
Return only one key like YTHG-830.
If not found, return none.

Question: {question}
Answer:
""".strip()
)


def get_llm():
    return llm


def _contains_any(text: str, hints: tuple[str, ...]) -> bool:
    return any(h in text for h in hints)


async def classify_query_intent(question: str) -> QueryIntent:
    q = (question or "").strip()
    q_lower = q.lower()
    has_issue_key = ISSUE_KEY_RE.search(q) is not None

    # Rule-first routing for speed and fewer tokens.
    if _contains_any(q_lower, WIKI_HINTS):
        return QueryIntent.WIKI

    if _contains_any(q_lower, FILTER_HINTS):
        return QueryIntent.FILTER

    if _contains_any(q_lower, SIMILARITY_HINTS):
        return QueryIntent.SIMILARITY

    if has_issue_key and _contains_any(q_lower, DETAIL_HINTS):
        return QueryIntent.DETAIL

    # Guardrail: similarity usually needs an anchor (issue key or explicit similarity wording).
    if has_issue_key:
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

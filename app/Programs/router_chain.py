import re
from app.Programs.Agent import get_llm
from app.Programs.Chroma import get_chroma
from app.services.db_service import get_issue_by_key
from langchain.chains import ConversationalRetrievalChain
from langchain_core.prompts import PromptTemplate


default_chain = None
wiki_chain = None
chat_history = []
ISSUE_KEY_RE = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")
JIRA_BROWSE_URL = "https://mayohumancapital.atlassian.net/browse/"


def _link_issue_keys(text: str) -> str:
    if not text:
        return text

    def _replace(match: re.Match) -> str:
        key = match.group(0)
        start = match.start()
        end = match.end()

        # Skip if already inside markdown link label: [YTHG-830](...)
        if start > 0 and end < len(text) and text[start - 1] == "[" and text[end] == "]":
            return key

        # Skip if key already appears as part of /browse/{KEY}
        prefix = text[max(0, start - 8):start]
        if prefix.endswith("/browse/"):
            return key

        return f"[{key}]({JIRA_BROWSE_URL}{key})"

    return ISSUE_KEY_RE.sub(_replace, text)


SIMILARITY_PROMPT = PromptTemplate.from_template(
    """
你是 Jira 相似案例分析助手。
請依據 context 回答，格式固定:
1. 相似案例 (最多 3 筆，依相似度高到低)
2. 每筆包含: Issue Key、Summary、相似原因(1-2句)
3. 最後補一段「差異點」比較
若資訊不足，明確說明不足處。

Context:
{context}

Question:
{question}
""".strip()
)

FILTER_PROMPT = PromptTemplate.from_template(
    """
你是 Jira 條件篩選助手。
請先列出你辨識到的篩選條件，再回傳結果。
格式固定:
1. 條件解析
2. 符合條件的 Issues (key, status, assignee, 符合原因)
3. 不符合原因摘要（若有）
若查無結果，回覆「無符合項目」。

Context:
{context}

Question:
{question}
""".strip()
)

GENERAL_PROMPT = PromptTemplate.from_template(
    """
You are a Jira + Wiki assistant.
You have access to:
1) Jira issues with fields: key, summary, description, status.
2) Wiki documents with metadata: path, title.
When possible, include hyperlinks for each issue key (e.g. [YTHG-830](https://mayohumancapital.atlassian.net/browse/YTHG-830)).
If the answer is from wiki content, mention the wiki path/title as citation.
Respond in Traditional Chinese.

Context:
{context}

Question:
{question}
""".strip()
)


async def issue_detail_chain(issue_key: str):
    issue = await get_issue_by_key(issue_key)
    if not issue:
        return {"answer": f"找不到 Issue: {issue_key}"}

    answer = (
        f"**[{issue_key}](https://mayohumancapital.atlassian.net/browse/{issue_key})**\n"
        f"- Summary: {issue.get('summary')}\n"
        f"- Description: {issue.get('description')}\n"
        f"- Status: {issue.get('status')}\n"
        f"- Assignee: {issue.get('assignee')}\n"
        f"- Created: {issue.get('created')}\n"
        f"- Updated: {issue.get('updated')}\n"
    )
    if issue.get("comments"):
        answer += "\nComments:\n"
        for c in issue["comments"]:
            answer += f"- {c.get('author')} ({c.get('created')}): {c.get('body')}\n"
    return {"answer": answer}


async def similarity_chain(question: str, issue_key: str):
    if issue_key and issue_key.lower() != "none":
        issue = await get_issue_by_key(issue_key)
        if issue:
            question = (
                f"請找與 {issue_key} 最相似的 Jira issues。"
                f"參考內容: {issue.get('summary', '')} {issue.get('description', '')}"
            )
    return default_chain.invoke({"question": question, "issue_key": issue_key or "", "chat_history": chat_history})


async def filter_chain(question: str):
    query_text = f"請依條件篩選 Jira issues: {question}"
    return default_chain.invoke({"question": query_text, "issue_key": "", "chat_history": chat_history})


async def wiki_only_chain(question: str):
    query_text = f"請只根據 wiki 文件回答，並附上 wiki path/title：{question}"
    return wiki_chain.invoke({"question": query_text, "issue_key": "", "chat_history": chat_history})


def _build_chain(llm, retriever, prompt_template: PromptTemplate):
    return ConversationalRetrievalChain.from_llm(
        llm,
        retriever,
        combine_docs_chain_kwargs={"prompt": prompt_template},
        return_source_documents=True,
    )


async def router_chain(question: str, query_type: str, issue_key):
    global chat_history, default_chain, wiki_chain

    llm = get_llm()
    vectordb = await get_chroma()

    default_retriever = vectordb.as_retriever(search_type="similarity", search_kwargs={"k": 8})
    wiki_retriever = vectordb.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 6, "filter": {"source": "wiki"}},
    )

    query_type = (query_type or "").strip().lower()

    if query_type == "similarity":
        default_chain = _build_chain(llm, default_retriever, SIMILARITY_PROMPT)
    elif query_type == "filter":
        default_chain = _build_chain(llm, default_retriever, FILTER_PROMPT)
    else:
        default_chain = _build_chain(llm, default_retriever, GENERAL_PROMPT)

    wiki_chain = _build_chain(llm, wiki_retriever, GENERAL_PROMPT)

    if query_type == "detail":
        result = await issue_detail_chain(issue_key)
    elif query_type == "similarity":
        result = await similarity_chain(question, issue_key)
    elif query_type == "filter":
        result = await filter_chain(question)
    elif query_type == "wiki":
        result = await wiki_only_chain(question)
    else:
        result = await default_chain.ainvoke({"question": question, "issue_key": "", "chat_history": chat_history})

    if isinstance(result, dict):
        output = result.get("answer") or result.get("result") or ""
        return _link_issue_keys(output)
    return _link_issue_keys(str(result))


def get_system_prompt() -> PromptTemplate:
    return GENERAL_PROMPT

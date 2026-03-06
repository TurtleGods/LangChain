from app.Programs.Agent import get_llm
from app.Programs.Chroma import get_chroma
from app.services.db_service import get_issue_by_key
from langchain.chains import ConversationalRetrievalChain
from langchain_core.prompts.chat import PromptTemplate


default_chain = None
wiki_chain = None
chat_history = []


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


async def similarity_chain(issue_key: str):
    issue = await get_issue_by_key(issue_key)
    if not issue:
        return {"answer": f"找不到 Issue: {issue_key}"}

    query_text = (
        "請找出與此 issue 最相似的 Jira 問題，並簡要說明相似原因："
        f"{issue.get('summary', '')} {issue.get('description', '')}"
    )
    return default_chain.invoke({"question": query_text, "issue_key": issue_key, "chat_history": chat_history})


async def filter_chain(question: str):
    query_text = f"請依條件篩選 Jira issues，必要時可參考 comments：{question}"
    return default_chain.invoke({"question": query_text, "issue_key": "", "chat_history": chat_history})


async def list_chain(question: str):
    query_text = f"請列出符合條件的 Jira issues：{question}"
    return default_chain.invoke({"question": query_text, "issue_key": "", "chat_history": chat_history})


async def wiki_only_chain(question: str):
    query_text = f"請只根據 wiki 文件回答，並附上 wiki path/title：{question}"
    return wiki_chain.invoke({"question": query_text, "issue_key": "", "chat_history": chat_history})


async def router_chain(question: str, query_type: str, issue_key):
    global chat_history, default_chain, wiki_chain

    llm = get_llm()
    vectordb = await get_chroma()

    default_retriever = vectordb.as_retriever(search_type="similarity", search_kwargs={"k": 8})
    wiki_retriever = vectordb.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 6, "filter": {"source": "wiki"}},
    )

    default_chain = ConversationalRetrievalChain.from_llm(
        llm,
        default_retriever,
        combine_docs_chain_kwargs={"prompt": get_system_prompt()},
        return_source_documents=True,
    )
    wiki_chain = ConversationalRetrievalChain.from_llm(
        llm,
        wiki_retriever,
        combine_docs_chain_kwargs={"prompt": get_system_prompt()},
        return_source_documents=True,
    )

    query_type = (query_type or "").strip().lower()

    if query_type == "detail":
        result = await issue_detail_chain(issue_key)
    elif query_type == "similarity":
        result = await similarity_chain(issue_key)
    elif query_type == "filter":
        result = await filter_chain(question)
    elif query_type == "list":
        result = await list_chain(question)
    elif query_type == "wiki":
        result = await wiki_only_chain(question)
    else:
        result = await default_chain.ainvoke({"question": question, "issue_key": "", "chat_history": chat_history})

    if isinstance(result, dict):
        return result.get("answer") or result.get("result") or ""
    return str(result)


def get_system_prompt() -> str:
    prompt = """
        You are a Jira + Wiki assistant.
        You have access to:
        1) Jira issues with fields: key, summary, description, status.
        2) Wiki documents with metadata: path, title.
        When possible, include hyperlinks for each issue key (e.g. [YTHG-830](https://mayohumancapital.atlassian.net/browse/YTHG-830)).
        If the answer is from wiki content, mention the wiki path/title as citation.
        response answer in Traditional Chinese.
        Context:
        {context}

        Question:
        {question}
    """
    return PromptTemplate.from_template(prompt)

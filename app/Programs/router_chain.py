import re
from app.Programs.Agent import get_llm
from app.Programs.Chroma import get_chroma
from app.services.db_service import get_issue_by_key
from sqlalchemy import text
from langchain.chains import ConversationalRetrievalChain
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma 
from langchain_core.prompts.chat import(
    PromptTemplate
)
default_chain = None
chat_history=[]
async def issue_detail_chain(issue_key:str):
    issue = await get_issue_by_key(issue_key)
    if not issue:
        return {"answer": f"❌ 沒有找到 {issue_key} 的細節"}
    
    answer = (
        f"**[{issue_key}](https://mayohumancapital.atlassian.net/browse/{issue_key})**\n"
        f"Issue {issue['key']} 細節：\n"
        f"- Summary: {issue.get('summary')}\n"
        f"- Description: {issue.get('description')}\n"
        f"- Status: {issue.get('status')}\n"
        f"- Assignee: {issue.get('assignee')}\n"
        f"- Created: {issue.get('created')}\n"
        f"- Updated: {issue.get('updated')}\n"
    )
    if issue.get("comments"):
        answer += "\n💬 Comments:\n"
        for c in issue["comments"]:
            answer += f"- {c['author']} ({c['created']}): {c['body']}\n"
    return {"answer":answer}

async def similarity_chain(issue_key:str):
    issue = await get_issue_by_key(issue_key)
    if not issue:
        return {"answer": f"❌ 沒找到 {issue_key}"}
    query_text = f"找和這個{issue} Issue 類似的案例: {issue.get('summary')} {issue.get('description')}"
    result = default_chain.invoke({"question": query_text,"issue_key":issue_key, "chat_history": chat_history})
    return result


async def filter_chain(question:str):
    query_text = f"根據jira issues，找出與此問題相關的案例，並確認comment 中是否有解決方法:{question}"
    result = default_chain.invoke({"question": query_text,"issue_key":"",  "chat_history": chat_history})
    return result

async def list_chain(question:str):
    query_text = f"列出所有與以下主題相關的 Jira issues：{question}"
    result = default_chain.invoke({"question": query_text, "issue_key":"", "chat_history": chat_history})
    return result

# --- RouterChain ---
async def router_chain(question: str,query_type:str,issue_key):
    global chat_history,default_chain
    llm = get_llm()
    vectordb =await get_chroma()
    retriever = vectordb.as_retriever(search_type="similarity", search_kwargs={"k": 10})
    print("Load default_chain")
    default_chain = ConversationalRetrievalChain.from_llm(
        llm,
        retriever, 
        combine_docs_chain_kwargs={"prompt": get_system_prompt()},
        return_source_documents=True)

    print(f"👉 Query type detected: {query_type}")

    if query_type == "detail":
        result = await issue_detail_chain(issue_key)
    elif query_type == "similarity":
        result = await similarity_chain(issue_key)
    elif query_type == "filter":
        result = await filter_chain(question)
    elif query_type == "list":
        result = await list_chain(question)
    else:
        result =await default_chain.ainvoke({"question": question,"issue_key":"","chat_history":chat_history})
    if isinstance(result, dict):
        return result.get("answer") or result.get("result") or ""
    return str(result)

def get_system_prompt()-> str:
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

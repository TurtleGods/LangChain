import re
from app.services.db_service import get_issue_by_key
from sqlalchemy import text
from langchain.chains import ConversationalRetrievalChain
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma 

chat_history = []  # list[BaseMessage]
default_chain = None

# --- Router 判斷 ---
def detect_query_type(question: str):
    if re.fullmatch(r"[A-Z]+-\d+", question.strip(), re.IGNORECASE) or "細節" in question or "內容" in question:
        return "detail"
    if "類似" in question and re.search(r"[A-Z]+-\d+", question):
        return "similarity"
    if "comment" in question.lower() or "解決" in question or "處理" in question:
        return "filter"
    if "列出" in question or "所有" in question:
        return "list"
    return "default"

#-- 子 Chain --

async def issue_detail_chain(issue_key:str):
    issue = await get_issue_by_key(issue_key)
    if not issue:
        return f"❌ 沒有找到 {issue_key} 的細節"
    
    answer = (
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
        return  f"❌ 沒找到 {issue_key}"

    query_text = f"找和這個 Issue 類似的案例: {issue.get('summary')} {issue.get('description')}"
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
async def router_chain(question: str, chain):
    global chat_history,default_chain
    default_chain = chain
    if question.strip().lower() in ["reset", "清除對話", "重新開始"]:
        chat_history = []
        return "✅ 對話已清除，請開始新的查詢"
    if len(chat_history) > 20:
        chat_history = []

    query_type = detect_query_type(question)
    print(f"👉 Query type detected: {query_type}")

    if query_type == "detail":
        issue_key = re.search(r"[A-Z]+-\d+", question, re.IGNORECASE).group(0).upper()
        result = await issue_detail_chain(issue_key)
    elif query_type == "similarity":
        issue_key = re.search(r"[A-Z]+-\d+", question, re.IGNORECASE).group(0).upper()
        result = await similarity_chain(issue_key)
    elif query_type == "filter":
        result = await filter_chain(question)
    elif query_type == "list":
        result = await list_chain(question)
    else:
        result = default_chain.invoke({"question": question,"issue_key":"", "chat_history": chat_history})

    chat_history.append((question, result["answer"]))
    return result
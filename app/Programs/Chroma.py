import os
from app.config import GOOGLE_API_KEY, OPENAI_API_KEY
from app.services.db_service import get_issue_by_key, load_jira_issues
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.vectorstores import Chroma
from langchain_core.prompts.chat import(
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate
)
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
from langchain.schema import HumanMessage, AIMessage
import re

# 改為存放 LangChain message 物件（HumanMessage/AIMessage）
chat_history = []  # list[BaseMessage]

async def run_qa(question: str, reset: bool = False):
    global chat_history
    
    if reset:
        chat_history = []

    # LLM
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=OPENAI_API_KEY)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    vectordb = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    if len(vectordb.get()["ids"]) == 0:
        issues = await load_jira_issues()
        vectordb = build_chroma(issues, embeddings)
    retriever = vectordb.as_retriever(search_type="similarity", search_kwargs={"k": 5})
    qa_chain = ConversationalRetrievalChain.from_llm(
        llm, retriever, return_source_documents=True
    )

    # 1️⃣ 精確查詢某個 issue
    issue_key = is_exact_issue_query(question)
    if issue_key:
        issue = await get_issue_by_key(issue_key)
        print(issue)
        if issue:
            answer = (
                f"Issue {issue['key']} 的細節如下：\n"
                f"- Summary: {issue.get('summary')}\n"
                f"- Description: {issue.get('description')}\n"
                f"- Status: {issue.get('status')}\n"
                f"- Assignee: {issue.get('assignee')}\n"
                f"- Created: {issue.get('created')}\n"
            )
            if issue.get("comments"):
                answer += "\n💬 Comments:\n"
                for c in issue["comments"]:
                    answer += f"- {c['author']} ({c['created']}): {c['body']}\n"
            chat_history.append((question, answer))
            return answer
        else:
            return  f"❌ 沒有找到 {issue_key} 的細節"

    # 2️⃣ 找類似案例
    issue_key = extract_issue_key(question)
    if issue_key and "類似" in question:
        issue = await get_issue_by_key(issue_key)
        if issue:
            query_text = f"找和這個 Issue 類似的案例: {issue.get('summary')} {issue.get('description')}"
            result = qa_chain.invoke({"question": query_text, "chat_history": chat_history})
            chat_history.append((question, result["answer"]))
            return result["answer"]

    # 3️⃣ 一般語意檢索
    result = qa_chain.invoke({"question": question, "chat_history": chat_history})
    chat_history.append((question, result["answer"]))

    return result["answer"]

def build_chroma(issues, embeddings):
    texts = []
    metadatas = []
    for issue in issues:
        text = f"Issue {issue['key']}\nSummary: {issue['summary']}\nDescription: {issue['description']}\nStatus: {issue['status']}\nAssignee: {issue['assignee']}"
        if "comments" in issue:
            for c in issue["comments"]:
                text += f"\nComment by {c['author']} at {c['created']}: {c['body']}"
        texts.append(text)
        metadatas.append({"key": issue["key"]})
    
    vectordb = Chroma.from_texts(texts, embeddings, metadatas=metadatas, persist_directory="./chroma_db")
    vectordb.persist()
    print("✅ Chroma vector DB built and persisted.")
    return vectordb


# --- 工具函式 ---
def is_exact_issue_query(question: str) -> str | None:
    print("Checking for exact issue query...")
    match = re.findall(r"[A-Z]+-\d+", question)
    if len(match) == 1:
        keywords = ["細節", "內容", "詳細", "資訊"]
        if any(kw in question for kw in keywords) or question.strip() == match[0]:
            return match[0]
    return None

def extract_issue_key(question: str) -> str | None:
    match = re.findall(r"[A-Z]+-\d+", question)
    return match[0] if match else None



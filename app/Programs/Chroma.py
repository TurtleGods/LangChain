import os
from app.Programs.router_chain import router_chain
from app.config import GOOGLE_API_KEY, OPENAI_API_KEY
from app.services.db_service import get_issue_by_key, load_jira_issues
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_community.vectorstores import Chroma 
from langchain_core.prompts.chat import(
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate
)
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
from langchain.schema import HumanMessage, AIMessage
import re



async def run_qa(question: str):
    # LLM
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=OPENAI_API_KEY)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    vectordb = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    if len(vectordb.get()["ids"]) == 0:
        issues = await load_jira_issues()
        vectordb = build_chroma(issues, embeddings)
    retriever = vectordb.as_retriever(search_type="similarity", search_kwargs={"k": 5})
    default_chain = ConversationalRetrievalChain.from_llm(llm, retriever, return_source_documents=True)
    result = await router_chain(question, default_chain)

    return result

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



import os
from app.config import OPENAI_API_KEY
from app.services.db_service import get_issue_by_key, load_jira_issues
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
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
from tqdm import tqdm
from openai import OpenAI

embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
# LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=OPENAI_API_KEY)
_vectordb =  None

async def run_qa(question: str):
    qa_system_prompt = get_system_prompt()
    prompt = PromptTemplate(
        input_variables=["context", "question","issue_key"],
        template=qa_system_prompt,
    )

    if len(vectordb.get()["ids"]) == 0:
        issues = await load_jira_issues()
        vectordb = build_chroma(issues, embeddings)
    retriever = vectordb.as_retriever(search_type="similarity", search_kwargs={"k": 10})

    default_chain = ConversationalRetrievalChain.from_llm(
        llm,
        retriever, 
        combine_docs_chain_kwargs={"prompt": prompt},
        return_source_documents=True)

    issue_key = (
        re.search(r"[A-Z]+-\d+", question, re.IGNORECASE).group(0).upper()
        if re.search(r"[A-Z]+-\d+", question, re.IGNORECASE)
        else None
        )

    print("Start Operating QA Chain...")
    result = await default_chain.ainvoke({"question": question,"issue_key":issue_key ,"chat_history": []})
    
    if '找不到' in result["answer"]:
        print("⚠️ Fallback to RouterChain")
        result = await router_chain(question, default_chain)
    print(result)
    return result["answer"]

async def get_chroma():
    global _vectordb
    if _vectordb is not None:
        return _vectordb
    _vectordb = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    if len(_vectordb.get()["ids"]) == 0:
        issues = await load_jira_issues()
        _vectordb = build_chroma(issues, embeddings)
    return _vectordb

def build_chroma(issues, embeddings):
    batch_size=50
    texts = []
    metadatas = []
    for issue in issues:
        text = f"Issue {issue['key']}\nSummary: {issue['summary']}\nDescription: {issue['description']}\nStatus: {issue['status']}\nAssignee: {issue['assignee']}"
        if "comments" in issue:
            for c in issue["comments"]:
                text += f"\nComment by {c['author']} at {c['created']}: {c['body']}"
        texts.append(text)
        metadatas.append({"key": issue["key"]})
    
    vectordb = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    print(f"🧠 Building Chroma in batches of {batch_size}...")
    for i in tqdm(range(0, len(texts), batch_size)):
        batch_texts = texts[i:i + batch_size]
        batch_meta = metadatas[i:i + batch_size]
        vectordb.add_texts(batch_texts, metadatas=batch_meta)
    vectordb.persist()
    print("✅ Chroma vector DB built and persisted.")
    return vectordb

async def update_chroma(issues):
    if not issues:
        print("🟢 No new issues to update in Chroma.")
        return

    vectordb = Chroma(persist_directory='./chroma_db', embedding_function=embeddings)

    for issue in issues:
        # 將文字組成一段，方便 embedding
        text_block = (
            f"Issue {issue['key']}\n"
            f"Summary: {issue['summary']}\n"
            f"Description: {issue['description']}\n"
            f"Status: {issue['status']}\n"
            f"Assignee: {issue['assignee']}"
        )

        if "comments" in issue:
            for c in issue["comments"]:
                text_block += f"\nComment by {c['author']} at {c['created']}: {c['body']}"

        # 新增或覆蓋該 issue 的向量資料
        vectordb.add_texts(
            texts=[text_block],
            metadatas=[{"key": issue["key"]}],
            ids=[issue["key"]],
        )

    vectordb.persist()
    print(f"💾 Chroma updated with {len(issues)} new/changed issues.")

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


def get_system_prompt()-> str:
    prompt = """
        You are a Jira issue assistant. You have access to Jira issues with fields:
        key, summary, description, status.
        
        Context:
        {context}

        Question:
        {question}
    """
    return prompt
    

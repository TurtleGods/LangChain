import os
from app.config import GOOGLE_API_KEY, OPENAI_API_KEY
from app.services.db_service import load_jira_issues
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

def search_issue_by_key(vectordb, key):
    # 直接遍歷 vectordb 的 documents 做精確 key 比對，回傳完整 dict 包含 content 與 metadata
    data = vectordb.get()
    documents = data.get("documents", [])    # list of page_content strings
    metadatas = data.get("metadatas", [])    # list of metadata dicts
    matched = []
    for doc_content, meta in zip(documents, metadatas):
        if meta.get("key", "").upper() == key.upper():
            matched.append({"metadata": meta, "content": doc_content})
    return matched

def should_use_exact_lookup(key: str, question: str) -> bool:
    # 根據問題內容判斷是否要用精確 key 查詢
    if not key:
        return False
    q = question.strip()
    if q.upper() == key.upper():
        return True
    # 若問題很短且包含 key，通常是直接查詢該單
    if len(q) <= len(key) + 10:
        return True
    q_lower = q.lower()
    keywords = [
        "status", "summary", "detail", "description", "assignee", "assigned",
        "comment", "comments", "show", "find",
        "查詢", "狀態", "摘要", "描述", "指派", "留言", "詳情"
    ]
    for kw in keywords:
        if kw in q_lower:
            return True
    return False

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


    key = extract_issue_key(question)
    # 若需精確查詢，直接以 metadata + content 回傳，並把對話加入 chat_history（HumanMessage + AIMessage）
    if key and should_use_exact_lookup(key, question):
        exact_docs = search_issue_by_key(vectordb, key)
        if exact_docs:
            # 若有多個結果，將每個 content 與 metadata 合併成可讀回覆
            answers = []
            for item in exact_docs:
                meta = item["metadata"]
                content = item["content"]
                # 你可以更換下面要回傳的欄位，這裡包含整份 document content（含 comments）
                answers.append(
                    f"Issue: {meta.get('key')}\nSummary: {meta.get('summary')}\nStatus: {meta.get('status')}\nAssignee: {meta.get('assignee')}\nCreated: {meta.get('created')}\n\nDetails:\n{content}"
                )
            answer = "\n\n---\n\n".join(answers)

            # 把使用者問題與助理回覆加入全域 chat_history（以 Message 物件）
            chat_history.append(HumanMessage(content=question))
            chat_history.append(AIMessage(content=answer))

            return answer
        else:
            answer = "找不到相關 Jira 單資訊"
            chat_history.append(HumanMessage(content=question))
            chat_history.append(AIMessage(content=answer))
            return answer

    # 如果不用精確查詢，走原本的 RAG 流程
    # Create prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a professional backend engineer skilled in databases and API development.
        Use the following data to answer user questions accurately.
        If the answer is not in the provided context, say explicitly: 找不到相關 Jira 單資訊
        instead of making something up.
        
        Context: {context}"""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}") 
    ])

    # Create ConversationalRetrievalChain
    qa_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectordb.as_retriever(search_kwargs={"k": 5}),
        memory=ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key='answer'
        ),
        chain_type="stuff",
        return_source_documents=True,
        get_chat_history=lambda h: h,
        combine_docs_chain_kwargs={"prompt": prompt}  
    )

    # 傳入 chat_history 讓 MessagesPlaceholder 可以取得之前的對話（必須是 list of Message）
    result = await qa_chain.ainvoke({"question": question, "chat_history": chat_history})
    
    # 將這次的使用者問題與助理回覆加入 chat_history
    # result["answer"] 通常是回覆文字
    chat_history.append(HumanMessage(content=question))
    chat_history.append(AIMessage(content=result.get("answer", "")))

    return result["answer"]

def build_chroma(issues, embeddings):
    """
    Build a Chroma vector database from a list of Jira issue dicts.
    Each issue is turned into a LangChain Document.
    """
    docs = []
    for issue in issues:
        # Extract important fields safely
        key = issue.get("key", "")
        summary = issue.get("summary", "")
        description = issue.get("description", "")
        status = issue.get("status", "")
        assignee = issue.get("assignee", "")
        comments = ""
        if issue.get("comments"):
            comments = "\n".join(
            f"{c.get('author', 'Unknown')} ({c.get('created', '')}): {c.get('body', '')}"
            for c in issue["comments"]
        )

        # Combine text fields into a readable body for embedding
        content = (
            f"Issue: {key}\n"
            f"Status: {status}\n"
            f"Assignee: {assignee}\n"
            f"Summary: {summary}\n"
            f"Description: {description}\n"
            f"Comments:\n{comments}"
        )

        metadata = {
            "key": key,
            "summary": summary,
            "status": status,
            "assignee": assignee,
            "created": issue.get("created", "")
        }

        docs.append(Document(page_content=content, metadata=metadata))
    # Debug: print all keys
    print("All issue keys in DB:", [doc.metadata["key"] for doc in docs])

    # Initialize embeddings
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large") 
    # Create or load Chroma DB
    persist_dir = "./chroma_db"
    os.makedirs(persist_dir, exist_ok=True)

    vectordb = Chroma.from_documents(docs, embedding=embeddings, persist_directory=persist_dir)
    vectordb.persist()
    print(f"✅ Built Chroma vector DB with {len(docs)} documents.")
    return vectordb


def extract_issue_key(question: str):
    match = re.search(r"[A-Z]+-\d+", question, re.IGNORECASE)
    return match.group(0).upper() if match else None

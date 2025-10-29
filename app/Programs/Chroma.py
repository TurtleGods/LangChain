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
        llm,
        retriever,
        return_source_documents=True
    )
    result = qa_chain({"question": question, "chat_history": chat_history})
    chat_history.append((question,result['answer']))
    return result['answer'],result['source_docmnents']

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
    return vectordb


def extract_issue_key(question: str):
    match = re.search(r"[A-Z]+-\d+", question, re.IGNORECASE)
    return match.group(0).upper() if match else None

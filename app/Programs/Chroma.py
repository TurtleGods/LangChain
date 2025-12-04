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
MAX_TEXT_LENGTH = 4000
CHROMA_BATCH_SIZE = 20

def _issue_to_text(issue):
    text = (
        f"Issue {issue['key']}\n"
        f"Summary: {issue['summary']}\n"
        f"Description: {issue['description']}\n"
        f"Status: {issue['status']}\n"
        f"Assignee: {issue['assignee']}"
    )
    if "comments" in issue:
        for c in issue["comments"]:
            text += f"\nComment by {c['author']} at {c['created']}: {c['body']}"
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH] + "\n...[truncated]"
    return text

async def get_chroma():
    global _vectordb
    if _vectordb is not None:
        return _vectordb
    _vectordb = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    if len(_vectordb.get()["ids"]) == 0:
        issues = await load_jira_issues()
        _vectordb = build_chroma(issues)
    return _vectordb

def build_chroma(issues):
    batch_size=CHROMA_BATCH_SIZE
    texts = []
    metadatas = []
    ids = []
    for issue in issues:
        texts.append(_issue_to_text(issue))
        metadatas.append({"key": issue["key"]})
        ids.append(issue["key"])
    
    vectordb = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    print(f"Building Chroma in batches of {batch_size}...")
    for i in tqdm(range(0, len(texts), batch_size)):
        batch_texts = texts[i:i + batch_size]
        batch_meta = metadatas[i:i + batch_size]
        batch_ids = ids[i:i + batch_size]
        vectordb.add_texts(batch_texts, metadatas=batch_meta, ids=batch_ids)
    vectordb.persist()
    print("Chroma vector DB built and persisted.")
    return vectordb

async def update_chroma(issues):
    if not issues:
        print("No new issues to update in Chroma.")
        return

    vectordb = Chroma(persist_directory='./chroma_db', embedding_function=embeddings)

    for issue in issues:
        text_block = _issue_to_text(issue)
        # Replace any previous vectors for this issue key before adding
        issue_id = issue["key"]
        vectordb.delete(ids=[issue_id])
        vectordb.add_texts(
            texts=[text_block],
            metadatas=[{"key": issue_id}],
            ids=[issue_id],
        )

    vectordb.persist()
    print(f"Chroma updated with {len(issues)} new/changed issues.")

async def sync_chroma_from_db():
    issues = await load_jira_issues()
    if not issues:
        print("No issues found to sync into Chroma.")
        return 0

    vectordb = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    existing = vectordb.get()
    existing_ids = existing.get("ids", []) if existing else []
    if existing_ids:
        vectordb.delete(ids=existing_ids)

    texts = [_issue_to_text(issue) for issue in issues]
    metadatas = [{"key": issue["key"]} for issue in issues]
    ids = [issue["key"] for issue in issues]

    batch_size = CHROMA_BATCH_SIZE
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        batch_meta = metadatas[i:i + batch_size]
        batch_ids = ids[i:i + batch_size]
        vectordb.add_texts(batch_texts, metadatas=batch_meta, ids=batch_ids)
    vectordb.persist()
    print(f"Synced {len(ids)} issues into Chroma from DB.")
    return len(ids)

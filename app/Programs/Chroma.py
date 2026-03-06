from typing import Dict, List, Tuple

from app.services.db_service import load_jira_issues, load_wiki_documents
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
_vectordb = None
MAX_TEXT_LENGTH = 4000
CHROMA_BATCH_SIZE = 20
WIKI_CHUNK_SIZE = 1000
WIKI_CHUNK_OVERLAP = 150


def _issue_to_text(issue: Dict) -> str:
    text = (
        f"Issue {issue.get('key', '')}\n"
        f"Summary: {issue.get('summary', '')}\n"
        f"Description: {issue.get('description', '')}\n"
        f"Status: {issue.get('status', '')}\n"
        f"Assignee: {issue.get('assignee', '')}"
    )
    for c in issue.get("comments", []):
        text += f"\nComment by {c.get('author', '')} at {c.get('created', '')}: {c.get('body', '')}"
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH] + "\n...[truncated]"
    return text


def _chunk_text(text: str, chunk_size: int = WIKI_CHUNK_SIZE, overlap: int = WIKI_CHUNK_OVERLAP) -> List[str]:
    if not text:
        return []
    chunks = []
    start = 0
    step = max(1, chunk_size - overlap)
    while start < len(text):
        chunks.append(text[start : start + chunk_size])
        start += step
    return chunks


def _wiki_to_chunks(wiki_doc: Dict) -> List[Tuple[str, str, Dict]]:
    rel_path = wiki_doc["rel_path"]
    title = wiki_doc.get("title") or rel_path
    content = wiki_doc.get("content", "")
    base_text = f"Wiki Title: {title}\nWiki Path: {rel_path}\n\n{content}"
    chunks = _chunk_text(base_text)

    result = []
    for idx, chunk in enumerate(chunks):
        chunk_id = f"wiki:{rel_path}:{idx}"
        metadata = {"source": "wiki", "path": rel_path, "title": title, "chunk_index": idx}
        result.append((chunk_id, chunk, metadata))
    return result


async def get_chroma():
    global _vectordb
    if _vectordb is not None:
        return _vectordb

    _vectordb = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    if len(_vectordb.get()["ids"]) == 0:
        await sync_chroma_from_db()
        _vectordb = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    return _vectordb


async def update_chroma(issues):
    if not issues:
        print("No new issues to update in Chroma.")
        return

    vectordb = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    for issue in issues:
        issue_id = f"jira:{issue['key']}"
        vectordb.delete(ids=[issue_id])
        vectordb.add_texts(
            texts=[_issue_to_text(issue)],
            metadatas=[{"source": "jira", "key": issue["key"]}],
            ids=[issue_id],
        )
    vectordb.persist()
    print(f"Chroma updated with {len(issues)} new/changed issues.")


async def sync_chroma_from_db():
    issues = await load_jira_issues()
    wiki_docs = await load_wiki_documents()

    if not issues and not wiki_docs:
        print("No Jira issues or Wiki docs found to sync into Chroma.")
        return {"jira_synced": 0, "wiki_chunks_synced": 0, "total_synced": 0}

    vectordb = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    existing = vectordb.get()
    existing_ids = existing.get("ids", []) if existing else []
    if existing_ids:
        vectordb.delete(ids=existing_ids)

    texts: List[str] = []
    metadatas: List[Dict] = []
    ids: List[str] = []

    for issue in issues:
        issue_key = issue["key"]
        ids.append(f"jira:{issue_key}")
        texts.append(_issue_to_text(issue))
        metadatas.append({"source": "jira", "key": issue_key})

    wiki_chunk_count = 0
    for wiki_doc in wiki_docs:
        for chunk_id, chunk_text, metadata in _wiki_to_chunks(wiki_doc):
            ids.append(chunk_id)
            texts.append(chunk_text)
            metadatas.append(metadata)
            wiki_chunk_count += 1

    for i in range(0, len(texts), CHROMA_BATCH_SIZE):
        batch_texts = texts[i : i + CHROMA_BATCH_SIZE]
        batch_meta = metadatas[i : i + CHROMA_BATCH_SIZE]
        batch_ids = ids[i : i + CHROMA_BATCH_SIZE]
        vectordb.add_texts(batch_texts, metadatas=batch_meta, ids=batch_ids)
    vectordb.persist()

    print(f"Synced Jira={len(issues)} and WikiChunks={wiki_chunk_count} into Chroma.")
    return {
        "jira_synced": len(issues),
        "wiki_chunks_synced": wiki_chunk_count,
        "total_synced": len(ids),
    }

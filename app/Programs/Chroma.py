from app.config import OPENAI_API_KEY
from app.services.db_service import load_jira_issues, load_wiki_documents
from app.services.wiki_service import sync_wiki_documents
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from tqdm import tqdm

embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=OPENAI_API_KEY)
_vectordb = None
MAX_TEXT_LENGTH = 4000
CHROMA_BATCH_SIZE = 20


def _truncate_text(text: str, max_length: int = MAX_TEXT_LENGTH) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length] + "\n...[truncated]"


def _issue_to_text(issue):
    text = (
        f"Issue {issue.get('key', '')}\n"
        f"Summary: {issue.get('summary', '')}\n"
        f"Description: {issue.get('description', '')}\n"
        f"Status: {issue.get('status', '')}\n"
        f"Assignee: {issue.get('assignee', '')}"
    )
    if "comments" in issue and issue["comments"]:
        for c in issue["comments"]:
            text += (
                f"\nComment by {c.get('author', '')} at {c.get('created', '')}: "
                f"{c.get('body', '')}"
            )
    return _truncate_text(text)


def _wiki_doc_to_text(doc):
    text = (
        f"Wiki Path: {doc.get('rel_path', '')}\n"
        f"Title: {doc.get('title', '')}\n"
        f"Content:\n{doc.get('content', '')}"
    )
    return _truncate_text(text)


def _build_chroma_payload(issues, wiki_documents):
    texts = []
    metadatas = []
    ids = []

    for issue in issues:
        issue_key = issue.get("key", "")
        texts.append(_issue_to_text(issue))
        metadatas.append({"source": "jira", "key": issue_key})
        ids.append(f"jira:{issue_key}")

    for doc in wiki_documents:
        doc_id = doc.get("id") or f"wiki:{doc.get('rel_path', '')}"
        texts.append(_wiki_doc_to_text(doc))
        metadatas.append(
            {
                "source": "wiki",
                "id": doc_id,
                "path": doc.get("rel_path", ""),
                "title": doc.get("title", ""),
            }
        )
        ids.append(doc_id)

    return texts, metadatas, ids


async def get_chroma():
    global _vectordb
    if _vectordb is not None:
        return _vectordb

    _vectordb = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    if len(_vectordb.get().get("ids", [])) == 0:
        issues = await load_jira_issues()
        await sync_wiki_documents()
        wiki_documents = await load_wiki_documents()
        _vectordb = build_chroma(issues, wiki_documents)
    return _vectordb


def build_chroma(issues, wiki_documents):
    texts, metadatas, ids = _build_chroma_payload(issues, wiki_documents)

    vectordb = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    print(f"Building Chroma in batches of {CHROMA_BATCH_SIZE}...")
    for i in tqdm(range(0, len(texts), CHROMA_BATCH_SIZE)):
        batch_texts = texts[i : i + CHROMA_BATCH_SIZE]
        batch_meta = metadatas[i : i + CHROMA_BATCH_SIZE]
        batch_ids = ids[i : i + CHROMA_BATCH_SIZE]
        vectordb.add_texts(batch_texts, metadatas=batch_meta, ids=batch_ids)
    vectordb.persist()
    print("Chroma vector DB built and persisted.")
    return vectordb


async def update_chroma(issues):
    if not issues:
        print("No new issues to update in Chroma.")
        return

    vectordb = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)

    for issue in issues:
        issue_key = issue.get("key", "")
        issue_id = f"jira:{issue_key}"
        text_block = _issue_to_text(issue)
        vectordb.delete(ids=[issue_id])
        vectordb.add_texts(
            texts=[text_block],
            metadatas=[{"source": "jira", "key": issue_key}],
            ids=[issue_id],
        )

    vectordb.persist()
    print(f"Chroma updated with {len(issues)} new/changed issues.")


async def sync_chroma_from_db():
    issues = await load_jira_issues()
    await sync_wiki_documents()
    wiki_documents = await load_wiki_documents()

    if not issues and not wiki_documents:
        print("No Jira issues or wiki documents found to sync into Chroma.")
        return {"jira_vectors": 0, "wiki_vectors": 0, "total_vectors": 0}

    vectordb = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    existing = vectordb.get()
    existing_ids = existing.get("ids", []) if existing else []
    if existing_ids:
        vectordb.delete(ids=existing_ids)

    texts, metadatas, ids = _build_chroma_payload(issues, wiki_documents)

    for i in range(0, len(texts), CHROMA_BATCH_SIZE):
        batch_texts = texts[i : i + CHROMA_BATCH_SIZE]
        batch_meta = metadatas[i : i + CHROMA_BATCH_SIZE]
        batch_ids = ids[i : i + CHROMA_BATCH_SIZE]
        vectordb.add_texts(batch_texts, metadatas=batch_meta, ids=batch_ids)

    vectordb.persist()
    print(
        f"Synced {len(issues)} Jira issues and {len(wiki_documents)} wiki docs "
        "into Chroma from DB."
    )
    return {
        "jira_vectors": len(issues),
        "wiki_vectors": len(wiki_documents),
        "total_vectors": len(ids),
    }

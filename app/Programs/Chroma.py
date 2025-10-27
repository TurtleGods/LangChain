
import os
from app.config import GOOGLE_API_KEY, OPENAI_API_KEY
from app.services.db_service import load_jira_issues
from langchain_openai import ChatOpenAI
from langchain.vectorstores import Chroma
from langchain_core.prompts.chat import(
    ChatPromptTemplate,
    MessagesPlaceholder
)
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
import re


chat_history = []
current_issue_key = None

async def run_qa(question: str, reset: bool = False):
    global chat_history,current_issue_key

    # Reset chat if needed
    if reset:
        chat_history = []
    # Load LLM
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0,openai_api_key=OPENAI_API_KEY)

    # # Load or create embeddings
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

    # # # Load Chroma (if exists)
    vectordb = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)

    # # # If the vectorstore is empty, rebuild it
    if len(vectordb.get()["ids"]) == 0:
        issues =await load_jira_issues()
        vectordb = build_chroma(issues, embeddings)
    # # # Retrieve relevant issues
    retriever = vectordb.as_retriever(search_type="similarity_score_threshold",search_kwargs={'score_threshold': 0.3})
    issue_key = extract_issue_key(question)
    print("Extracted issue key:", issue_key, "Current issue key:", current_issue_key)
    if issue_key and issue_key != current_issue_key:
        # 👉 新的 issue，清空對話記錄
        print("New issue key detected, resetting chat history.")
        chat_history = []
        current_issue_key = issue_key

        relevant_docs = vectordb.similarity_search(
            query=question,
            k=5,
            filter={"key": issue_key}
        )
    else:
        relevant_docs = retriever.get_relevant_documents(question)

    # # # Combine retrieved text
    context = "\n\n".join([doc.page_content for doc in relevant_docs])

    # # System and user prompts
    system_prompt = (
        "You are a professional backend engineer skilled in databases and API development. "
        "Use the following Jira issues data to answer user questions accurately. "
        "If something is unclear or missing, mention it explicitly."
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("history"),
        ("user", "Context:\n{context}\n\nQuestion: {question}")
    ])

    chain = prompt | llm
    result = await chain.ainvoke({
        "question": question,
        "context": context,
        "history": chat_history
        })
    chat_history.append(("user", question))
    chat_history.append(("ai", result.content))
    return result

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

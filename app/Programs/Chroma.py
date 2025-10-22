import asyncio
import json
import os
from app.config import GOOGLE_API_KEY, OPENAI_API_KEY
from app.services.db_service import load_jira_issues, select_all_issues
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain.vectorstores import Chroma
from langchain_core.prompts.chat import(
    ChatPromptTemplate
)
from langchain.schema import Document
from langchain.chains import LLMChain
from langchain_openai import OpenAIEmbeddings


async def run_qa(question: str):
    print("inRun_QA")
    # Load LLM
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0,openai_api_key=OPENAI_API_KEY)

    # # Load or create embeddings
    embeddings = OpenAIEmbeddings(model="models/embedding-001")

    # # # Load Chroma (if exists)
    vectordb = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)

    # # # If the vectorstore is empty, rebuild it
    if len(vectordb.get()["ids"]) == 0:
        issues =await load_jira_issues()
        vectordb = build_chroma(issues)
    # # # Retrieve relevant issues
    retriever = vectordb.as_retriever(search_kwargs={"k": 5})
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
        ("user", "Context:\n{context}\n\nQuestion: {question}")
    ])

    chain = LLMChain(llm=llm, prompt=prompt)
    response = chain.run(context=context, question=question)
    return response

def build_chroma(issues):
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
        comments = "\n".join(issue.get("comments", [])) if issue.get("comments") else ""

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
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small") 
    # Create or load Chroma DB
    persist_dir = "./chroma_db"
    os.makedirs(persist_dir, exist_ok=True)

    vectordb = Chroma.from_documents(docs, embedding=embeddings, persist_directory=persist_dir)
    vectordb.persist()
    print(f"✅ Built Chroma vector DB with {len(docs)} documents.")
    return vectordb
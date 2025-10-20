import asyncio
from app.services.db_service import load_jira_issues
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts.chat import(
    ChatPromptTemplate
)
from sqlalchemy.ext.asyncio import create_async_engine
from langchain_core.output_parsers import StrOutputParser


def run_qa():
    # --- LLM & embeddings ---
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    # --- Prepare text documents ---
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    issues_json = load_jira_issues()
    docs = splitter.create_documents(issues_json)

    # --- Create retriever (vectorstore) ---
    vectorstore = Chroma.from_documents(docs, embedding=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

    # --- Create chain ---
    system_prompt = (
        "You are a backend engineer analyzing Jira issues stored in PostgreSQL. "
        "Use the Jira data to answer user questions precisely."
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{question}")
    ])
    chain = prompt | llm | StrOutputParser()

    return chain
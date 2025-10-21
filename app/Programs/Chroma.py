import asyncio
import json
from app.services.db_service import load_jira_issues
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.vectorstores import Chroma
from langchain_core.prompts.chat import(
    ChatPromptTemplate
)
from langchain.schema import Document
from langchain.chains import LLMChain

def run_qa(question: str):
    # Load LLM
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

    # Load or create embeddings
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    # Load Chroma (if exists)
    vectordb = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)

    # If the vectorstore is empty, rebuild it
    if len(vectordb.get()["ids"]) == 0:
        issues = load_jira_issues()
        vectordb = build_chroma(issues)

    # Retrieve relevant issues
    retriever = vectordb.as_retriever(search_kwargs={"k": 5})
    relevant_docs = retriever.get_relevant_documents(question)

    # Combine retrieved text
    context = "\n\n".join([doc.page_content for doc in relevant_docs])

    # System and user prompts
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
    # Convert issues into LangChain Document objects
    docs = []
    for issue in issues:
        content = json.dumps(issue, ensure_ascii=False)
        metadata = {"key": issue.get("key"), "summary": issue.get("summary")}
        docs.append(Document(page_content=content, metadata=metadata))

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vectordb = Chroma.from_documents(docs, embedding=embeddings, persist_directory="./chroma_db")
    vectordb.persist()
    return vectordb
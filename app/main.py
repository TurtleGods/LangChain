from app.services.ingest_service import ingest_jira_data
import uvicorn
from app.models import QueryModel
from fastapi import FastAPI, HTTPException
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import GOOGLE_API_KEY
# --- Initialization (Run once on startup) ---

# We assume OPENAI_API_KEY is available in the environment (Docker best practice).
if not GOOGLE_API_KEY:
    # Raise an exception immediately if the key is missing, preventing server startup
    raise EnvironmentError("GOOGLE_API_KEY environment variable not set. Cannot initialize LLM.")

# Initialize FastAPI application
app = FastAPI(
    title="LangChain Containerized API",
    description="A simple, containerized API to run a LangChain chat prompt.",
    version="1.0.0"
)

# Initialize the LLM and Chain globally
try:
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    # Define the chain structure
    system_prompt = (
        "You are an expert containerization specialist and helpful AI assistant. "
        "Your responses are professional, concise, and directly address the user's question."
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{question}")
    ])

    # The runnable chain
    chain = prompt | llm | StrOutputParser()
except Exception as e:
    print(f"Error initializing LangChain components: {e}")
    # If the LLM initialization fails, the service should not start
    raise RuntimeError("Failed to set up LangChain components.")


@app.get("/")
async def root():
    """Simple health check endpoint."""
    print("Fetching Jira issues...")
    #ingest_jira_data()
    return {"status": "ok", "service": "LangChain FastAPI is ready to serve queries at /ask"}

@app.get("/jira")
async def fetch_jira_issues():
    """
    Fetches issues from Jira and returns the count.
    """
    try:
        await ingest_jira_data()
        return {"status": "success", "message": "Jira issues ingested successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest Jira issues: {str(e)}")
    
@app.post("/ask", response_model=QueryModel.QueryResponse)
async def ask_question(query: QueryModel.QueryRequest):
    """
    Processes a natural language question using the LangChain LLM.
    """
    try:
        # Invoke the chain with the user's question
        result = chain.invoke({"question": query.question})
        
        return QueryModel.QueryResponse(
            query=query.question,
            response=result.strip()
        )
    except Exception as e:
        # Catch exceptions during chain invocation (e.g., API errors)
        raise HTTPException(status_code=500, detail=f"LLM chain failed: {e}")

# This block is only for running the file directly outside of the container
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

from http.client import HTTPException
from app.models import QueryModel
from fastapi import APIRouter, Depends
from app.services.db_service import select_all_issues
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

router = APIRouter(prefix="/googleAI", tags=["googleAI"])

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

@router.get("/issues")
async def list_issues():
    await select_all_issues()
    
@router.post("/ask", response_model=QueryModel.QueryResponse)
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
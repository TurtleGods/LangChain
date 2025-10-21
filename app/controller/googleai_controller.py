from http.client import HTTPException
from app.Programs.Agent import create_chain
from app.models import QueryModel
from fastapi import APIRouter
from app.services.db_service import select_all_issues
from app.config import POSTGRES_URL
from langchain_google_genai import ChatGoogleGenerativeAI
router = APIRouter(prefix="/googleAI", tags=["googleAI"])


@router.get("/issues")
async def list_issues():
    await select_all_issues()
    
@router.post("/ask", response_model=QueryModel.QueryResponse)
async def ask_question(query: QueryModel.QueryRequest):
    """
    Processes a natural language question using the LangChain LLM.
    """
    try:
        # toolkit = SQLDatabaseToolkit(db=db, llm=llm)
        # agent_executor = create_sql_agent(
        #     llm=llm,
        #     toolkit=toolkit,
        #     verbose=True
        # )
        # result = agent_executor.run("List all Jira issues where status is 'To Do'")
        # Invoke the chain with the user's question
        #qachain = run_qa()
        result = create_chain("English", "English", query.question)
        #run_qa(query.question)
        return QueryModel.QueryResponse(
            query=query.question,
            response=result.strip()
        )
    except Exception as e:
        # Catch exceptions during chain invocation (e.g., API errors)
        raise HTTPException(status_code=500, detail=f"LLM chain failed: {e}")
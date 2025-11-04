

from app.Programs.Agent import classify_issue, classify_query_intent
from app.Programs.router_chain import router_chain
from app.models import QueryModel
from fastapi import APIRouter,HTTPException
router = APIRouter(prefix="/openAI", tags=["openAI"])


@router.post("/ask", response_model=QueryModel.QueryResponse)
async def ask_question(query: QueryModel.QueryRequest):
    """
    Processes a natural language question using the LangChain LLM.
    """
    try:
        intent = await classify_query_intent(query.question)
        issue_key = await classify_issue(query.question)
        result= await router_chain(query.question,intent, issue_key)
        return QueryModel.QueryResponse(
            senderId="OpenAI",
            senderDisplayName="OpenAI",
            content=result
        )
    except Exception as e:
        # Catch exceptions during chain invocation (e.g., API errors)
        raise HTTPException(status_code=400, error=f"LLM chain failed: {e}")
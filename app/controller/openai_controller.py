from app.models import QueryModel
from app.Programs.Chroma import run_qa
from fastapi import APIRouter,HTTPException
router = APIRouter(prefix="/openAI", tags=["openAI"])


@router.post("/ask", response_model=QueryModel.QueryResponse)
async def ask_question(query: QueryModel.QueryRequest):
    """
    Processes a natural language question using the LangChain LLM.
    """
    try:
        result= await run_qa(query.question)
        return QueryModel.QueryResponse(
            senderId="OpenAI",
            senderDisplayName="OpenAI",
            content=result
        )
    except Exception as e:
        # Catch exceptions during chain invocation (e.g., API errors)
        raise HTTPException(status_code=500, detail=f"LLM chain failed: {e}")
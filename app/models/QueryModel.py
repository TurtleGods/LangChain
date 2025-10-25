from pydantic import BaseModel
# --- API Data Models ---

class QueryRequest(BaseModel):
    """Schema for the incoming request body."""
    question: str
    
class QueryResponse(BaseModel):
    """Schema for the outgoing response body."""
    id: str
    senderId: str
    senderDisplayName: str
    content: str
    response:str
class QueryResponse1(BaseModel):
    response: str
# --- API Endpoints ---
class QueryRequest1(BaseModel):
    input_language: str
    output_language: str
    text: str
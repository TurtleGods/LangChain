from app.controller import jira_controller, openai_controller
from app.database import create_schema
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
# Initialize FastAPI application
app = FastAPI(
    title="LangChain Containerized API",
    description="A simple, containerized API to run a LangChain chat prompt.",
    version="1.0.0"
)
origins = [
    "https://localhost:5001",   # 你的 .NET 前端
    "https://localhost:4200",    # 如果有 Angular Dev server
    "http://localhost:4200",
    "https://localhost:5173",
    "https://localhost:44303"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # 或 ["*"] 在開發環境允許全部
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jira_controller.router)
app.include_router(openai_controller.router)
@app.on_event("startup")
async def on_startup():
    print("Creating schema...")
    await create_schema()
@app.get("/")
async def root():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "LangChain FastAPI is ready to serve queries at /ask"}
    
# This block is only for running the file directly outside of the container
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

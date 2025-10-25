from app.controller import jira_controller, googleai_controller, openai_controller
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
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # 或 ["*"] 在開發環境允許全部
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(googleai_controller.router)
app.include_router(jira_controller.router)
app.include_router(openai_controller.router)

@app.get("/")
async def root():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "LangChain FastAPI is ready to serve queries at /ask"}

@app.get("/seed")
async def seed_database():
    """
    Seeds the database with initial data from the seed JSON file.
    """
    try:
        from app.services.db_service import seed_data
        await seed_data()
        return {"status": "success", "message": "Database seeded successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to seed database: {str(e)}")
    
# This block is only for running the file directly outside of the container
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

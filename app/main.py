from fastapi import FastAPI
from langchain.llms import OpenAI

app = FastAPI()

@app.get("/")
def root():
    llm = OpenAI(model="gpt-3.5-turbo")
    response = llm.invoke("Hello from LangChain in Docker!")
    return {"message": response}

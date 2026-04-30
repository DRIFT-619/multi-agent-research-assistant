from fastapi import FastAPI
from pydantic import BaseModel
import time
from langsmith import traceable

from src.multi_agent_pipeline import get_answer

app = FastAPI(
    title="Multi-Agent Research Assistant",
    description="Hybrid RAG + Graph AI System",
    version="1.0"
)

# Request Schema
class QueryRequest(BaseModel):
    query: str

# Root endpoint
@app.get("/")
def home():
    return {
        "message": "API is running",
        "status": "success"
    }

# Main AI endpoint
@app.post("/ask")
@traceable(name="Multi-Agent Pipeline")
def ask_question(request: QueryRequest):
    query = request.query

    start = time.time()
    result = get_answer(query)
    end = time.time()

    return {
        "query": query,
        "decision": result["decision"],
        "reasoning": result["reasoning"],
        "answer": result["answer"],
        "status": "success",
        "response_time": round(end - start, 2)
    }
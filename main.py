import os
from dotenv import load_dotenv

load_dotenv()  

from graph import graph, vectorstore, DB_PATH, COLLECTION_NAME
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from graph import graph, vectorstore, DB_PATH, COLLECTION_NAME
import uvicorn


# ============= APP SETUP =============
app = FastAPI(title="Jio RAG Support API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============= SCHEMAS =============
class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    answer: str
    status: str = "success"


# ============= ENDPOINTS =============
@app.get("/")
def root():
    return {"message": "Jio RAG Support API is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/stats")
def stats():
    count = len(vectorstore.get().get("ids", []))
    return {
        "total_vectors": count,
        "collection": COLLECTION_NAME,
        "db_path": DB_PATH
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    try:
        result = graph.invoke({"messages": [HumanMessage(content=request.query)]})
        answer = result["messages"][-1].content
        return ChatResponse(answer=answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============= RUN =============
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

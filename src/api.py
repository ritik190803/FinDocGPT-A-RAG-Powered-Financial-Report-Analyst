# src/api.py

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

# Import your working pipeline
from rag_pipeline import FinancialRAGPipeline

# Initialize the application
app = FastAPI(
    title="FinDocGPT Engine", 
    description="RAG-powered API for financial document analysis",
    version="1.0.0"
)

# Advanced Security: Configure CORS to exclusively allow your Angular local development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"], # Standard port for Angular CLI
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

# Load the AI pipeline into memory once when the server starts
print("Booting up RAG Engine...")
rag_engine = FinancialRAGPipeline()

# Define strict Pydantic data models for request/response validation
class ChatRequest(BaseModel):
    question: str

class SourceData(BaseModel):
    company: str
    fiscal_year: str
    page_number: int

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceData]

@app.post("/api/ask", response_model=ChatResponse)
async def ask_question(request: ChatRequest):

    print("=" * 80)
    print("API ENDPOINT HIT")
    print("Question:", request.question)
    print("=" * 80)
    """
    Receives a natural language question, processes it through the local vector DB 
    and Groq LLM, and returns a structured analysis with distinct citations.
    """
    try:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty.")
            
        # Execute the RAG pipeline
        result = rag_engine.query(request.question)
        
        # Deduplicate sources so the frontend doesn't show identical citation tags
        unique_sources = []
        seen = set()
        
        for meta in result["raw_metadata"]:
            identifier = f"{meta['company']}_{meta['fiscal_year']}_{meta['page_number']}"
            if identifier not in seen:
                seen.add(identifier)
                unique_sources.append(
                    SourceData(
                        company=meta['company'],
                        fiscal_year=meta['fiscal_year'],
                        page_number=meta['page_number']
                    )
                )
                
        return ChatResponse(
            answer=result["answer"],
            sources=unique_sources
        )
        
    except Exception as e:
        print(f"API Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error during AI generation.")

if __name__ == "__main__":
    # Runs the server asynchronously on port 8000
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
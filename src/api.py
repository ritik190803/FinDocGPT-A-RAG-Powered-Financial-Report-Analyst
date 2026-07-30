import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# Import working pipeline
from rag_pipeline import FinancialRAGPipeline

# Initialize application
app = FastAPI(
    title="FinDocGPT Engine"
)
frontend_url = os.getenv("FRONTEND_URL", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", frontend_url, "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Booting up RAG Engine...")
rag_engine = FinancialRAGPipeline()

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

    try:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty.")
            
        # Execute RAG pipeline (retrieves top 10 chunks now)
        result = rag_engine.query(request.question)
        
        # Deduplicate sources for UI rendering
        unique_sources = []
        seen = set()
        
        for meta in result["raw_metadata"]:
            identifier = f"{meta['company']}_{meta['fiscal_year']}_{meta['page_number']}"
            if identifier not in seen:
                seen.add(identifier)
                unique_sources.append(
                    SourceData(
                        company=meta['company'],
                        fiscal_year=str(meta['fiscal_year']),
                        page_number=int(meta['page_number'])
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
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
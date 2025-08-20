from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

from ..services.rag import RAGService
from ..config import settings


router = APIRouter(prefix="", tags=["chat"])


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = 6
    namespace: Optional[str] = None
    conversation_history: Optional[List[Dict[str, str]]] = None


class Source(BaseModel):
    id: str
    score: float
    metadata: dict
    drawing_name: Optional[str] = None
    page_number: Optional[int] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]
    confidence: Optional[str] = None  # "high", "medium", "low"
    drawings_referenced: List[str] = []


rag_service: RAGService | None = None


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        global rag_service
        if rag_service is None:
            rag_service = RAGService()
        namespace = req.namespace or settings.pinecone_namespace
        answer, sources = rag_service.answer_query(
            query=req.query, 
            top_k=req.top_k, 
            namespace=namespace,
            conversation_history=req.conversation_history
        )
        
        # Extract drawing names and assess confidence
        drawings_referenced = list(set([
            s["metadata"].get("source", "").replace(".pdf", "") 
            for s in sources if s["metadata"].get("source")
        ]))
        
        # Simple confidence scoring based on source scores and count
        avg_score = sum(s["score"] for s in sources) / len(sources) if sources else 0
        confidence = "high" if avg_score < 0.3 and len(sources) >= 3 else "medium" if avg_score < 0.5 else "low"
        
        enhanced_sources = []
        for s in sources:
            enhanced_sources.append(Source(
                id=s["id"], 
                score=s["score"], 
                metadata=s["metadata"],
                drawing_name=s["metadata"].get("source", "").replace(".pdf", ""),
                page_number=int(s["metadata"].get("page", 0)) if s["metadata"].get("page") is not None else None
            ))
        
        return ChatResponse(
            answer=answer,
            sources=enhanced_sources,
            confidence=confidence,
            drawings_referenced=drawings_referenced
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


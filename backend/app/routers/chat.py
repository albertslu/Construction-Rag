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


class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class Source(BaseModel):
    id: str
    score: float
    metadata: dict
    drawing_name: Optional[str] = None
    page_number: Optional[int] = None
    bbox: Optional[BoundingBox] = None
    text_content: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]
    confidence: Optional[str] = None  # "high", "medium", "low"
    drawings_referenced: List[str] = []


rag_service: Optional[RAGService] = None


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        global rag_service
        if rag_service is None:
            rag_service = RAGService()
        namespace = req.namespace or settings.pinecone_namespace
        answer, sources, confidence_override = rag_service.answer_query(
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
        
        # Use construction validator confidence override if provided, otherwise use simple scoring
        if confidence_override:
            confidence = confidence_override
        else:
            avg_score = sum(s["score"] for s in sources) / len(sources) if sources else 0
            confidence = "high" if avg_score < 0.3 and len(sources) >= 3 else "medium" if avg_score < 0.5 else "low"
        
        enhanced_sources = []
        for s in sources:
            # Parse bbox coordinates if available
            bbox = None
            bbox_str = s["metadata"].get("bbox")
            if bbox_str and isinstance(bbox_str, str):
                try:
                    coords = [float(x) for x in bbox_str.split(",")]
                    if len(coords) == 4:
                        bbox = BoundingBox(x0=coords[0], y0=coords[1], x1=coords[2], y1=coords[3])
                except (ValueError, IndexError):
                    bbox = None
            
            enhanced_sources.append(Source(
                id=s["id"], 
                score=s["score"], 
                metadata=s["metadata"],
                drawing_name=s["metadata"].get("source", "").replace(".pdf", ""),
                page_number=int(s["metadata"].get("page", 0)) if s["metadata"].get("page") is not None else None,
                bbox=bbox,
                text_content=s.get("text_content")
            ))
        
        return ChatResponse(
            answer=answer,
            sources=enhanced_sources,
            confidence=confidence,
            drawings_referenced=drawings_referenced
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


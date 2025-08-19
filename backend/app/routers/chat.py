from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

from ..services.rag import RAGService
from ..config import settings


router = APIRouter(prefix="", tags=["chat"])


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = 6
    namespace: Optional[str] = None


class Source(BaseModel):
    id: str
    score: float
    metadata: dict


class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]


rag_service: RAGService | None = None


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        global rag_service
        if rag_service is None:
            rag_service = RAGService()
        namespace = req.namespace or settings.pinecone_namespace
        answer, sources = rag_service.answer_query(
            query=req.query, top_k=req.top_k, namespace=namespace
        )
        return ChatResponse(
            answer=answer,
            sources=[Source(id=s["id"], score=s["score"], metadata=s["metadata"]) for s in sources],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from __future__ import annotations

from typing import List, Tuple, Dict, Any, Optional

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

from ..config import settings


class RAGService:
    def __init__(self) -> None:
        self.embeddings = OpenAIEmbeddings(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
        )
        self.llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            temperature=settings.openai_temperature,
        )

        # Vector store will connect to existing Pinecone index
        self.vectorstore = PineconeVectorStore(
            index_name=settings.pinecone_index_name,
            embedding=self.embeddings,
            namespace=settings.pinecone_namespace,
            pinecone_api_key=settings.pinecone_api_key,
        )

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", ". ", ".", " "]
        )

    def split_documents(self, docs: List[Document]) -> List[Document]:
        return self.splitter.split_documents(docs)

    def answer_query(
        self, 
        query: str, 
        top_k: int = 6, 
        namespace: str | None = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        vectorstore = self.vectorstore
        if namespace is not None and namespace != settings.pinecone_namespace:
            vectorstore = PineconeVectorStore(
                index_name=settings.pinecone_index_name,
                embedding=self.embeddings,
                namespace=namespace,
                pinecone_api_key=settings.pinecone_api_key,
            )

        retriever = vectorstore.as_retriever(search_kwargs={"k": top_k})
        docs = retriever.get_relevant_documents(query)

        # Build context with source attribution
        context_parts = []
        for d in docs:
            source = d.metadata.get("source", "unknown")
            page = d.metadata.get("page", "")
            page_info = f" (page {int(page)})" if page != "" else ""
            context_parts.append(f"[From {source}{page_info}]:\n{d.page_content}")
        
        context = "\n\n".join(context_parts)

        system_prompt = (
            "You are an expert construction and architectural assistant specialized in analyzing technical drawings, blueprints, and construction documents. "
            
            "CRITICAL REQUIREMENTS:\n"
            "- ALWAYS specify which drawing/plan number you're referencing (e.g., 'According to drawing A3.2 - First Floor Plan...')\n"
            "- When multiple drawings contain similar information, compare and distinguish between them clearly\n"
            "- For ambiguous questions, ask for clarification (e.g., 'Which floor plan - A3.1 Ground Floor or A3.2 First Floor?')\n"
            "- For complex multi-drawing queries, synthesize information across drawings and cite each source\n"
            "- Keep original units and scales exactly as shown\n"
            "- If uncertain, explain what additional information would help verify\n"
            
            "EXPERTISE AREAS:\n"
            "- Construction details, materials, dimensions, codes, specifications\n"
            "- Building systems (structural, MEP, fire safety)\n"
            "- Code compliance and building regulations\n"
            "- Construction sequencing and coordination\n"
            
            "RESPONSE FORMAT:\n"
            "- Lead with the specific drawing reference\n"
            "- Provide precise measurements with units\n"
            "- Note any discrepancies between drawings\n"
            "- Suggest verification methods when uncertain"
        )

        # Build conversation with history
        messages = [("system", system_prompt)]
        
        # Add conversation history (token-based limit ~8k tokens for context)
        if conversation_history:
            # Rough token estimation: ~4 chars per token
            token_budget = 8000
            current_tokens = len(system_prompt) // 4 + len(context) // 4 + len(query) // 4
            
            # Add history from newest to oldest until we hit token limit
            history_to_include = []
            for msg in reversed(conversation_history):
                msg_tokens = len(msg["content"]) // 4
                if current_tokens + msg_tokens > token_budget:
                    break
                history_to_include.insert(0, msg)
                current_tokens += msg_tokens
            
            for msg in history_to_include:
                messages.append((msg["role"], msg["content"]))
        
        # Add current query with context
        messages.append(("user", f"Context from drawings:\n{context}\n\nQuestion: {query}"))

        response = self.llm.invoke(messages)
        answer = response.content if hasattr(response, "content") else str(response)

        sources: List[Dict[str, Any]] = []
        for d in docs:
            metadata = d.metadata or {}
            sources.append({
                "id": metadata.get("id") or metadata.get("source") or metadata.get("path", "unknown"),
                "score": metadata.get("_distance", 0.0) or metadata.get("score", 0.0),
                "metadata": metadata,
                "text_content": d.page_content,  # Include the actual text content
            })

        return answer, sources


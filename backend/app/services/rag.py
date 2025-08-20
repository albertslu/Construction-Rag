from __future__ import annotations

from typing import List, Tuple, Dict, Any

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
            chunk_size=1200,
            chunk_overlap=150,
            separators=["\n\n", "\n", ". ", ".", " "]
        )

    def split_documents(self, docs: List[Document]) -> List[Document]:
        return self.splitter.split_documents(docs)

    def answer_query(self, query: str, top_k: int = 6, namespace: str | None = None) -> Tuple[str, List[Dict[str, Any]]]:
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

        context = "\n\n".join([d.page_content for d in docs])

        system_prompt = (
            "You are a helpful assistant specialized in architectural drawings. "
            "Use the provided context from technical drawings, notes, legends, and specifications to answer precisely. "
            "When giving measurements, keep original units and scales if present. If unsure, say you are unsure and suggest how to verify."
        )

        messages = [
            ("system", system_prompt),
            ("user", f"Context:\n{context}\n\nQuestion: {query}")
        ]

        response = self.llm.invoke(messages)
        answer = response.content if hasattr(response, "content") else str(response)

        sources: List[Dict[str, Any]] = []
        for d in docs:
            metadata = d.metadata or {}
            sources.append({
                "id": metadata.get("id") or metadata.get("source") or metadata.get("path", "unknown"),
                "score": metadata.get("_distance", 0.0) or metadata.get("score", 0.0),
                "metadata": metadata,
            })

        return answer, sources


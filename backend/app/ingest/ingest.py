import argparse
import os
from typing import List

from langchain.schema import Document

from ..services.rag import RAGService
from ..utils.pdf_extract import extract_documents_from_pdf
from ..config import settings


def load_pdfs_from_dir(directory: str) -> List[Document]:
    documents: List[Document] = []
    for root, _, files in os.walk(directory):
        for f in files:
            if f.lower().endswith(".pdf"):
                path = os.path.join(root, f)
                docs = extract_documents_from_pdf(path, ocr_fallback=True, ocr_dpi=300)
                for d in docs:
                    d.metadata = {**(d.metadata or {}), "path": path, "source": os.path.basename(path)}
                documents.extend(docs)
    return documents


def main(data_dir: str, namespace: str) -> None:
    rag = RAGService()
    docs = load_pdfs_from_dir(data_dir)
    if not docs:
        print(f"No PDFs found in {data_dir}")
        return

    chunks = rag.split_documents(docs)

    print(f"Loaded {len(docs)} documents, split into {len(chunks)} chunks. Uploading to Pinecone...")

    # Use a temporary vector store bound to the specified namespace
    vectorstore = rag.vectorstore
    if namespace and namespace != settings.pinecone_namespace:
        from langchain_pinecone import PineconeVectorStore
        vectorstore = PineconeVectorStore(
            index_name=settings.pinecone_index_name,
            embedding=rag.embeddings,
            namespace=namespace,
        )

    vectorstore.add_documents(chunks)
    print("Ingestion complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", default=settings.data_dir)
    parser.add_argument("--namespace", default=settings.pinecone_namespace)
    args = parser.parse_args()
    main(args.data_dir, args.namespace)


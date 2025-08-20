from __future__ import annotations

import os
import shutil
import tempfile
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from langchain_community.document_loaders import PyPDFLoader
from langchain.schema import Document
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from langchain_pinecone import PineconeVectorStore

from ..services.rag import RAGService
from ..config import settings


router = APIRouter(prefix="", tags=["upload"])


class UploadResponse(BaseModel):
    namespace: str
    files_ingested: int
    documents_loaded: int
    chunks_indexed: int


@router.post("/upload", response_model=UploadResponse)
async def upload_pdfs(
    files: List[UploadFile] = File(...),
    namespace: Optional[str] = Form(None),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    target_namespace = namespace or settings.pinecone_namespace

    tmp_dir = tempfile.mkdtemp(prefix="ingest_")
    try:
        saved_paths: List[str] = []
        for f in files:
            if not f.filename.lower().endswith(".pdf"):
                continue
            tmp_path = os.path.join(tmp_dir, f.filename)
            with open(tmp_path, "wb") as out:
                content = await f.read()
                out.write(content)
            saved_paths.append(tmp_path)

        if not saved_paths:
            raise HTTPException(status_code=400, detail="No PDF files uploaded")

        rag = RAGService()

        total_docs = 0
        all_chunks = []
        for path in saved_paths:
            # Try text extraction first
            loader = PyPDFLoader(path)
            docs = loader.load()
            for d in docs:
                d.metadata = {**(d.metadata or {}), "path": path, "source": os.path.basename(path)}
            total_docs += len(docs)
            chunks = rag.split_documents(docs)
            all_chunks.extend(chunks)

            # If no chunks, fall back to OCR for scanned PDFs
            if len(chunks) == 0:
                ocr_docs: list[Document] = []
                with fitz.open(path) as pdf:
                    for page_index in range(len(pdf)):
                        page = pdf[page_index]
                        pix = page.get_pixmap(dpi=200)
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        text = pytesseract.image_to_string(img)
                        text = text.strip()
                        if not text:
                            continue
                        ocr_docs.append(
                            Document(page_content=text, metadata={"path": path, "source": os.path.basename(path), "page": page_index})
                        )
                if ocr_docs:
                    total_docs += len(ocr_docs)
                    ocr_chunks = rag.split_documents(ocr_docs)
                    all_chunks.extend(ocr_chunks)

        if not all_chunks:
            raise HTTPException(status_code=400, detail="No content extracted from PDFs")

        vectorstore = rag.vectorstore
        if target_namespace != settings.pinecone_namespace:
            vectorstore = PineconeVectorStore(
                index_name=settings.pinecone_index_name,
                embedding=rag.embeddings,
                namespace=target_namespace,
            )

        vectorstore.add_documents(all_chunks)

        return UploadResponse(
            namespace=target_namespace,
            files_ingested=len(saved_paths),
            documents_loaded=total_docs,
            chunks_indexed=len(all_chunks),
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


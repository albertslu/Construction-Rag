from __future__ import annotations

from typing import List

import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from langchain.schema import Document


def extract_documents_from_pdf(
    pdf_path: str,
    *,
    ocr_fallback: bool = True,
    ocr_dpi: int = 300,
    min_block_chars: int = 40,
) -> List[Document]:
    """Extract text blocks from a PDF using PyMuPDF, with optional OCR fallback.

    - Splits per text block to preserve layout
    - Filters tiny blocks
    - Adds page and bbox metadata
    """
    documents: List[Document] = []

    with fitz.open(pdf_path) as pdf:
        for page_index in range(len(pdf)):
            page = pdf[page_index]
            blocks = page.get_text("blocks") or []
            total_chars = 0
            for block in blocks:
                # block: (x0, y0, x1, y1, text, block_no, ...)
                if len(block) < 5:
                    continue
                x0, y0, x1, y1, text = block[0], block[1], block[2], block[3], (block[4] or "")
                text = text.strip()
                if len(text) < min_block_chars:
                    continue
                total_chars += len(text)
                documents.append(
                    Document(
                        page_content=text,
                        metadata={
                            "path": pdf_path,
                            "source": pdf_path.split("/")[-1],
                            "page": page_index,
                            "bbox": f"{x0:.1f},{y0:.1f},{x1:.1f},{y1:.1f}",
                        },
                    )
                )

            # OCR fallback if page had almost no selectable text
            if ocr_fallback and total_chars < min_block_chars:
                pix = page.get_pixmap(dpi=ocr_dpi)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                text = pytesseract.image_to_string(img)
                text = text.strip()
                if len(text) >= min_block_chars:
                    # For OCR, use full page as bounding box
                    page_rect = page.rect
                    documents.append(
                        Document(
                            page_content=text,
                            metadata={
                                "path": pdf_path,
                                "source": pdf_path.split("/")[-1],
                                "page": page_index,
                                "bbox": f"{page_rect.x0:.1f},{page_rect.y0:.1f},{page_rect.x1:.1f},{page_rect.y1:.1f}",
                                "ocr": True,
                            },
                        )
                    )

    return documents



from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import fitz  # PyMuPDF
import os
from ..config import settings

router = APIRouter(prefix="/pdf", tags=["pdf"])


@router.get("/{filename}/page/{page_num}")
async def get_pdf_page_image(filename: str, page_num: int):
    """
    Serve a PDF page as a PNG image for frontend display and highlighting
    """
    try:
        # Construct the full path to the PDF (check both data_dir and drawings folder)
        pdf_path = os.path.join("drawings", filename)
        if not os.path.exists(pdf_path):
            pdf_path = os.path.join(settings.data_dir, filename)
        
        # Security check - ensure the file exists
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail="PDF not found")
        
        # Open PDF and get the specified page
        with fitz.open(pdf_path) as pdf:
            if page_num < 0 or page_num >= len(pdf):
                raise HTTPException(status_code=404, detail="Page not found")
            
            page = pdf[page_num]
            
            # Render page to PNG at high DPI for good quality
            pix = page.get_pixmap(dpi=150)
            img_data = pix.tobytes("png")
            
            return Response(content=img_data, media_type="image/png")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering PDF page: {str(e)}")


@router.get("/{filename}/info")
async def get_pdf_info(filename: str):
    """
    Get basic info about a PDF (page count, dimensions)
    """
    try:
        # Construct the full path to the PDF (check both data_dir and drawings folder)
        pdf_path = os.path.join("drawings", filename)
        if not os.path.exists(pdf_path):
            pdf_path = os.path.join(settings.data_dir, filename)
        
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail="PDF not found")
        
        with fitz.open(pdf_path) as pdf:
            page_info = []
            for page_num in range(len(pdf)):
                page = pdf[page_num]
                rect = page.rect
                page_info.append({
                    "page": page_num,
                    "width": rect.width,
                    "height": rect.height
                })
            
            return {
                "filename": filename,
                "page_count": len(pdf),
                "pages": page_info
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading PDF info: {str(e)}")

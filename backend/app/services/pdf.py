from __future__ import annotations
import asyncio
import io
import fitz
from typing import Any, List, Optional, Set, TypedDict
from PIL import Image
from fastapi import HTTPException
from app.core.config import logger, MAX_DOC_PAGES, PYMUPDF_DPI

class PageImage(TypedDict):
    page_no: int
    image: Image.Image
    width: int
    height: int

def parse_page_filter(pages_str: str, total_pages: int = 0) -> Optional[Set[int]]:
    """Parse a page selection string into a set of 1-based page numbers.

    Supported formats:
        ""  or "all"  → None (all pages)
        "1"           → {1}
        "-1"          → {total_pages} (last page)
        "1,3,5"       → {1, 3, 5}
        "1-5"         → {1, 2, 3, 4, 5}
        "1-3,7,9-11"  → {1, 2, 3, 7, 9, 10, 11}
        "1, -2, -1"   → {1, total_pages - 1, total_pages}
    """
    cleaned = pages_str.strip().lower()
    if not cleaned or cleaned == "all":
        return None

    page_set: Set[int] = set()
    for part in cleaned.split(","):
        part = part.strip()
        if not part:
            continue
        # Check for range: e.g. "1-5", or "-2--1"
        search_idx = 1 if part.startswith("-") else 0
        hyphen_idx = part.find("-", search_idx)
        
        if hyphen_idx != -1:
            start_str = part[:hyphen_idx].strip()
            end_str = part[hyphen_idx+1:].strip()
            try:
                start = int(start_str)
                end = int(end_str)
                orig_start = start
                orig_end = end
                if start < 0 and total_pages > 0:
                    start = total_pages + 1 + start
                if end < 0 and total_pages > 0:
                    end = total_pages + 1 + end
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "error_type": "invalid_page_range",
                        "message": f"Invalid page range: '{part}'. Use format like '1-5' or '-2--1'.",
                    },
                )
            
            if total_pages > 0:
                if start < 1 or start > total_pages:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "success": False,
                            "error_type": "invalid_page_number",
                            "message": f"Page number {orig_start} is out of bounds. The PDF has only {total_pages} pages.",
                        },
                    )
                if end < 1 or end > total_pages:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "success": False,
                            "error_type": "invalid_page_number",
                            "message": f"Page number {orig_end} is out of bounds. The PDF has only {total_pages} pages.",
                        },
                    )
                if orig_start < 0 and start == 1 and total_pages > 1:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "success": False,
                            "error_type": "invalid_page_number",
                            "message": f"Invalid page range: '{part}'. Page {orig_start} resolves to page 1, which is invalid.",
                        },
                    )
                if orig_end < 0 and end == 1 and total_pages > 1:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "success": False,
                            "error_type": "invalid_page_number",
                            "message": f"Invalid page range: '{part}'. Page {orig_end} resolves to page 1, which is invalid.",
                        },
                    )

            if start < 1 or end < start:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "error_type": "invalid_page_range",
                        "message": f"Invalid page range: '{part}'. Start must be ≥ 1 and ≤ end.",
                    },
                )
            page_set.update(range(start, end + 1))
        else:
            try:
                num = int(part)
                orig_num = num
                if num < 0 and total_pages > 0:
                    num = total_pages + 1 + num
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "error_type": "invalid_page_number",
                        "message": f"Invalid page number: '{part}'. Must be an integer.",
                    },
                )
            
            if total_pages > 0:
                if num < 1 or num > total_pages:
                    if orig_num < 0:
                        continue
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "success": False,
                            "error_type": "invalid_page_number",
                            "message": f"Page number {orig_num} is out of bounds. The PDF has only {total_pages} pages.",
                        },
                    )
                if orig_num < 0 and num == 1 and total_pages > 1:
                    continue
            else:
                if num < 1:
                    continue
            page_set.add(num)
            
    return page_set

def _render_pdf_pages(pdf_bytes: bytes, effective_max: int, page_filter: Optional[Set[int]]) -> List[PageImage]:
    """Helper to render pages synchronously using PyMuPDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages = len(doc)
    pages: List[PageImage] = []

    for i in range(total_pages):
        page_no = i + 1
        if len(pages) >= effective_max:
            break
        if page_filter is not None and page_no not in page_filter:
            continue

        try:
            page = doc[i]
            # Render page to pixmap at target DPI
            pix = page.get_pixmap(dpi=PYMUPDF_DPI)
            # Convert pixmap directly to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            pages.append({
                "page_no": page_no,
                "image": img,
                "width": pix.width,
                "height": pix.height
            })
            del img, pix
        except Exception as e:
            logger.error("Failed to render page %d with PyMuPDF: %s", page_no, e)

    doc.close()
    try:
        fitz.TOOLS.store_shrink(100)
    except Exception:
        pass
    return pages

async def extract_pages(pdf_bytes: bytes, max_pages: int = MAX_DOC_PAGES, pages_str: str = "") -> List[PageImage]:
    """Render PDF pages to PIL images at target DPI using PyMuPDF."""
    num_pages = 0
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        num_pages = len(doc)
        doc.close()
    except Exception as e:
        logger.warning("Could not pre-verify PDF page count: %s", e)
    page_filter = parse_page_filter(pages_str, num_pages)

    if page_filter is None and num_pages > max_pages:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error_type": "page_limit_exceeded",
                "message": f"Too many pages. Maximum is {max_pages}, but the PDF has {num_pages} pages.",
            },
        )

    effective_max = max(page_filter) if page_filter else max_pages

    try:
        return await asyncio.to_thread(_render_pdf_pages, pdf_bytes, effective_max, page_filter)
    except Exception as e:
        logger.error("PyMuPDF page rendering failed: %s", e)
        return []

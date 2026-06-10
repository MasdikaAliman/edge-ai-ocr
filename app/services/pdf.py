import asyncio
import io
import os
import tempfile
from typing import Any, Dict, List, TypedDict

from fastapi import HTTPException
from app.core.config import logger, MAX_DOC_PAGES
from app.utils.image import pil_to_content_item

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableStructureOptions
from docling.datamodel.accelerator_options import AcceleratorOptions, AcceleratorDevice
from docling.datamodel.base_models import InputFormat
import pdfplumber
import fitz

class PageData(TypedDict):
    page_no: int
    image: Dict[str, Any]
    table_images: List[Dict[str, Any]]
    figure_images: List[Dict[str, Any]]
    colored_texts: list[dict]
    markdown: str

def _classify_color(r: int, g: int, b: int) -> str | None:
    """Classify an RGB value into a named color category.
    
    Returns None for black/near-black/white/gray text (i.e. "default" text).
    """
    # Skip black / near-black / white / gray
    if r < 40 and g < 40 and b < 40:
        return None
    if r > 220 and g > 220 and b > 220:
        return None
    # Gray — all channels close together and not vivid
    if max(r, g, b) - min(r, g, b) < 40:
        return None

    # Red family (includes dark red, maroon, crimson)
    if r > 120 and r > g * 1.5 and r > b * 1.5:
        return "RED"
    # Blue family (includes navy, royal blue, dark blue)
    if b > 80 and b > r * 1.3 and b > g * 1.2:
        return "BLUE"
    # Green family
    if g > 100 and g > r * 1.3 and g > b * 1.3:
        return "GREEN"
    # Orange / amber
    if r > 180 and 80 < g < 180 and b < 80:
        return "ORANGE"
    # Any other clearly non-neutral color
    if max(r, g, b) - min(r, g, b) > 60:
        return "COLORED"
    return None


def extract_colored_text(fitz_page: fitz.Page) -> list[dict]:
    """Extract non-black, non-white colored text spans from a PDF page."""
    colored = []
    for block in fitz_page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if not text:
                    continue
                color = span.get("color", 0)
                r = (color >> 16) & 0xFF
                g = (color >> 8) & 0xFF
                b = color & 0xFF

                label = _classify_color(r, g, b)
                if label:
                    colored.append({
                        "text": text,
                        "color": label,
                        "rgb": f"({r},{g},{b})",
                    })
    return colored


def _run_docling(pdf_bytes: bytes, max_pages: int = MAX_DOC_PAGES) -> List[PageData]:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    try:
        pipeline_options = PdfPipelineOptions(artifacts_path='./models/docling')
        pipeline_options.do_ocr = False
        pipeline_options.table_structure_options = TableStructureOptions(do_cell_matching=True)
        pipeline_options.accelerator_options = AcceleratorOptions(device=AcceleratorDevice.CUDA)
        pipeline_options.images_scale = 2.0
        pipeline_options.generate_page_images = True
        pipeline_options.generate_table_images = True
        pipeline_options.generate_picture_images = True

        converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
        )
        result = converter.convert(tmp_path)
        doc = result.document

        tables_by_page: Dict[int, list] = {}
        for table in doc.tables:
            for p in (getattr(table, "prov", None) or []):
                tables_by_page.setdefault(p.page_no, []).append(table)

        figures_by_page: Dict[int, list] = {}
        for pic in getattr(doc, "pictures", []):
            for p in (getattr(pic, "prov", None) or []):
                figures_by_page.setdefault(p.page_no, []).append(pic)

        text_by_page: Dict[int, List[str]] = {}
        for item, _level in doc.iterate_items():
            if hasattr(item, "text") and hasattr(item, "prov") and item.prov:
                for p in item.prov:
                    text_by_page.setdefault(p.page_no, []).append(item.text)

        fitz_doc = fitz.open(tmp_path)

        pages: List[PageData] = []
        for page_no, page in sorted(doc.pages.items()):
            if len(pages) >= max_pages:
                break
            if page.image is None:
                logger.warning("Page %d has no image, skipping.", page_no)
                continue

            table_image_items: List[Dict[str, Any]] = []
            for table in tables_by_page.get(page_no, []):
                try:
                    table_img = table.get_image(doc)
                    if table_img:
                        table_image_items.append(pil_to_content_item(table_img))
                except Exception as e:
                    logger.error("Could not extract table image on page %d: %s", page_no, e)

            figure_image_items: List[Dict[str, Any]] = []
            for pic in figures_by_page.get(page_no, []):
                try:
                    fig_img = pic.get_image(doc)
                    if fig_img:
                        figure_image_items.append(pil_to_content_item(fig_img))
                except Exception as e:
                    logger.error("Could not extract figure image on page %d: %s", page_no, e)

            colored_texts = []
            try:
                fitz_page = fitz_doc[page_no - 1]
                colored_texts = extract_colored_text(fitz_page)
            except Exception as e:
                logger.warning("Could not extract colored text on page %d: %s", page_no, e)

            pages.append(PageData(
                page_no=page_no,
                image=pil_to_content_item(page.image.pil_image),
                table_images=table_image_items,
                figure_images=figure_image_items,
                colored_texts = colored_texts,
                markdown="\n".join(text_by_page.get(page_no, [])),
            ))
        fitz_doc.close()
        logger.info("Docling extracted %d pages from PDF.", len(pages))
        return pages
    finally:
        os.unlink(tmp_path)


def _run_pdfplumber(pdf_bytes: bytes, max_pages: int = MAX_DOC_PAGES) -> List[PageData]:
    pages: List[PageData] = []
    fitz_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for i, page in enumerate(pdf.pages):
            if i >= max_pages:
                break
            im = page.to_image(resolution=200).original
            native_text = page.extract_text(x_tolerance=3, y_tolerance=5) or ""

            # Attempt table extraction as markdown hint
            table_md = _extract_tables_markdown(page)
            markdown = native_text
            if table_md:
                markdown += "\n\n" + table_md

            colored_texts = []
            try:
                fitz_page = fitz_doc[i]
                colored_texts = extract_colored_text(fitz_page)
            except Exception as e:
                logger.warning("Could not extract colored text on page %d: %s", i + 1, e)

            pages.append(PageData(
                page_no=i + 1,
                image=pil_to_content_item(im),
                table_images=[],
                figure_images=[],
                colored_texts = colored_texts,
                markdown=markdown,
            ))
    fitz_doc.close()
    return pages

def _extract_tables_markdown(page: Any) -> str:
    _TABLE_SETTINGS_LINES = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 5,
        "join_tolerance": 5,
        "edge_min_length": 10,
        "min_words_vertical": 2,
        "min_words_horizontal": 1,
    }
    _TABLE_SETTINGS_TEXT = {
        "vertical_strategy": "text",
        "horizontal_strategy": "text",
        "snap_tolerance": 5,
        "join_tolerance": 5,
        "min_words_vertical": 2,
        "min_words_horizontal": 1,
    }

    tables = page.extract_tables(_TABLE_SETTINGS_LINES)
    if not tables:
        tables = page.extract_tables(_TABLE_SETTINGS_TEXT)
    parts = []
    for table in (tables or []):
        if table:
            rows = [" | ".join(cell or "" for cell in row) for row in table]
            parts.append("\n".join(rows))
    return "\n\n".join(parts)

async def extract_pages(pdf_bytes: bytes, max_pages: int = MAX_DOC_PAGES) -> List[PageData]:
    # Check total page count first to prevent silent truncation
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            num_pages = len(pdf.pages)
            if num_pages > max_pages:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "error_type": "page_limit_exceeded",
                        "message": f"Too many pages. Maximum is {max_pages}, but the PDF has {num_pages} pages.",
                    },
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Could not pre-verify PDF page count: %s", e)

    logger.info("Routing PDF through Docling pipeline.")
    try:
        pages = await asyncio.to_thread(_run_docling, pdf_bytes, max_pages)
        if pages:
            return pages
        logger.error("Docling returned no pages, falling back to pdfplumber.")
    except Exception as e:
        logger.error("Docling failed (%s), falling back to pdfplumber.", e)

    logger.info("Falling back to pdfplumber image extraction.")
    try:
        return await asyncio.to_thread(_run_pdfplumber, pdf_bytes, max_pages)
    except Exception as e:
        logger.error("pdfplumber also failed to process PDF: %s", e)
        return []

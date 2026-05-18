import asyncio
import io
import os
import tempfile
from typing import Any, Dict, List, TypedDict

from app.core.config import logger, MAX_IMAGES
from app.utils.image import pil_to_content_item

try:
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TableStructureOptions, EasyOcrOptions
    from docling.datamodel.accelerator_options import AcceleratorOptions, AcceleratorDevice
    from docling.datamodel.base_models import InputFormat
    _DOCLING_AVAILABLE = True
    logger.info("Docling is available — PDF text extraction enabled.")
except ImportError:
    _DOCLING_AVAILABLE = False
    logger.warning("Docling not installed. PDFs will fall back to image-based OCR.")


class PageData(TypedDict):
    page_no: int
    image: Dict[str, Any]
    table_images: List[Dict[str, Any]]
    markdown: str


def _run_docling(pdf_bytes: bytes) -> List[PageData]:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    try:
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False
        pipeline_options.table_structure_options = TableStructureOptions(do_cell_matching=True)
        pipeline_options.accelerator_options = AcceleratorOptions(device=AcceleratorDevice.CPU)
        pipeline_options.images_scale = 2.0
        pipeline_options.generate_page_images = True

        converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
        )
        result = converter.convert(tmp_path)
        doc = result.document

        tables_by_page: Dict[int, list] = {}
        for table in doc.tables:
            for p in (getattr(table, "prov", None) or []):
                tables_by_page.setdefault(p.page_no, []).append(table)

        text_by_page: Dict[int, List[str]] = {}
        for item, _level in doc.iterate_items():
            if hasattr(item, "text") and hasattr(item, "prov") and item.prov:
                for p in item.prov:
                    text_by_page.setdefault(p.page_no, []).append(item.text)

        pages: List[PageData] = []
        for page_no, page in doc.pages.items():
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

            pages.append(PageData(
                page_no=page_no,
                image=pil_to_content_item(page.image.pil_image),
                table_images=table_image_items,
                markdown="\n".join(text_by_page.get(page_no, [])),
            ))

        logger.info("Docling extracted %d pages from PDF.", len(pages))
        return pages
    finally:
        os.unlink(tmp_path)


def _run_pdfplumber(pdf_bytes: bytes, max_pages: int = MAX_IMAGES) -> List[PageData]:
    import pdfplumber
    pages: List[PageData] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for i, page in enumerate(pdf.pages):
            if i >= max_pages:
                break
            im = page.to_image(resolution=500).original
            pages.append(PageData(
                page_no=i + 1,
                image=pil_to_content_item(im),
                table_images=[],
                markdown="",
            ))
    return pages


async def extract_pages(pdf_bytes: bytes) -> List[PageData]:
    if _DOCLING_AVAILABLE:
        logger.info("Routing PDF through Docling page-by-page pipeline.")
        try:
            pages = await asyncio.to_thread(_run_docling, pdf_bytes)
            if pages:
                return pages
            logger.error("Docling returned no pages, falling back to pdfplumber.")
        except Exception as e:
            logger.error("Docling failed (%s), falling back to pdfplumber.", e)

    logger.info("Falling back to pdfplumber image-based OCR.")
    try:
        return await asyncio.to_thread(_run_pdfplumber, pdf_bytes)
    except Exception as e:
        logger.error("pdfplumber also failed to process PDF: %s", e)
        return []

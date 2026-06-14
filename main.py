import requests
from typing import Annotated, List, Optional, Set
import re

from fastapi import FastAPI, File, Form, HTTPException, UploadFile as UF
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import WithJsonSchema

from app.core.config import BASE_URL_LLM, MAX_IMAGE_SIZE, MAX_DOC_PAGES, DocumentType, logger
from app.core.doc_prompt import DOCUMENT_PROMPTS
from app.core.sys_prompt import BASE_DIRECTIVES
from app.services.pdf import PageData, extract_pages
from app.services.pipeline import run_ocr
from app.utils.call_log import create_call_log
from app.utils.image import bytes_to_content_item

UploadFile = Annotated[UF, WithJsonSchema({"type": "string", "format": "binary"})]

app = FastAPI(
    title="Document OCR API",
    description=(
        "High-precision document OCR powered by Qwen3-VL via vLLM.\n\n"
        "Accepts images as **base64 JSON** or **multipart file uploads**.\n\n"
        "Features a **LangGraph-powered page-by-page pipeline** that sends each page's "
        "full image, table crops, and extracted markdown to the VLM for maximum accuracy.\n\n"
        "PDFs are processed via **Docling** (page images + table crops + markdown).\n\n"
        "Supported document types: " + ", ".join(DOCUMENT_PROMPTS.keys())
    ),
    version="5.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/openapi.json", include_in_schema=False)
async def custom_openapi():
    return JSONResponse(content=app.openapi(), media_type="application/json; charset=utf-8")


async def _process_files(
    files: List[UploadFile],
    pages: str = "",
    document_type: str = "",
) -> List[PageData]:
    if len(files) == 0:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error_type": "no_files",
                "message": "At least one file is required.",
            },
        )

    # COO specific composition validation
    if document_type == "COO":
        if len(files) > 4:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error_type": "coo_files_limit_exceeded",
                    "message": "Unggahan berkas COO melebihi batas (maksimal 4 berkas: PEB, INV, PL, BL).",
                },
            )

        types_found = {"BL": 0, "PEB": 0, "PL": 0, "INV": 0}
        for upload in files:
            name = upload.filename.lower()
            if "bl" in name or "lading" in name or "bill" in name:
                types_found["BL"] += 1
            elif "peb" in name or "ekspor" in name:
                types_found["PEB"] += 1
            elif "packing" in name or "pl" in name:
                types_found["PL"] += 1
            elif "invoice" in name or "inv" in name:
                types_found["INV"] += 1
            else:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "error_type": "file_pages_required",
                        "message": f"Berkas tidak didukung ({upload.filename}), pastikan berkas berkaitan dengan tipe dokumen COO.",
                    },
                )

        missing = [t for t, count in types_found.items() if count == 0]
        duplicates = [t for t, count in types_found.items() if count > 1]

        if missing or duplicates:
            msg_parts = []
            if missing:
                msg_parts.append(f"berkas kurang: {', '.join(missing)}")
            if duplicates:
                msg_parts.append(f"berkas duplikat: {', '.join(duplicates)}")
            
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error_type": "coo_invalid_composition",
                    "message": f"Komposisi berkas COO tidak valid. {'; '.join(msg_parts)}.",
                },
            )

    pdf_count = 0
    image_count = 0
    image_pages: List[PageData] = []

    # Check multiple PDFs condition: only allow multiple PDFs if document_type == "COO"
    for upload in files:
        content_type = upload.content_type or "application/octet-stream"
        mime = content_type.split(";")[0].strip().lower()
        if mime == "application/pdf":
            pdf_count += 1

    if document_type != "COO" and pdf_count > 1:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error_type": "multiple_pdfs",
                "message": "Only a single PDF file is allowed.",
            },
        )

    for upload in files:
        content_type = upload.content_type or "application/octet-stream"
        raw_bytes = await upload.read()
        if not raw_bytes:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error_type": "empty_file",
                    "message": f"Uploaded file '{upload.filename}' is empty.",
                },
            )

        try:
            mime = content_type.split(";")[0].strip().lower()
            if mime == "application/pdf":
                # Determine page range rule for this PDF
                if document_type == "COO":
                    name = upload.filename.lower()
                    if "bl" in name or "lading" in name or "bill" in name:
                        file_pages = pages if pages else ""
                    elif "peb" in name or "ekspor" in name:
                        file_pages = pages if pages else "1"
                    elif "packing" in name or "pl" in name:
                        file_pages = pages if pages else "1"
                    elif "invoice" in name or "inv" in name:
                        file_pages = pages if pages else "-2"
                    else: 
                        file_pages = pages
                elif document_type == "Invoice":
                    file_pages = pages if pages else "1, -2"
                else:
                    file_pages = pages

                pdf_pages = await extract_pages(raw_bytes, pages_str=file_pages)
                # We need to assign sequential page numbers to avoid duplicates
                for page in pdf_pages:
                    page["page_no"] = len(image_pages) + 1
                    image_pages.append(page)
            else:
                image_count += 1
                if image_count > MAX_DOC_PAGES:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "success": False,
                            "error_type": "too_many_images",
                            "message": f"Too many images. Maximum is {MAX_DOC_PAGES}.",
                        },
                    )
                content_item = bytes_to_content_item(raw_bytes, content_type)
                image_pages.append(PageData(
                    page_no=len(image_pages) + 1,
                    image=content_item,
                    table_images=[],
                    markdown="",
                ))
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error_type": "file_read_error",
                    "message": f"Could not process file '{upload.filename}': {e}",
                },
            )

    return image_pages


@app.post(
    "/ocr/process/document",
    summary="Extract document based on predefined type",
    tags=["OCR"],
)
async def process_ocr_document(
    files: List[UploadFile] = File(
        ...,
        description=(
            f"One or more image/PDF files to process (max {MAX_DOC_PAGES} pages/images). "
            "Accepted formats: JPEG, PNG, WebP, GIF, TIFF, PDF."
        ),
    ),
    document_type: DocumentType = Form(
        ...,
        description="Document type. Options: " + ", ".join(DOCUMENT_PROMPTS.keys()),
    ),
    pages: str = Form(
        "",
        description=(
            "Page selection for PDF files. "
            "Leave empty or 'all' for all pages. "
            "Examples: '1' (page 1 only), '1-5' (pages 1 to 5), '1,3,5' (specific pages), '1-3,7' (mixed)."
        ),
    ),
):
    image_pages = await _process_files(files, pages=pages, document_type=document_type)
    result = await run_ocr(document_type, image_pages, None, "")
    create_call_log(
        request_data={"endpoint": "/ocr/process/document", "document_type": document_type, "pages": pages, "files": [f.filename for f in files]},
        pdf_result=[{"page_no": p["page_no"], "markdown": p.get("markdown", ""), "image": p["image"], "table_images": p.get("table_images", [])} for p in image_pages],
        messages_sent=result.pop("messages_log", []),
        output=result,
    )
    return result


@app.post(
    "/ocr/process/fields",
    summary="Extract specific custom fields",
    tags=["OCR"],
)
async def process_ocr_fields(
    files: List[UploadFile] = File(
        ...,
        description=(
            f"One or more image/PDF files to process (max {MAX_DOC_PAGES} pages/images). "
            "Accepted formats: JPEG, PNG, WebP, GIF, TIFF, PDF."
        ),
    ),
    fields: List[str] = Form(
        [],
        description="List of field names to extract. They will be converted to snake_case internally.",
    ),
    pages: str = Form(
        "",
        description=(
            "Page selection for PDF files. "
            "Leave empty or 'all' for all pages. "
            "Examples: '1' (page 1 only), '1-5' (pages 1 to 5), '1,3,5' (specific pages), '1-3,7' (mixed)."
        ),
    ),
):
    # Helper to convert strings to snake_case
    def _to_snake_case(value: str) -> str:
        # Replace non-alphanumeric characters with underscore, collapse multiple underscores, strip leading/trailing underscores
        s = re.sub(r"[^0-9a-zA-Z]+", "_", value)
        s = re.sub(r"_+", "_", s)
        return s.strip("_").lower()

    # Split each entry by comma (supports both comma-separated and repeated form fields), then normalize to snake_case
    raw = []
    for f in fields:
        for part in f.split(","):
            part = part.strip()
            if part:
                raw.append(part)
    normalized_fields = [_to_snake_case(f) for f in raw]
    parsed_fields = normalized_fields or None
    image_pages = await _process_files(files, pages=pages, document_type="Fields")
    result = await run_ocr("Fields", image_pages, parsed_fields, "")
    create_call_log(
        request_data={"endpoint": "/ocr/process/fields", "fields": parsed_fields, "pages": pages, "files": [f.filename for f in files]},
        pdf_result=[{"page_no": p["page_no"], "markdown": p.get("markdown", ""), "image": p["image"], "table_images": p.get("table_images", [])} for p in image_pages],
        messages_sent=result.pop("messages_log", []),
        output=result,
    )
    return result


@app.post(
    "/ocr/process/prompt",
    summary="Extract using a custom prompt",
    tags=["OCR"],
)
async def process_ocr_prompt(
    files: List[UploadFile] = File(
        ...,
        description=(
            f"One or more image/PDF files to process (max {MAX_DOC_PAGES} pages/images). "
            "Accepted formats: JPEG, PNG, WebP, GIF, TIFF, PDF."
        ),
    ),
    custom_prompt: str = Form(
        BASE_DIRECTIVES,
        description="Custom instruction prepended to the model input.",
    ),
    pages: str = Form(
        "",
        description=(
            "Page selection for PDF files. "
            "Leave empty or 'all' for all pages. "
            "Examples: '1' (page 1 only), '1-5' (pages 1 to 5), '1,3,5' (specific pages), '1-3,7' (mixed)."
        ),
    ),
):
    image_pages = await _process_files(files, pages=pages, document_type="Custom")
    result = await run_ocr("Custom", image_pages, None, custom_prompt)
    create_call_log(
        request_data={"endpoint": "/ocr/process/prompt", "custom_prompt": custom_prompt, "pages": pages, "files": [f.filename for f in files]},
        pdf_result=[{"page_no": p["page_no"], "markdown": p.get("markdown", ""), "image": p["image"], "table_images": p.get("table_images", [])} for p in image_pages],
        messages_sent=result.pop("messages_log", []),
        output=result,
    )
    return result


@app.get("/health", tags=["Utility"])
def health_check():
    base_info = {
        "vllm_max_model_len": 11000,
        "max_image_size": f"{MAX_IMAGE_SIZE}×{MAX_IMAGE_SIZE}",
        "max_images_per_request": MAX_DOC_PAGES,
    }
    try:
        resp = requests.get(f"{BASE_URL_LLM}/health", timeout=5)
        if resp.status_code == 200:
            return {"status": "Healthy", "model_ready": True, **base_info}
        return {"status": f"Unhealthy (HTTP {resp.status_code})", "model_ready": False, **base_info}
    except requests.exceptions.ConnectionError:
        return {"status": "vLLM server not reachable", "model_ready": False, **base_info}
    except requests.exceptions.Timeout:
        return {"status": "vLLM server timeout", "model_ready": False, **base_info}
    except Exception as e:
        return {"status": f"Unexpected error: {e}", "model_ready": False, **base_info}


@app.get("/", tags=["Utility"])
async def root():
    return {
        "name": "Document OCR API",
        "version": "5.1.0",
        "supported_document_types": list(DOCUMENT_PROMPTS.keys()),
        "endpoints": {
            "document_ocr": "POST /ocr/process/document",
            "fields_ocr":   "POST /ocr/process/fields",
            "prompt_ocr":   "POST /ocr/process/prompt",
            "health":       "GET  /health",
            "docs":         "GET  /docs",
            "redoc":        "GET  /redoc",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5030)

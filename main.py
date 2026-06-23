import requests
import io
import base64
from typing import Annotated, List, Optional, Set, Dict
import re
from PIL import Image

from fastapi import FastAPI, File, Form, HTTPException, UploadFile as UF
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import WithJsonSchema

from app.core.config import BASE_URL_LLM, MAX_DOC_PAGES, DocumentType, logger
from app.core.doc_prompt import DOCUMENT_PROMPTS
from app.services.pdf import PageImage, extract_pages
from app.services.semantic import run_semantic
from app.utils.call_log import create_call_log

UploadFile = Annotated[UF, WithJsonSchema({"type": "string", "format": "binary"})]

app = FastAPI(
    title="Document OCR API",
    description=(
        "High-precision document OCR powered by PaddleOCR + Qwen2.5 text-only semantic mapping.\n\n"
        "Accepts images or PDFs, runs high-precision local OCR, and maps fields semantically using the LLM.\n\n"
        "Supported document types: " + ", ".join(DOCUMENT_PROMPTS.keys())
    ),
    version="6.0.0",
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


def _to_call_log_pdf_result(page_images: List[PageImage]) -> List[dict]:
    """Helper to convert PIL images in page_images to standard Call Log format."""
    pdf_result = []
    for p in page_images:
        try:
            buffered = io.BytesIO()
            p["image"].save(buffered, format="JPEG")
            img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            pdf_result.append({
                "page_no": p["page_no"],
                "markdown": "",
                "image": {
                    "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                    "mime_type": "image/jpeg"
                },
                "table_images": []
            })
        except Exception as e:
            logger.warning("Failed to prepare image for call log: %s", e)
    return pdf_result


async def _process_files(
    files: List[UploadFile],
    pages: str = "",
    document_type: str = "",
) -> List[PageImage]:
    if len(files) == 0:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error_type": "no_files",
                "message": "At least one file is required.",
            },
        )

    pdf_count = 0
    image_count = 0
    image_pages: List[PageImage] = []

    for upload in files:
        content_type = upload.content_type or "application/octet-stream"
        mime = content_type.split(";")[0].strip().lower()
        if mime == "application/pdf":
            pdf_count += 1

    if pdf_count > 1:
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
                if document_type == "INV_COO":
                    file_pages = "1"
                elif document_type == "PEB":
                    file_pages = "-2"
                elif document_type == "PL":
                    file_pages = "1"
                elif document_type == "Invoice_SPBB":
                    file_pages = "1, -1, -2"
                else:
                    file_pages = pages

                pdf_pages = await extract_pages(raw_bytes, pages_str=file_pages)
                # Assign sequential page numbers to avoid duplicates
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
                img = Image.open(io.BytesIO(raw_bytes))
                width, height = img.size
                image_pages.append({
                    "page_no": len(image_pages) + 1,
                    "image": img,
                    "width": width,
                    "height": height
                })
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
    show_only_mismatch: bool = Form(
        False,
        description="If True, only return bounding boxes for mismatched values between LLM and raw OCR.",
    ),
):
    if document_type == "COO":
        return await process_ocr_coo_document(files, pages, show_only_mismatch)
    else:
        page_images = await _process_files(files, pages=pages, document_type=document_type)
        result = await run_semantic(document_type, page_images, fields=None, custom_prompt="", show_only_mismatch=show_only_mismatch)
        
        # Include page dimensions in response
        page_dims = {str(p["page_no"]): {"width": p["width"], "height": p["height"]} for p in page_images}
        result["page_dimensions"] = page_dims

        # Call Log
        pdf_result = _to_call_log_pdf_result(page_images)
        messages_sent = list(result.get("messages_log", []))
        # Create a copy of results for call log without popping messages_log
        clean_result = {k: v for k, v in result.items() if k != "messages_log"}
        create_call_log(
            request_data={"endpoint": "/ocr/process/document", "document_type": document_type, "pages": pages, "files": [f.filename for f in files]},
            pdf_result=pdf_result,
            messages_sent=messages_sent,
            output=clean_result,
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
    show_only_mismatch: bool = Form(
        False,
        description="If True, only return bounding boxes for mismatched values between LLM and raw OCR.",
    ),
):
    # Helper to convert strings to snake_case
    def _to_snake_case(value: str) -> str:
        s = re.sub(r"[^0-9a-zA-Z]+", "_", value)
        s = re.sub(r"_+", "_", s)
        return s.strip("_").lower()

    # Split each entry by comma
    raw = []
    for f in fields:
        for part in f.split(","):
            part = part.strip()
            if part:
                raw.append(part)
    normalized_fields = [_to_snake_case(f) for f in raw]
    parsed_fields = normalized_fields or None
    page_images = await _process_files(files, pages=pages, document_type="Fields")
    result = await run_semantic("Fields", page_images, parsed_fields, "", show_only_mismatch=show_only_mismatch)
    
    # Include page dimensions in response
    page_dims = {str(p["page_no"]): {"width": p["width"], "height": p["height"]} for p in page_images}
    result["page_dimensions"] = page_dims

    # Call Log
    pdf_result = _to_call_log_pdf_result(page_images)
    messages_sent = list(result.get("messages_log", []))
    clean_result = {k: v for k, v in result.items() if k != "messages_log"}
    create_call_log(
        request_data={"endpoint": "/ocr/process/fields", "fields": parsed_fields, "pages": pages, "files": [f.filename for f in files]},
        pdf_result=pdf_result,
        messages_sent=messages_sent,
        output=clean_result,
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
        ...,
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
    show_only_mismatch: bool = Form(
        False,
        description="If True, only return bounding boxes for mismatched values between LLM and raw OCR.",
    ),
):
    page_images = await _process_files(files, pages=pages, document_type="Custom")
    result = await run_semantic("Custom", page_images, None, custom_prompt, show_only_mismatch=show_only_mismatch)
    
    # Include page dimensions in response
    page_dims = {str(p["page_no"]): {"width": p["width"], "height": p["height"]} for p in page_images}
    result["page_dimensions"] = page_dims

    # Call Log
    pdf_result = _to_call_log_pdf_result(page_images)
    messages_sent = list(result.get("messages_log", []))
    clean_result = {k: v for k, v in result.items() if k != "messages_log"}
    create_call_log(
        request_data={"endpoint": "/ocr/process/prompt", "custom_prompt": custom_prompt, "pages": pages, "files": [f.filename for f in files]},
        pdf_result=pdf_result,
        messages_sent=messages_sent,
        output=clean_result,
    )
    return result


async def process_ocr_coo_document(
    files: List[UploadFile],
    pages: str,
    show_only_mismatch: bool = False
):
    if len(files) > 4:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error_type": "coo_files_limit_exceeded",
                "message": "Unggahan berkas COO melebihi batas (maksimal 4 berkas: PEB, INV, PL, BL).",
            },
        )

    classified: Dict[str, UploadFile] = {
        "BL": None,
        "PEB": None,
        "PL": None,
        "INV_COO": None
    }

    for upload in files:
        name = upload.filename.lower()
        if "bl" in name or "lading" in name or "bill" in name:
            if classified["BL"] is not None:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "error_type": "coo_invalid_composition",
                        "message": "Komposisi berkas COO tidak valid. Ditemukan lebih dari satu berkas BL.",
                    },
                )
            classified["BL"] = upload
        elif "peb" in name or "ekspor" in name:
            if classified["PEB"] is not None:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "error_type": "coo_invalid_composition",
                        "message": "Komposisi berkas COO tidak valid. Ditemukan lebih dari satu berkas PEB.",
                    },
                )
            classified["PEB"] = upload
        elif "packing" in name or "pl" in name:
            if classified["PL"] is not None:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "error_type": "coo_invalid_composition",
                        "message": "Komposisi berkas COO tidak valid. Ditemukan lebih dari satu berkas PL.",
                    },
                )
            classified["PL"] = upload
        elif "invoice" in name or "inv" in name:
            if classified["INV_COO"] is not None:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "error_type": "coo_invalid_composition",
                        "message": "Komposisi berkas COO tidak valid. Ditemukan lebih dari satu berkas Invoice.",
                    },
                )
            classified["INV_COO"] = upload
        else:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error_type": "file_pages_required",
                    "message": f"Berkas tidak didukung ({upload.filename}), pastikan berkas berkaitan dengan tipe dokumen COO (BL, PEB, PL, INV).",
                },
            )

    missing = [t for t, f in classified.items() if f is None]
    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error_type": "coo_invalid_composition",
                "message": f"Komposisi berkas COO tidak lengkap. Berkas berikut kurang: {', '.join(missing)}.",
            },
        )

    # Process BL
    bl_pages = pages if pages else ""
    bl_file_pages = await _process_files([classified["BL"]], pages=bl_pages, document_type="BL")
    bl_result = await run_semantic("BL", bl_file_pages, None, "", show_only_mismatch=show_only_mismatch)
    bl_data = bl_result.get("data", {}) if bl_result.get("success") else {}
    bl_data = bl_data or {}

    # Process PEB
    peb_pages = "-2"
    peb_file_pages = await _process_files([classified["PEB"]], pages=peb_pages, document_type="PEB")
    peb_result = await run_semantic("PEB", peb_file_pages, None, "", show_only_mismatch=show_only_mismatch)
    peb_data = peb_result.get("data", {}) if peb_result.get("success") else {}
    peb_data = peb_data or {}

    # Process PL
    pl_pages = "1"
    pl_file_pages = await _process_files([classified["PL"]], pages=pl_pages, document_type="PL")
    pl_result = await run_semantic("PL", pl_file_pages, None, "", show_only_mismatch=show_only_mismatch)
    pl_data = pl_result.get("data", {}) if pl_result.get("success") else {}
    pl_data = pl_data or {}

    # Process INV_COO
    inv_pages = "1"
    inv_file_pages = await _process_files([classified["INV_COO"]], pages=inv_pages, document_type="INV_COO")
    inv_result = await run_semantic("INV_COO", inv_file_pages, None, "", show_only_mismatch=show_only_mismatch)
    inv_data = inv_result.get("data", {}) if inv_result.get("success") else {}
    inv_data = inv_data or {}

    # Programmatic merge based on the sub-document schemas
    merged_data = {
        "consignee": bl_data.get("consignee"),
        "vessel_voyage_no": bl_data.get("vessel_voyage_no"),
        "mvs": bl_data.get("mvs"),
        "invoice_no": inv_data.get("invoice_number"),
        "invoice_date": inv_data.get("invoice_date"),
        "document_no_bl": bl_data.get("document_no"),
        "date_bl": bl_data.get("document_date"),
        "document_no_peb": peb_data.get("nomor_pendaftaran"),
        "date_peb": peb_data.get("tanggal_pendaftaran"),
        "document_no_pl": pl_data.get("no"),
        "date_pl": pl_data.get("date"),
        "ship_date": bl_data.get("ship_date"),
        "country_of_destination": bl_data.get("country_of_destination"),
        "form": inv_data.get("form"),
        "table": inv_data.get("table", []),
        "total_amount": inv_data.get("total_amount"),
        "total_weight_bruto": inv_data.get("total_weight_bruto"),
        "total_weight_netto": inv_data.get("total_weight_netto"),
        "total_quantity_ctns": inv_data.get("total_quantity_ctns"),
        "total_quantity_pcs": inv_data.get("total_quantity_pcs"),
    }

    # Combined logs formatting
    combined_pdf_result = []
    combined_messages_log = []
    combined_page_dims = {}

    for pages_data in [bl_file_pages, peb_file_pages, pl_file_pages, inv_file_pages]:
        for p in pages_data:
            next_page_no = len(combined_pdf_result) + 1
            combined_page_dims[str(next_page_no)] = {"width": p["width"], "height": p["height"]}
            
            buffered = io.BytesIO()
            p["image"].save(buffered, format="JPEG")
            img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            combined_pdf_result.append({
                "page_no": next_page_no,
                "markdown": "",
                "image": {
                    "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                    "mime_type": "image/jpeg"
                },
                "table_images": []
            })

    for res in [bl_result, peb_result, pl_result, inv_result]:
        if "messages_log" in res:
            combined_messages_log.extend(res["messages_log"])

    result_output = {
        "success": True, 
        "data": merged_data,
        "page_dimensions": combined_page_dims
    }
    
    create_call_log(
        request_data={"endpoint": "/ocr/process/coo", "pages": pages, "files": [f.filename for f in files]},
        pdf_result=combined_pdf_result,
        messages_sent=combined_messages_log,
        output={"success": True, "data": merged_data, "page_dimensions": combined_page_dims},
    )

    return result_output


@app.get("/health", tags=["Utility"])
def health_check():
    base_info = {
        "vllm_max_model_len": 11000,
        "max_image_size": "N/A",
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
        "version": "6.0.0",
        "supported_document_types": list(DOCUMENT_PROMPTS.keys()) + ["COO"],
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

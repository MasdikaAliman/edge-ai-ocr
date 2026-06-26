import requests
import asyncio
import io
import base64
from typing import Annotated, List, Optional, Set, Dict
import re
from PIL import Image

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile as UF
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import WithJsonSchema
from pydantic import BaseModel

from app.utils.auth import get_current_user, get_current_admin, verify_password, create_access_token
from app.utils.user_db import get_user, add_user, load_users, delete_user, update_user


from app.core.config import BASE_URL_LLM, MAX_DOC_PAGES, DocumentType, logger, MAX_UPLOAD_BYTES
from app.core.doc_prompt import DOCUMENT_PROMPTS
from app.services.pdf import PageImage, extract_pages
from app.services.semantic import run_semantic
from app.utils.call_log import create_call_log
from app.utils.image import validate_file_content

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


UploadFile = Annotated[UF, WithJsonSchema({"type": "string", "format": "binary"})]

app = FastAPI(
    title="Document OCR API",
    description=(
        "High-precision document OCR powered by PaddleOCR + Qwen2.5 text-only semantic mapping.\n\n"
        "Accepts images or PDFs, runs high-precision local OCR, and maps fields semantically using the LLM.\n\n"
        "Supported document types: " + ", ".join(DOCUMENT_PROMPTS.keys())
    ),
    version="6.0.0",
    docs_url=None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
class LoginRequest(BaseModel):
    nomor_badge: str
    password: str

class UserCreateRequest(BaseModel):
    username: str
    password: str
    employee: str
    role: str = "user"

class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    employee: Optional[str] = None

@app.on_event("startup")
def startup_event():
    from app.utils.user_db import init_default_admin
    init_default_admin()



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

async def safe_read(upload: UploadFile):
    chunks = []
    total = 0
    chunk_size = 64 * 1024
    while True:
        chunk = await upload.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail={
                "success": False,
                "error_type": "too_large_file",
                "message": f"File melebihi batas maksimum {MAX_UPLOAD_BYTES // 1024 // 1024}MB."
            })
        chunks.append(chunk)
    return b"".join(chunks)

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

    validated_files = []
    pdf_count = 0

    for upload in files:
        raw_bytes = await safe_read(upload)
        mime = validate_file_content(raw_bytes, upload.filename)
        if mime == "application/pdf":
            pdf_count += 1
        validated_files.append((upload, raw_bytes, mime))

    if pdf_count > 1:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error_type": "multiple_pdfs",
                "message": "Only a single PDF file is allowed.",
            },
        )

    image_count = 0
    image_pages: List[PageImage] = []

    for upload, raw_bytes, mime in validated_files:
        try:
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
                # Keep original page numbers from PDF
                for page in pdf_pages:
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
@limiter.limit("20/minute")
async def process_ocr_document(
    request: Request,
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
    current_user: dict = Depends(get_current_user),
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

        # Explicitly close PIL images to free memory
        for p in page_images:
            if "image" in p and p["image"]:
                try:
                    p["image"].close()
                except Exception:
                    pass

        # Remove heavy base64 log from the user-facing response
        result.pop("messages_log", None)
        return result


@app.post(
    "/ocr/process/fields",
    summary="Extract specific custom fields",
    tags=["OCR"],
)
@limiter.limit("20/minute")
async def process_ocr_fields(
    request: Request,
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
    current_user: dict = Depends(get_current_user),
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

    # Explicitly close PIL images to free memory
    for p in page_images:
        if "image" in p and p["image"]:
            try:
                p["image"].close()
            except Exception:
                pass

    # Remove heavy base64 log from the user-facing response
    result.pop("messages_log", None)
    return result


@app.post(
    "/ocr/process/prompt",
    summary="Extract using a custom prompt",
    tags=["OCR"],
)
@limiter.limit("20/minute")
async def process_ocr_prompt(
    request: Request,
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
    current_user: dict = Depends(get_current_user),
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

    # Explicitly close PIL images to free memory
    for p in page_images:
        if "image" in p and p["image"]:
            try:
                p["image"].close()
            except Exception:
                pass

    # Remove heavy base64 log from the user-facing response
    result.pop("messages_log", None)
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

    # Define helper to process a single sub-document
    async def process_single_doc(doc_type: str, upload_file: UploadFile, pages_rule: str):
        file_pages = await _process_files([upload_file], pages=pages_rule, document_type=doc_type)
        result = await run_semantic(doc_type, file_pages, None, "", show_only_mismatch=show_only_mismatch)
        data = result.get("data", {}) if result.get("success") else {}
        data = data or {}
        return file_pages, result, data

    # Process all sub-documents in parallel
    (
        (bl_file_pages, bl_result, bl_data),
        (peb_file_pages, peb_result, peb_data),
        (pl_file_pages, pl_result, pl_data),
        (inv_file_pages, inv_result, inv_data)
    ) = await asyncio.gather(
        process_single_doc("BL", classified["BL"], "1"),
        process_single_doc("PEB", classified["PEB"], "-2"),
        process_single_doc("PL", classified["PL"], "1"),
        process_single_doc("INV_COO", classified["INV_COO"], "1")
    )

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

    # Explicitly close PIL images to free memory
    for pages_data in [bl_file_pages, peb_file_pages, pl_file_pages, inv_file_pages]:
        for p in pages_data:
            if "image" in p and p["image"]:
                try:
                    p["image"].close()
                except Exception:
                    pass

    return result_output


@app.get("/health")
async def health_check():
    base_info = {
        "vllm_max_model_len": 11000,
        "max_image_size": "N/A",
        "max_images_per_request": MAX_DOC_PAGES,
    }
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{BASE_URL_LLM}/health", timeout=5.0)
            if resp.status_code == 200:
                return {"status": "Healthy", "model_ready": True, **base_info}
        return {"status": f"Unhealthy (HTTP {resp.status_code})", "model_ready": False, **base_info}
    except httpx.ConnectError:
        return {"status": "vLLM server not reachable", "model_ready": False, **base_info}
    except httpx.TimeoutException:
        return {"status": "vLLM server timeout", "model_ready": False, **base_info}

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


@app.post("/api/auth/login", tags=["Authentication"])
async def login(payload: LoginRequest):
    user = get_user(payload.nomor_badge)
    if not user or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "error_type": "invalid_credentials",
                "message": "Nomor badge atau password salah.",
            }
        )
    
    token_data = {
        "username": user["username"],
        "role": user["role"],
        "employee": user["employee"]
    }
    token = create_access_token(token_data)
    return {
        "success": True,
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "username": user["username"],
            "role": user["role"],
            "employee": user["employee"]
        }
    }

@app.get("/api/users", tags=["User Management"])
async def get_all_users(current_admin: dict = Depends(get_current_admin)):
    users = load_users()
    safe_users = []
    for u in users:
        safe_users.append({
            "username": u["username"],
            "employee": u["employee"],
            "role": u["role"]
        })
    return {"success": True, "users": safe_users}

@app.post("/api/users", tags=["User Management"])
async def create_user(payload: UserCreateRequest, current_admin: dict = Depends(get_current_admin)):
    if payload.role not in ("admin", "user"):
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error_type": "invalid_role",
                "message": "Role harus berupa 'admin' atau 'user'.",
            }
        )
    
    add_user(
        username=payload.username,
        plain_password=payload.password,
        employee=payload.employee,
        role=payload.role
    )
    return {
        "success": True,
        "message": f"Pengguna '{payload.username}' berhasil dibuat."
    }

@app.delete("/api/users/{username}", tags=["User Management"])
async def delete_user_endpoint(username: str, current_admin: dict = Depends(get_current_admin)):
    if username.lower() == current_admin["username"].lower():
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error_type": "cannot_delete_self",
                "message": "Anda tidak diperbolehkan menghapus akun Anda sendiri.",
            }
        )
    
    success = delete_user(username)
    if not success:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error_type": "user_not_found",
                "message": f"Pengguna '{username}' tidak ditemukan.",
            }
        )
        
    return {
        "success": True,
        "message": f"Pengguna '{username}' berhasil dihapus."
    }

@app.put("/api/users/{employee}", tags=["User Management"])
async def update_user_endpoint(
    employee: str,
    payload: UserUpdateRequest,
    current_admin: dict = Depends(get_current_admin)
):
    if payload.role and payload.role not in ("admin", "user"):
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error_type": "invalid_role",
                "message": "Role harus berupa 'admin' atau 'user'.",
            }
        )
    
    updated = update_user(
        employee=employee,
        username=payload.username,
        plain_password=payload.password,
        role=payload.role,
        new_employee=payload.employee
    )
    if not updated:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error_type": "user_not_found",
                "message": f"Pengguna dengan Nomor Badge '{employee}' tidak ditemukan.",
            }
        )
    return {
        "success": True,
        "message": f"Pengguna dengan Nomor Badge '{employee}' berhasil diperbarui.",
        "user": {
            "username": updated["username"],
            "employee": updated["employee"],
            "role": updated["role"]
        }
      }


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", "5030"))
    uvicorn.run(app, host="0.0.0.0", port=port)

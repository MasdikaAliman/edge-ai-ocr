import base64
import io
from typing import Any, Dict, List

from fastapi import HTTPException
from PIL import Image

from app.core.config import ALLOWED_MIME_TYPES, MAX_IMAGE_SIZE


def pil_to_content_item(img: Image.Image) -> Dict[str, Any]:
    img = img.convert("RGB")
    # if max(img.size) > MAX_IMAGE_SIZE:
    #     img.thumbnail((MAX_IMAGE_SIZE, MAX_IMAGE_SIZE), Image.LANCZOS)
    with io.BytesIO() as buf:
        img.save(buf, format="PNG")
        print(img.format)
        b64 = base64.b64encode(buf.getvalue()).decode()
    return {"type": "image_url",
     "image_url": {"url": f"data:image/png;base64,{b64}"}
     }


def detect_mime_type(raw_bytes: bytes) -> str:
    """
    Detects the MIME type of a file based on its magic bytes (file signature).
    Returns the MIME type string if recognized, otherwise 'application/octet-stream'.
    """
    if len(raw_bytes) < 4:
        return "application/octet-stream"

    # PDF: %PDF
    if raw_bytes.startswith(b"%PDF"):
        return "application/pdf"

    # PNG: \x89PNG\r\n\x1a\n
    if raw_bytes.startswith(b"\x89PNG"):
        return "image/png"

    # JPEG: \xff\xd8\xff
    if raw_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"

    # WebP: RIFFxxxxWEBP
    if raw_bytes.startswith(b"RIFF") and len(raw_bytes) >= 12 and raw_bytes[8:12] == b"WEBP":
        return "image/webp"

    # GIF: GIF87a or GIF89a
    if raw_bytes.startswith(b"GIF8"):
        return "image/gif"

    # TIFF: II*\x00 (little endian) or MM\x00* (big endian)
    if raw_bytes.startswith(b"II\x2a\x00") or raw_bytes.startswith(b"MM\x00\x2a"):
        return "image/tiff"

    return "application/octet-stream"


def validate_file_content(raw_bytes: bytes, filename: str) -> str:
    """
    Validates file content using magic bytes and returns the detected MIME type.
    Raises HTTPException (415 or 400) if invalid or unsupported.
    """
    if not raw_bytes:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error_type": "empty_file",
                "message": f"Uploaded file '{filename}' is empty.",
            },
        )

    mime = detect_mime_type(raw_bytes)

    if mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail={
                "success": False,
                "error_type": "unsupported_media_type",
                "message": (
                    f"File '{filename}' has an unsupported or invalid file type. "
                    f"Accepted types: {', '.join(sorted(ALLOWED_MIME_TYPES))}."
                ),
            },
        )

    return mime


def bytes_to_content_item(raw_bytes: bytes, content_type: str = "") -> Dict[str, Any]:
    mime = validate_file_content(raw_bytes, "file")
    with io.BytesIO(raw_bytes) as src:
        img = Image.open(src)
        img.load()
    return pil_to_content_item(img)



def validate_content(content: List[Dict[str, Any]]) -> None:
    for item in content:
        if item.get("type") == "image_url":
            url: str = item["image_url"]["url"]
            if url.startswith(("http://", "https://")):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "error_type": "url_not_allowed",
                        "message": (
                            "External image URLs are not supported. "
                            "Send images as base64 data URIs or upload via multipart/form-data."
                        ),
                    },
                )

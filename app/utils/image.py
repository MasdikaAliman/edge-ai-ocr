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


def bytes_to_content_item(raw_bytes: bytes, content_type: str) -> Dict[str, Any]:
    mime = content_type.split(";")[0].strip().lower()
    if mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail={
                "success": False,
                "error_type": "unsupported_media_type",
                "message": (
                    f"File type '{mime}' is not supported. "
                    f"Accepted types: {', '.join(sorted(ALLOWED_MIME_TYPES))}."
                ),
            },
        )
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

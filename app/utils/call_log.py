import base64
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from app.core.config import logger

CALL_LOG_DIR = os.getenv("CALL_LOG_DIR", "call_logs")
CALL_LOG_ENABLED = os.getenv("CALL_LOG_ENABLED", "true").lower() in ("true", "1", "yes")


def _serialize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(v) for v in obj]
    if isinstance(obj, bytes):
        try:
            return base64.b64encode(obj).decode("utf-8")
        except Exception:
            return "<binary data>"
    if hasattr(obj, "__class__") and obj.__class__.__name__ in ("SystemMessage", "HumanMessage", "AIMessage"):
        return {"type": obj.__class__.__name__, "content": str(obj.content)}
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)


def create_call_log(
    request_data: Dict[str, Any],
    pdf_result: List[Dict[str, Any]],
    messages_sent: List[Dict[str, Any]],
    output: Dict[str, Any],
) -> str:
    if not CALL_LOG_ENABLED:
        return ""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    call_dir = Path(CALL_LOG_DIR) / timestamp
    call_dir.mkdir(parents=True, exist_ok=True)

    log_data = {
        "timestamp": timestamp,
        "request": request_data,
        "pdf_result": pdf_result,
        "messages_sent": messages_sent,
        "output": output,
    }

    log_file = call_dir / "call.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(_serialize(log_data), f, indent=2, ensure_ascii=False)

    _save_images(call_dir, pdf_result)

    logger.info("Call log saved to: %s", call_dir)
    return str(call_dir)


def _save_images(call_dir: Path, pdf_result: List[Dict[str, Any]]) -> None:
    for i, page in enumerate(pdf_result, 1):
        page_dir = call_dir / f"page_{i}"
        page_dir.mkdir(exist_ok=True)

        if "image" in page and isinstance(page["image"], dict):
            _save_image(page_dir, page["image"], "page_image")

        for j, table_img in enumerate(page.get("table_images", []), 1):
            if isinstance(table_img, dict):
                _save_image(page_dir, table_img, f"table_{j}")


def _save_image(output_dir: Path, image_data: Dict[str, Any], name: str) -> None:
    try:
        img_bytes = base64.b64decode(image_data.get("image_bytes", ""))
        mime = image_data.get("mime_type", "image/png")
        ext = mime.split("/")[-1]
        path = output_dir / f"{name}.{ext}"
        with open(path, "wb") as f:
            f.write(img_bytes)
    except Exception as e:
        logger.warning("Failed to save image %s: %s", name, e)
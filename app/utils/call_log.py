import base64
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from app.core.config import logger

CALL_LOG_DIR = os.getenv("CALL_LOG_DIR", "call_logs")
CALL_LOG_ENABLED = os.getenv("CALL_LOG_ENABLED", "true").lower() in ("true", "1", "yes")


class MessageSerializer:
    def __init__(self, call_dir: Path):
        self.call_dir = call_dir
        self.image_counter = 0
        self.saved_images: List[Dict[str, Any]] = []

    def serialize(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            if obj.get("type") == "image_url":
                self.image_counter += 1
                img_id = f"<image_{self.image_counter}>"
                img_bytes = obj.get("image_url", {}).get("url", "")
                if img_bytes.startswith("data:"):
                    img_bytes = img_bytes.split(",", 1)[-1]
                self._save_image_bytes(img_bytes, f"message_image_{self.image_counter}")
                return {"type": "image_url", "url": img_id}
            return {k: self.serialize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.serialize(v) for v in obj]
        if isinstance(obj, bytes):
            try:
                return base64.b64encode(obj).decode("utf-8")
            except Exception:
                return "<binary data>"
        if hasattr(obj, "__class__") and obj.__class__.__name__ in ("SystemMessage", "HumanMessage", "AIMessage"):
            return {"type": obj.__class__.__name__, "content": self.serialize(obj.content)}
        try:
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            return str(obj)

    def _save_image_bytes(self, b64_data: str, name: str) -> None:
        try:
            if not b64_data:
                logger.warning("No image data for %s", name)
                return
            img_bytes = base64.b64decode(b64_data)
            if len(img_bytes) == 0:
                logger.warning("Decoded 0 bytes for %s", name)
                return
            path = self.call_dir / f"{name}.jpg"
            with open(path, "wb") as f:
                f.write(img_bytes)
            self.saved_images.append({"id": f"<image_{self.image_counter}>", "file": str(path)})
        except Exception as e:
            logger.warning("Failed to save message image %s: %s", name, e)


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

    serializer = MessageSerializer(call_dir)
    log_data = {
        "timestamp": timestamp,
        "request": request_data,
        "pdf_result": pdf_result,
        "messages_sent": [serializer.serialize(msg) for msg in messages_sent],
        "output": output,
        "image_references": serializer.saved_images,
    }

    log_file = call_dir / "call.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)

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
        url = image_data.get("image_url", {}).get("url", "")
        if not url:
            img_bytes = base64.b64decode(image_data.get("image_bytes", ""))
        elif url.startswith("data:"):
            img_bytes = base64.b64decode(url.split(",", 1)[-1])
        else:
            img_bytes = base64.b64decode(url)
        mime = image_data.get("mime_type", "image/jpeg")
        ext = mime.split("/")[-1]
        path = output_dir / f"{name}.{ext}"
        with open(path, "wb") as f:
            f.write(img_bytes)
    except Exception as e:
        logger.warning("Failed to save image %s: %s", name, e)
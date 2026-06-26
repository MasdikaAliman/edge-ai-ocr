import logging
import os
from typing import Literal
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

MAX_DOC_PAGES = int(os.getenv("MAX_DOC_PAGES", "20"))
MAX_IMAGE_SIZE = int(os.getenv("MAX_IMAGE_SIZE", "1024"))
ENABLE_PADDLEOCR = os.getenv("ENABLE_PADDLEOCR", "true").lower() in ("true", "1", "yes")
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/tiff", "application/pdf"}

BASE_URL_LLM = os.getenv("BASE_URL_LLM", "http://localhost:1234")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-2B-Instruct")

DocumentType = Literal["KTP", "KK", "NPWP", "Invoice_SPBB", "Quotation", "SIM", "IJAZAH", "BL", "INV_COO", "PEB", "PL", "COO"]

PYMUPDF_DPI = int(os.getenv("PYMUPDF_DPI", "200"))
PADDLE_USE_GPU = os.getenv("PADDLE_USE_GPU", "true").lower() in ("true", "1", "yes")
PADDLE_OCR_LANG = os.getenv("PADDLE_OCR_LANG", "en")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", "52428800"))

from langchain.chat_models import init_chat_model
model = init_chat_model(
    model=MODEL_NAME,
    model_provider="openai",
    base_url=f"{BASE_URL_LLM}/v1",
    api_key="EMPTY",
    temperature=0.0,
    top_p=0.95,
    extra_body={
        "top_k": 1,
        "mm_processor_kwargs": {
            "min_pixels": 512*32*32,
            "max_pixels": 2048*32*32
        }
    }
)
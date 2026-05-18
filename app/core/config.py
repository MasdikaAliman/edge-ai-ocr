import logging
import os
from typing import Literal
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

MAX_IMAGES = int(os.getenv("MAX_IMAGES", "5"))
MAX_IMAGE_SIZE = int(os.getenv("MAX_IMAGE_SIZE", "1024"))
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/tiff", "application/pdf"}

BASE_URL_LLM = os.getenv("BASE_URL_LLM", "http://localhost:1234")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen/qwen3-vl-4b")

DocumentType = Literal["KTP", "KK", "NPWP", "Invoice", "Quotation", "SIM"]

model = init_chat_model(
    model=MODEL_NAME,
    model_provider="openai",
    base_url=f"{BASE_URL_LLM}/v1",
    api_key="EMPTY",
    temperature=0.0,
)

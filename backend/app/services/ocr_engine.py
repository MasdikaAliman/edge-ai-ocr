import sys
import types
from typing import TypedDict, List, Any

# Mock legacy langchain modules required by paddleocr/paddlex internal code
try:
    from langchain_core.documents import Document
    docstore = types.ModuleType("langchain.docstore")
    docstore_document = types.ModuleType("langchain.docstore.document")
    docstore_document.Document = Document
    docstore.document = docstore_document
    sys.modules["langchain.docstore"] = docstore
    sys.modules["langchain.docstore.document"] = docstore_document
    
    class RecursiveCharacterTextSplitter:
        pass
        
    text_splitter = types.ModuleType("langchain.text_splitter")
    text_splitter.RecursiveCharacterTextSplitter = RecursiveCharacterTextSplitter
    sys.modules["langchain.text_splitter"] = text_splitter
except ImportError:
    pass
import os
import numpy as np
from PIL import Image

# Disable MKLDNN/oneDNN prior to PaddlePaddle imports to prevent PIR crashes on CPU
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

# Configure PaddlePaddle memory strategy to optimize GPU memory allocation on Jetson Orin NX
os.environ["FLAGS_allocator_strategy"] = "auto_growth"
os.environ["FLAGS_fraction_of_gpu_memory_to_use"] = "0.15"
os.environ["FLAGS_eager_delete_tensor_gb"] = "0.0"

from app.core.config import logger, PADDLE_USE_GPU, PADDLE_OCR_LANG
from paddleocr import PaddleOCR
import threading

_lock = threading.Lock()
_ocr_instance = None




class OCRFragment(TypedDict):
    text: str
    bbox: List[int]       # [x_min, y_min, x_max, y_max] absolute pixels
    confidence: float     # 0.0 – 1.0 from PaddleOCR recognition score
    page_no: int

def get_ocr_engine():
    global _ocr_instance
    if _ocr_instance is None:
        with _lock:
            if _ocr_instance is None:  # Check ulang setelah acquire lock
                _ocr_instance = PaddleOCR(
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=False,
                    enable_mkldnn=False,
                    device="gpu" if PADDLE_USE_GPU else "cpu",
                    enable_hpi=True,
                    precision="fp16",
                    engine="paddle_static",
                )
    return _ocr_instance

def run_ocr_on_image(image: Image.Image, page_no: int) -> List[OCRFragment]:
    """Run PaddleOCR on a PIL Image and return absolute coordinates OCRFragments."""
    ocr = get_ocr_engine()
    if ocr is None:
        return []

    # Convert PIL Image to RGB numpy array
    img_np = np.array(image.convert("RGB"))

    try:
        # PaddleOCR predict accepts numpy array
        result = ocr.predict(img_np)
        fragments: List[OCRFragment] = []

        for res in result:
            # Check structure of result.
            # Usually, PaddleOCR in predict mode returns objects with rec_texts, rec_scores, rec_boxes
            rec_texts = res.get("rec_texts", [])
            rec_scores = res.get("rec_scores", [])
            rec_boxes = res.get("rec_boxes", [])

            for text, score, box in zip(rec_texts, rec_scores, rec_boxes):
                # PaddleOCR boxes are normally 4-point polygons: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                # or [xmin, ymin, xmax, ymax]
                # Let's normalize it to [x_min, y_min, x_max, y_max] absolute coordinates
                if len(box) == 4:
                    if isinstance(box[0], (list, tuple, np.ndarray)):
                        # It is [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                        xs = [pt[0] for pt in box]
                        ys = [pt[1] for pt in box]
                        xmin, ymin, xmax, ymax = min(xs), min(ys), max(xs), max(ys)
                    else:
                        # It is [xmin, ymin, xmax, ymax]
                        xmin, ymin, xmax, ymax = box
                    
                    fragments.append({
                        "text": str(text),
                        "bbox": [int(xmin), int(ymin), int(xmax), int(ymax)],
                        "confidence": round(float(score), 4),
                        "page_no": page_no
                    })
        return fragments
    except Exception as e:
        logger.error("Error executing PaddleOCR on page %d: %s", page_no, e)
        return []

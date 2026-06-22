# MIGRATION PLAN — PaddleOCR + LLM Semantic Flow

## Overview

```
BEFORE:
Image/PDF → PyMuPDF/Docling → Qwen3-VL (OCR + bbox + semantic) → output

AFTER:
Image/PDF → PyMuPDF (render) → PaddleOCR (OCR + bbox + confidence) → LLM text-only (semantic) → output
```

### Why This Change

The previous flow asked Qwen3-VL to do two things in a single inference: read text from the document
AND determine pixel-accurate bounding box coordinates for every field. For an 8B model this is
too demanding — the model frequently "hallucinates" coordinates rather than precisely detecting them.

The new flow gives each component one clear responsibility:

| Component | Responsibility |
|---|---|
| PyMuPDF | Render PDF pages to PIL images at a fixed DPI |
| PaddleOCR | Detect and recognize text — outputs real bbox + confidence |
| LLM (text-only) | Semantic understanding only — maps OCR fragments to requested fields |

---

## Scope of Changes

### Files to Delete
- `app/services/pipeline.py` — entire LangGraph flow replaced
- `app/core/sys_prompt.py` — GROUNDING_RULE no longer relevant, bbox schema changes

### Files with Major Changes
- `app/services/pdf.py` — remove Docling, replace with PyMuPDF render only
- `app/core/config.py` — model init changes from VL to text-only
- `app/core/sys_prompt.py` — remove all `bbox_2d` grounding schemas, update to new output schema
- `main.py` — endpoints unchanged (backward compatible), internal pipeline rewired
- `requirements.txt` — add paddleocr/paddlepaddle, remove docling and langgraph

### New Files
- `app/services/ocr_engine.py` — PaddleOCR singleton wrapper
- `app/services/ocr_grouping.py` — group OCR fragments into readable lines for LLM
- `app/services/semantic.py` — LLM semantic field matching (replaces pipeline.py)
- `app/core/semantic_prompt.py` — prompts for text-only semantic extraction

### Files with Minor Changes
- `app/core/doc_prompt.py` — remove grounding schema references at the end of each prompt
- `app/core/coo_prompt.py` — same
- `app/core/spbb_prompt.py` — same
- `app/core/quatation_prompt.py` — same
- `frontend/src/components/DocumentPreviewer.jsx` — update bbox key names and coordinate handling
- `frontend/src/components/ResultViewer.jsx` — update cleanGroundingResult() for new schema

### Files Unchanged
- `app/utils/errors.py`
- `app/utils/call_log.py`
- `app/utils/image.py`
- `app/utils/parsing.py`
- `app/utils/fileSystem.js`
- All other frontend files
- `main.py` endpoint signatures (fully backward compatible)

---

## Phase 1 — Dependencies & Configuration

### 1.1 Update `requirements.txt`

```
# REMOVE
docling
langchain
langchain-core
langchain-openai
langchain-community
langgraph

# ADD
paddlepaddle-gpu>=3.2.1    # use paddlepaddle for CPU-only
paddleocr>=3.4.0
PyMuPDF>=1.23.0     # fitz — likely already installed, verify version

# KEEP
fastapi
uvicorn[standard]
python-multipart
requests
pydantic
pydantic-settings
python-dotenv
Pillow
```

### 1.2 Update `.env.example`

```bash
# LLM Backend Configuration
BASE_URL_LLM=http://localhost:8000
MODEL_NAME=Qwen/Qwen2.5-2B-Instruct   # changed from qwen3-vl

# Server Configuration
PORT=5030
LOG_LEVEL=INFO

# OCR Limits
MAX_DOC_PAGES=20
PYMUPDF_DPI=200            # NEW — render DPI for PDF pages

# PaddleOCR Configuration (NEW)
PADDLE_OCR_LANG=en         # en, ch, latin — use 'en' for mixed docs
PADDLE_USE_GPU=true
PADDLE_DET_MODEL_DIR=./models/paddle/det
PADDLE_REC_MODEL_DIR=./models/paddle/rec
PADDLE_CLS_MODEL_DIR=./models/paddle/cls (FOR NOW USE THE CACHE INSTEAD OF DOWNLOADING THE MODELS)
```

### 1.3 Update `app/core/config.py`

```python
from langchain.chat_models import init_chat_model
model = init_chat_model(
    model=MODEL_NAME,
    model_provider="openai",
    ...
    model_kwargs={"extra_body": {"mm_processor_kwargs": {...}}}  # VL-specific, no longer needed
)
LLM_MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-2B-Instruct")
PYMUPDF_DPI = int(os.getenv("PYMUPDF_DPI", "200"))
PADDLE_USE_GPU = os.getenv("PADDLE_USE_GPU", "true").lower() in ("true", "1", "yes")
PADDLE_OCR_LANG = os.getenv("PADDLE_OCR_LANG", "en")

```

---

## Phase 2 — OCR Engine

### 2.1 Create `app/services/ocr_engine.py`

**Responsibilities:**
- Singleton PaddleOCR instance — initialize once, reuse across requests
- Accept a PIL Image, return a list of `OCRFragment`
- Convert PaddleOCR's 4-point polygon bbox → `[x_min, y_min, x_max, y_max]` absolute pixels

**Output data structure:**

```python
class OCRFragment(TypedDict):
    text: str
    bbox: list[int]       # [x_min, y_min, x_max, y_max] absolute pixels
    confidence: float     # 0.0 – 1.0 from PaddleOCR recognition score
    page_no: int
```

**Key implementation notes:**
- PaddleOCR returns polygon as `[[x1,y1],[x2,y2],[x3,y3],[x4,y4]]` — normalize with `min/max`
- PaddleOCR instance should be initialized at module level (singleton), not per request

### 2.2 Create `app/services/ocr_grouping.py`

**Responsibilities:**
- Accept `List[OCRFragment]` for a single page
- Group fragments whose Y-center values are within a threshold (~12px) into the same line
- Within each line, sort fragments left to right (X ascending)
- Concatenate fragments per line into a single string
- Return both the formatted string for LLM and a mapping back to original fragments

**Output format for LLM input:**

```
Line 1  [y:120]: "Invoice No : INV-2024-001"
Line 2  [y:145]: "Date : 15 January 2025"
Line 3  [y:170]: "Bill To : PT Maju Bersama"
Line 4  [y:220]: "Item  Qty  Unit Price  Amount"
Line 5  [y:240]: "Steel Pipe 100  USD 2.50  USD 250.00"
```

**Fragment mapping structure** (used after LLM returns field selection):

```python
# key = line index, value = list of fragments that make up that line
line_fragment_map: dict[int, list[OCRFragment]]
```

This mapping is critical — when the LLM says "invoice_number is on line 2", we look up
`line_fragment_map[2]` to get the actual bbox and confidence values from PaddleOCR.

### 2.3 Modify `app/services/pdf.py`

**Remove:**
- `_run_docling()` and all Docling imports
- `TableStructureOptions`, `AcceleratorOptions`, `AcceleratorDevice`
- `generate_page_images`, `generate_table_images`, `generate_picture_images`
- `_run_pdfplumber()` — no longer needed as fallback (PyMuPDF handles rendering)
- `extract_colored_text()` — no longer needed (PaddleOCR handles text extraction)

**Keep:**
- `parse_page_filter()` — logic unchanged
- `extract_pages()` — signature unchanged, internal implementation replaced

**New `PageImage` structure:**

```python
class PageImage(TypedDict):
    page_no: int
    image: Any          # PIL.Image
    width: int          # rendered pixel width
    height: int         # rendered pixel height
```

**New `extract_pages()` implementation:**
- Use `fitz.open()` to load PDF
- Render each page with `page.get_pixmap(dpi=PYMUPDF_DPI)`
- Convert pixmap to PIL Image
- Apply `parse_page_filter()` to select requested pages
- Return `List[PageImage]`

---

## Phase 3 — Semantic LLM Layer

### 3.1 Create `app/core/semantic_prompt.py`

Three prompt builders for three extraction modes:

**`get_doctype_semantic_prompt(doc_type, schema)`**
- Tell the LLM what document type it is
- Provide the expected field list and their descriptions
- Instruct LLM to return `{field_name: {text, line_ref, confidence_override}}` JSON
- `line_ref` = the line number in the grouped text where this field was found

**`get_fields_semantic_prompt(fields)`**
- Provide user-defined field list in snake_case
- Same JSON output structure

**`get_custom_semantic_prompt(custom_prompt)`**
- Prepend user's custom instruction
- OCR lines provided as context

**Critical instruction in all prompts:**
```
You are given OCR-extracted text lines from a document.
Your ONLY task is to identify which line contains each requested field.
Do NOT generate or modify any text values.
Do NOT invent bounding box coordinates.
Return the exact text as it appears in the OCR output.
For each field, return: {"text": "...", "line_ref": <line_number>}
If a field is not found, return null for that field.
```

### 3.2 Create `app/services/semantic.py`

This replaces `pipeline.py`. No LangGraph — simple async function.

**Full processing flow:**

```
Input:
  - document_type / fields / custom_prompt
  - List[OCRFragment] (all pages combined)
  - line_fragment_map per page

Step 1 — Group fragments per page:
  For each page: ocr_grouping.group_by_line(fragments) → (lines_string, fragment_map)

Step 2 — Build LLM prompt:
  Combine all page lines into one context string with page markers
  Select appropriate prompt based on mode (doc_type / fields / custom)

Step 3 — Call LLM (text-only, no image):
  POST to vLLM /v1/chat/completions
  Model: Qwen2.5-2B-Instruct
  Response: JSON with {field_name: {text, line_ref}} per field

Step 4 — Resolve bbox from fragment map:
  For each field the LLM returned:
    → Look up line_ref in fragment_map
    → Get bbox and confidence from the actual PaddleOCR fragments on that line
    → If multiple fragments on the line, compute union bbox

Step 5 — Build final output:
  {
    "field_name": {
      "text": "INV-2024-001",
      "bbox": [234, 118, 456, 138],    # real pixel coords from PaddleOCR
      "confidence": 0.987               # real confidence from PaddleOCR
    }
  }
```

**Multi-page aggregation:**
- For scalar fields: take the result with highest confidence across pages
- For array fields (tables): merge all pages, deduplicate by text similarity
- No LLM aggregation step needed — deterministic merge is sufficient for text-only results

---

## Phase 4 — Wire Up `main.py`

### 4.1 New internal flow

The three public endpoints keep identical signatures. Only the internal calls change:

```python
# BEFORE
async def process_ocr_document(files, document_type, pages):
    image_pages = await _process_files(files, pages, document_type)
    result = await run_ocr(document_type, image_pages, None, "")
    ...

# AFTER
async def process_ocr_document(files, document_type, pages):
    page_images = await render_pages(files, pages)          # PyMuPDF only
    fragments = await run_paddle_ocr(page_images)           # PaddleOCR
    result = await run_semantic(document_type, fragments, fields=None, custom_prompt="")
    ...
```

### 4.2 Simplify `_process_files()`

Remove all Docling and colored text logic. This function now only:
- Validates file count and MIME types
- Calls `extract_pages()` from the updated `pdf.py`
- Returns `List[PageImage]`

### 4.3 COO flow unchanged at merge level

The four-document merge logic in `process_ocr_coo_document()` remains programmatic.
Only the per-document extraction calls change to use the new `run_semantic()`.

---

## Phase 5 — Output Schema Changes

### 5.1 New response structure

```jsonc
// BEFORE — bbox generated by VL model (unreliable)
{
  "success": true,
  "data": {
    "invoice_number": {
      "value": "INV-2024-001",
      "bbox_2d": [234, 118, 456, 138]
    }
  }
}

// AFTER — bbox from PaddleOCR (pixel-accurate), confidence is real
{
  "success": true,
  "data": {
    "invoice_number": {
      "text": "INV-2024-001",
      "bbox": [234, 118, 456, 138],
      "confidence": 0.987
    }
  }
}
```

### 5.2 Update `app/core/sys_prompt.py`

- Remove `GROUNDING_RULE` constant entirely
- Remove `bbox_2d` from all schema definitions (KTP_SCHEMA, INVOICE_SCHEMA, etc.)
- Schemas are no longer embedded in prompts — they move to `semantic_prompt.py`
- Keep `BASE_DIRECTIVES`, `_CURRENCY_RULE`, `_DATE_RULE`, `NUMERIC_RULE`

### 5.3 Update `frontend/src/components/DocumentPreviewer.jsx`

```javascript
// BEFORE
function findBboxLeaves(val, currentKey) {
  if ("bbox_2d" in val) {  // old key
    return [{ key, bbox_2d: val.bbox_2d, value: val.value }]
  }
}
// Coordinate conversion: (x1_norm / 999) * width  ← wrong normalization

// AFTER
function findBboxLeaves(val, currentKey) {
  if ("bbox" in val && "text" in val) {  // new schema
    return [{ key, bbox: val.bbox, confidence: val.confidence, text: val.text }]
  }
}
// Coordinate conversion: bbox is already absolute pixels
// Need to scale by (rendered_canvas_size / original_image_size)
```

The bboxes are now absolute pixel coordinates from the PyMuPDF render (at `PYMUPDF_DPI`).
The frontend needs to know the original render dimensions to scale correctly to the canvas display size.
Include `page_width` and `page_height` in the response so the frontend can compute the scale factor.

### 5.4 Update `frontend/src/components/ResultViewer.jsx`

```javascript
// BEFORE
function cleanGroundingResult(obj) {
  if ("value" in obj && "bbox_2d" in obj) return obj.value;
}

// AFTER
function cleanGroundingResult(obj) {
  if ("text" in obj && "bbox" in obj) return obj.text;
}
```

---

## Phase 6 — Testing

### 6.1 New unit tests

**`tests/test_ocr_engine.py`**
- Test PaddleOCR wrapper with a sample document image
- Verify polygon → xyxy conversion is correct
- Verify confidence filtering works

**`tests/test_ocr_grouping.py`**
- Test line grouping with mock fragments at various Y positions
- Verify fragments within threshold are merged into one line
- Verify sort order within a line is left-to-right
- Verify fragment map keys match grouped line indices

**`tests/test_semantic.py`**
- Mock LLM response and fragment map
- Verify bbox resolution from line_ref is correct
- Verify multi-page merge picks highest confidence value for scalar fields

### 6.2 Update `tests/test_main.py`

```python
# REPLACE these mocks
@patch("main._process_files")
@patch("main.run_ocr")

# WITH these mocks
@patch("main.render_pages")
@patch("main.run_paddle_ocr")
@patch("main.run_semantic")
```

---

## Implementation Order

```
1.  requirements.txt + .env.example
2.  app/core/config.py
3.  app/services/ocr_engine.py
4.  app/services/ocr_grouping.py
5.  app/services/pdf.py  (strip Docling)
6.  app/core/semantic_prompt.py
7.  app/services/semantic.py
8.  main.py  (wire up new flow)
9.  app/core/sys_prompt.py  (remove grounding schemas)
10. app/core/doc_prompt.py + coo + spbb + quatation  (remove schema refs)
11. frontend/src/components/DocumentPreviewer.jsx
12. frontend/src/components/ResultViewer.jsx
13. tests/
```

---

## Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| PaddleOCR fails on low-quality scans | Medium | Add contrast/sharpen pre-processing in `ocr_engine.py` before passing to Paddle |
| Qwen2.5-2B misidentifies fields on ambiguous layouts | Medium | Add confidence threshold — if LLM is uncertain, return `null` not a guess |
| Complex table layouts break Y-axis line grouping | High | Detect table regions via bbox clustering, treat as separate block with dedicated grouping |
| COO multi-document merge breaks | Low | Merge logic in `main.py` is programmatic and independent of OCR engine |
| Frontend overlay misaligned after coordinate change | Medium | Pass `page_width` and `page_height` in response; frontend divides bbox by these to get relative position |
| PaddleOCR model download on first run | Low | Pre-download models to `./models/paddle/` and point env vars to local path |
| Qwen2.5-2B context window too small for long documents | Medium | Limit lines sent to LLM per page; split into chunks if line count exceeds 200 |
# SYSTEM_MAP — Edge AI OCR

---

## Project Summary

**Tujuan Aplikasi**
Sistem OCR dokumen berbasis multimodal AI lokal (edge deployment). Menerima gambar atau PDF, mengekstraksi field terstruktur ke JSON, dan mengekspornya ke Excel. Mendukung dokumen Indonesia (KTP, KK, NPWP, SIM, Ijazah, Invoice, Quotation, COO) dan ekstraksi bebas via custom prompt.

**Tech Stack Utama**

| Lapis | Teknologi |
|---|---|
| Backend runtime | Python 3.x, FastAPI, Uvicorn |
| LLM pipeline | LangGraph (StateGraph), LangChain (langchain-openai), Qwen3-VL via vLLM |
| PDF parsing | Docling (primary, CUDA-accelerated) → pdfplumber + PyMuPDF/fitz (fallback) |
| Image processing | Pillow |
| Frontend | React 18 + Vite, Tailwind CSS |
| PDF rendering (FE) | pdfjs-dist |
| Excel export (FE) | SheetJS (xlsx) |
| Tour/Guide (FE) | driver.js |
| State persistence (FE) | IndexedDB (directory handle), React state |

**Pola Arsitektur**
- Backend: RESTful API monolitik dengan pipeline LangGraph per-request (tidak ada DB, semua stateless per-request)
- Frontend: SPA React single-page, berkomunikasi langsung ke backend via fetch
- LLM: OpenAI-compatible endpoint (vLLM lokal), diakses lewat LangChain `init_chat_model`
- Log: disimpan ke disk lokal (`call_logs/`) per request, tidak ada queue atau message broker

---

## Core Logic Flow (Function-Level)

### Flow 1 — Ekstraksi Dokumen Predefined (KTP, Invoice, dll.)

```
POST /ocr/process/document
  └─ main.py: process_ocr_document()
       ├─ main.py: _process_files(files, pages, document_type)
       │    ├─ [PDF]  pdf.py: extract_pages(pdf_bytes, pages_str)
       │    │         ├─ pdf.py: parse_page_filter(pages_str)
       │    │         ├─ pdf.py: _run_docling(pdf_bytes, max_pages, page_filter)
       │    │         │         → DocumentConverter (Docling) → page image + table crops + markdown + colored_texts
       │    │         └─ [fallback] pdf.py: _run_pdfplumber(pdf_bytes, max_pages, page_filter)
       │    │                       → pdfplumber + fitz → page image + markdown + colored_texts
       │    └─ [Image] image.py: bytes_to_content_item(raw_bytes, content_type)
       │                         → Pillow resize → base64 JPEG
       └─ pipeline.py: run_ocr(document_type, pages, fields, custom_prompt)
            └─ LangGraph StateGraph (_ocr_graph)
                 ├─ Node: process_page_node(state)
                 │        ├─ _build_user_message() — inject colored_texts + markdown
                 │        ├─ doc_prompt.py: get_prompt_for_document(doc_type)
                 │        └─ _invoke_model(messages)
                 │             └─ LangChain model.invoke() → vLLM (Qwen3-VL)
                 │                  └─ parsing.py: clean_json_response() → json.loads()
                 ├─ [jika field kurang] Node: reprocess_page_node(state)
                 │        └─ _invoke_model() dengan prompt missing fields
                 └─ Node: aggregate_node(state)  [jika > 1 halaman]
                          ├─ build_field_tallies(page_results) — majority vote + last-page rule
                          └─ _invoke_model() — LLM confirm/override tallies
                               → [fallback] aggregate_programmatic()
  └─ call_log.py: create_call_log() → disk: call_logs/{timestamp}/
  └─ return {success, data}
```

### Flow 2 — Ekstraksi COO (multi-dokumen khusus)

```
POST /ocr/process/document (document_type=COO)
  └─ main.py: process_ocr_coo_document(files, pages)
       ├─ Klasifikasi file by filename: BL / PEB / PL / INV_COO
       ├─ _process_files() + run_ocr("BL", ...)   → coo_prompt.py: BL_PROMPT
       ├─ _process_files() + run_ocr("PEB", ...)  → coo_prompt.py: PEB_PROMPT  [default: last 2 pages]
       ├─ _process_files() + run_ocr("PL", ...)   → coo_prompt.py: PL_PROMPT   [default: page 1]
       ├─ _process_files() + run_ocr("INV_COO", ...) → coo_prompt.py: INV_COO_PROMPT [default: page 1]
       ├─ Programmatic merge: bl_data + peb_data + pl_data + inv_data → COO schema
       └─ create_call_log() → return {success, data: merged_coo}
```

### Flow 3 — Batch Images (Frontend)

```
uploadedFiles (multiple) → App.jsx: handleRunOcr()
  └─ batchProcessor.js: processBatch({ files, endpoint, concurrencyLimit=3 })
       ├─ Per file: fetch POST /ocr/process/* (FormData)
       └─ mergeResults(results)
            → normalize keys, pad null, tambah _source filename
  └─ setOcrResult(result) → ResultViewer.jsx
```

### Flow 4 — Excel Export (COO Template)

```
ResultViewer.jsx: handleDownloadExcel()
  └─ [COO] excelExporter.js: getCooExcelBlob(ocrResult)
       ├─ fetch /coo_template.xlsx (public folder)
       ├─ XLSX.read() → fill "CREATE COO" sheet (scalar cells D25–D57)
       ├─ Fill "Sheet1" table rows (kolom A–I per item)
       └─ XLSX.write() → Blob
  └─ [lainnya] excelExporter.js: getExcelBlob(ocrResult)
       ├─ Flat fields → sheet "data"
       └─ Array fields → sheet terpisah per key
```

---

## Clean Tree

```
edge-ai-ocr/
├── main.py                        # FastAPI app + semua route handler
├── run.py                         # Server entrypoint (uvicorn)
├── requirements.txt
├── .env.example
│
├── app/
│   ├── core/
│   │   ├── config.py              # Env vars, LangChain model init
│   │   ├── doc_prompt.py          # Lookup DOCUMENT_PROMPTS dict + per-doc prompt strings
│   │   ├── sys_prompt.py          # Base directives, schemas, aggregate prompt builder
│   │   ├── coo_prompt.py          # BL / PEB / PL / INV_COO / COO prompts
│   │   ├── spbb_prompt.py         # Invoice_SPBB prompt
│   │   └── quatation_prompt.py    # Quotation prompt
│   ├── services/
│   │   ├── pdf.py                 # PDF extraction (Docling + pdfplumber fallback)
│   │   └── pipeline.py            # LangGraph OCR pipeline + aggregation logic
│   └── utils/
│       ├── call_log.py            # Disk logging per request
│       ├── errors.py              # vLLM error → HTTPException mapper
│       ├── image.py               # Pillow resize, base64, MIME validation
│       └── parsing.py             # clean_json_response, clean_markdown_response
│
└── frontend/
    ├── src/
    │   ├── main.jsx               # React root
    │   ├── App.jsx                # State orchestration + OCR trigger
    │   ├── App.css
    │   ├── index.css
    │   ├── components/
    │   │   ├── ConfigPanel.jsx    # Mode config UI (doc-type / fields / custom)
    │   │   ├── DocumentPreviewer.jsx  # PDF.js canvas + image strip
    │   │   ├── GuidedTour.jsx     # driver.js tour steps
    │   │   ├── HealthIndicator.jsx    # /health polling (30s interval)
    │   │   └── ResultViewer.jsx   # JSON syntax highlight + export buttons
    │   └── utils/
    │       ├── batchProcessor.js  # Concurrent fetch queue (limit=3) + merge
    │       ├── excelExporter.js   # SheetJS XLSX builder (generic + COO template)
    │       └── fileSystem.js      # IndexedDB directory handle + saveBlobToDirectory
    └── public/
        └── coo_template.xlsx      # Template Excel COO (wajib ada, di-fetch runtime)
```

---

## Module Map (The Chapters)

| Path | Fungsi/Class Publik Utama | Peran |
|---|---|---|
| `main.py` | `process_ocr_document`, `process_ocr_fields`, `process_ocr_prompt`, `process_ocr_coo_document`, `_process_files`, `health_check`, `root` | Semua route handler FastAPI + validasi file input |
| `run.py` | `__main__` block | Entrypoint uvicorn dengan env vars |
| `app/core/config.py` | `model`, `DocumentType`, konstanta `MAX_*` | Init LangChain model + semua env config |
| `app/core/doc_prompt.py` | `DOCUMENT_PROMPTS` dict, `get_prompt_for_document()` | Registry prompt per tipe dokumen |
| `app/core/sys_prompt.py` | `BASE_DIRECTIVES`, `BASE_DIRECTIVES_COO`, schema constants, `get_prompt_for_fields()`, `get_prompt_for_custom()`, `get_aggregate_prompt()` | Blok prompt reusable (extraction rules, schemas, aggregasi) |
| `app/core/coo_prompt.py` | `BL_PROMPT`, `PEB_PROMPT`, `PL_PROMPT`, `COO_PROMPT`, `INV_COO_PROMPT` | Prompt spesifik dokumen shipping/COO |
| `app/core/spbb_prompt.py` | `INVOICE_SPBB_PROMPT` | Prompt invoice internal (SPBB) |
| `app/core/quatation_prompt.py` | `QUOTATION_PROMPT` | Prompt quotation dengan color-based material code extraction |
| `app/services/pdf.py` | `extract_pages()`, `_run_docling()`, `_run_pdfplumber()`, `parse_page_filter()`, `extract_colored_text()` | Konversi PDF → list `PageData` (image + table crops + markdown + colored text) |
| `app/services/pipeline.py` | `run_ocr()`, `process_page_node()`, `reprocess_page_node()`, `aggregate_node()`, `build_field_tallies()`, `aggregate_programmatic()` | Orkestrasi LangGraph OCR per halaman + agregasi multi-halaman |
| `app/utils/call_log.py` | `create_call_log()`, `MessageSerializer` | Simpan request/response + image ke disk untuk debugging |
| `app/utils/errors.py` | `handle_llm_exception()` | Map exception vLLM ke HTTPException bermakna |
| `app/utils/image.py` | `pil_to_content_item()`, `bytes_to_content_item()`, `validate_content()` | Resize + base64 encode gambar, blokir external URL |
| `app/utils/parsing.py` | `clean_json_response()`, `clean_markdown_response()` | Strip thinking block / markdown fence, ekstrak JSON bersih |
| `frontend/src/App.jsx` | `App` (default export) | Root state, file upload, mode selector, OCR trigger, progress tracking |
| `frontend/src/components/ConfigPanel.jsx` | `ConfigPanel` | UI input konfigurasi mode (doc-type / fields / custom-prompt) + folder picker |
| `frontend/src/components/DocumentPreviewer.jsx` | `DocumentPreviewer` | Preview PDF via PDF.js canvas + image strip, zoom, page selector |
| `frontend/src/components/ResultViewer.jsx` | `ResultViewer` | Tampilkan JSON dengan syntax highlighting + download JSON/Excel |
| `frontend/src/components/HealthIndicator.jsx` | `HealthIndicator` | Poll `GET /health` setiap 30 detik, tampilkan status dot |
| `frontend/src/components/GuidedTour.jsx` | `startGuidedTour()` | Driver.js tour 6 langkah untuk onboarding pengguna |
| `frontend/src/utils/batchProcessor.js` | `processBatch()`, `mergeResults()` | Antrian upload konkuren (limit 3) + normalisasi hasil batch |
| `frontend/src/utils/excelExporter.js` | `getExcelBlob()`, `getCooExcelBlob()`, `exportToExcel()`, `exportCooToExcelTemplate()` | Buat file XLSX dari data OCR (generic + fill template COO) |
| `frontend/src/utils/fileSystem.js` | `saveDirectoryHandle()`, `loadDirectoryHandle()`, `saveBlobToDirectory()` | Simpan/load directory handle via IndexedDB, tulis file ke folder lokal |

---

## Data & Config

**Lokasi Config**
- `.env` (dari `.env.example`) — root project
- Dibaca oleh `app/core/config.py` via `python-dotenv`

**Variabel Environment Kunci**

| Var | Default | Keterangan |
|---|---|---|
| `BASE_URL_LLM` | `http://localhost:8000` | URL vLLM server |
| `MODEL_NAME` | `qwen3-vl` | Model identifier untuk vLLM |
| `PORT` | `5030` | Port FastAPI |
| `LOG_LEVEL` | `INFO` | Log level Uvicorn |
| `MAX_DOC_PAGES` | `20` | Batas halaman per request |
| `MAX_IMAGE_SIZE` | `1024` | Batas ukuran gambar (px, sisi terpanjang) |
| `CALL_LOG_DIR` | `call_logs` | Direktori log disk |
| `CALL_LOG_ENABLED` | `true` | Toggle logging ke disk |

**Skema Data Inti**

Tidak ada database. Data mengalir sepenuhnya in-memory per request.

Struktur internal utama:

```
PageData (TypedDict)
  ├── page_no: int
  ├── image: {type: "image_url", image_url: {url: "data:image/jpeg;base64,..."}}
  ├── table_images: List[image_url_dict]
  ├── figure_images: List[image_url_dict]
  ├── colored_texts: List[{text, color, rgb}]
  └── markdown: str

OCRState (TypedDict / LangGraph state)
  ├── document_type, fields, custom_prompt
  ├── pages: List[PageData]
  ├── current_idx: int
  ├── page_results: List[Dict]
  ├── final_result: Dict
  └── messages_log: List[Dict]
```

**Schema Output per Tipe Dokumen** — didefinisikan sebagai string konstanta di `app/core/sys_prompt.py`:
`KTP_SCHEMA`, `KK_SCHEMA`, `NPWP_SCHEMA`, `INVOICE_SCHEMA`, `QUOTATION_SCHEMA`, `SIM_SCHEMA`, `IJAZAH_SCHEMA`, `BL_SCHEMA`, `PEB_SCHEMA`, `PL_SCHEMA`, `COO_SCHEMA`, `INV_COO_SCHEMA`

**Folder Runtime Artifacts**

| Path | Isi |
|---|---|
| `call_logs/{timestamp}/` | `call.json` + halaman PNG + tabel PNG per request |
| `models/docling/` | Artifact model Docling (di-set via `artifacts_path`) |
| `frontend/public/coo_template.xlsx` | Template Excel COO (di-fetch runtime oleh frontend) |

**Migration / Seed**: Not found (tidak ada DB, tidak diperlukan)

---

## External Integrations

| Layanan / API | Modul Pemanggil | Keterangan |
|---|---|---|
| **vLLM server** (local, OpenAI-compatible) | `app/core/config.py` → `init_chat_model()`, `app/services/pipeline.py` → `model.invoke()` | Inferensi Qwen3-VL; dipanggil via LangChain tiap node LangGraph |
| **GET `{BASE_URL_LLM}/health`** | `main.py: health_check()` | Cek kesiapan vLLM saat `GET /health` |
| **Docling** (library lokal) | `app/services/pdf.py: _run_docling()` | Parse PDF → image + table crop + markdown; CUDA accelerated |
| **CDN jsDelivr** (`pdfjs-dist worker`) | `frontend/src/components/DocumentPreviewer.jsx` | Worker PDF.js diload dari CDN saat render PDF di browser |

---

## Risks / Blind Spots

1. **Inkonsistensi entrypoint**: `run.py` memanggil `uvicorn.run("app.main:app", ...)` tetapi FastAPI app (`app = FastAPI(...)`) berada di `main.py` (root), bukan `app/main.py`. Kemungkinan ada `app/main.py` yang meng-import dari `main.py` root — file tersebut **tidak ada dalam codebase yang tersedia** untuk dipetakan.

2. **`coo_template.xlsx` wajib ada**: Frontend melakukan `fetch("/coo_template.xlsx")` secara runtime. Jika file tidak ada di `frontend/public/`, ekspor COO gagal dengan error tidak informatif. Tidak ada fallback.

3. **COO file klasifikasi by filename**: `process_ocr_coo_document()` menentukan tipe sub-dokumen (BL/PEB/PL/INV) berdasarkan substring nama file (`"bl"`, `"peb"`, `"invoice"`). Nama file yang tidak sesuai konvensi akan menyebabkan error `file_pages_required`.

4. **LangGraph state tidak persisten**: Jika server restart di tengah request (mis. karena timeout panjang), state OCR hilang tanpa recovery mechanism.

5. **Docling model path hardcoded**: `artifacts_path='./models/docling'` di `_run_docling()` — relative path; jika app dijalankan dari direktori berbeda, Docling gagal dan fallback ke pdfplumber.

6. **CALL_LOG_DIR tumbuh tanpa batas**: Tidak ada mekanisme cleanup/rotation log disk di `call_logs/`. Disk bisa penuh pada penggunaan produksi intensif.

7. **`tailwind.config.js`** direferensikan di `index.css` (`@config "../tailwind.config.js"`) — file tidak ada dalam snapshot codebase, tidak bisa dipetakan konfigurasi token warnanya.

8. **`frontend/src/components/GuidedTour.jsx`** menggunakan selector DOM ID hardcoded (`#health-indicator-container`, dll.) — jika ID berubah di komponen lain, tour rusak tanpa error compile-time.
# SYSTEM_MAP — Edge AI OCR

---

## Project Summary

**Tujuan Aplikasi**
Sistem OCR dokumen berbasis AI multimodal/VLM lokal (edge deployment). Menerima berkas gambar atau PDF, melakukan rendering halaman dengan PyMuPDF, mengekstraksi fragmen teks berpresisi tinggi dengan PaddleOCR, lalu melakukan pemetaan semantik terstruktur ke format JSON menggunakan model VLM (Qwen3.0 - VL) via vLLM. Sistem ini juga menyertakan fitur pencocokan koordinat (bounding box) dan tingkat kepercayaan (confidence score) untuk setiap field, sistem autentikasi pengguna berbasis JWT, manajemen pengguna (CRUD), pemrosesan batch, serta ekspor data ke berkas Excel.

Aplikasi ini dirancang untuk mendukung dokumen terstandardisasi Indonesia (KTP, KK, NPWP, SIM, Ijazah, Invoice SPBB, Quotation, COO sub-documents BL, PEB, PL, INV_COO) serta ekstraksi dinamis via custom fields atau custom prompt.

**Tech Stack Utama**

| Lapis | Teknologi |
|---|---|
| Backend runtime | Python 3.x, FastAPI, Uvicorn |
| OCR Engine | PaddleOCR (Inference berjalan lokal di CPU/GPU, menggunakan fp16 static engine, dengan serialisasi concurrency menggunakan Threading Lock) |
| VLM Pipeline | LangChain (`init_chat_model` dengan OpenAI-compatible provider), mengakses model `Qwen/Qwen3.0 - VL-2B-Instruct` (atau sejenisnya) via vLLM lokal |
| PDF Rendering | PyMuPDF (`fitz`) — merender halaman PDF langsung ke PIL Images pada target DPI (`PYMUPDF_DPI`) |
| Keamanan & Rate Limit | SlowAPI (Limiter rate limit 20 request/menit untuk endpoint pemrosesan), PyJWT + bcrypt untuk autentikasi dan otorisasi |
| Penyimpanan Lokal | Berkas JSON (`users.json` untuk database pengguna), Direktori lokal (`call_logs/` untuk log request & response per aktivitas) |
| Frontend SPA | React 18 + Vite, Tailwind CSS, pdfjs-dist (viewer PDF), SheetJS / xlsx (export Excel), driver.js (guided tour) |
| State Persistence (FE) | IndexedDB (menyimpan folder handle untuk ekspor berkas otomatis), LocalStorage (token JWT, data user, tema) |

**Pola Arsitektur**
- **Backend (Stateless & Modular)**: FastAPI monolitik yang memisahkan logika ke dalam service modules (`pdf.py`, `ocr_engine.py`, `semantic.py`, `validator.py`, `auth.py`, `user_db.py`). Pipeline OCR & Semantic berjalan per-request tanpa database relasional eksternal.
- **Frontend (Component-Driven SPA)**: Aplikasi React single-page yang terbagi atas dashboard, halaman ekstraksi khusus, panel pengaturan admin, sidebar navigasi, dan helper utility.
- **Autentikasi**: Endpoint diamankan menggunakan skema Bearer Token JWT. Untuk admin, peran dicek melalui dekorator FastAPI Dependency (`get_current_admin`).

---

## Core Logic Flow (Function-Level)

### Flow 1 — Ekstraksi Dokumen Predefined, Custom Fields, & Custom Prompt

```
POST /ocr/process/document  (atau /ocr/process/fields, /ocr/process/prompt)
  └─ main.py: process_ocr_document() / process_ocr_fields() / process_ocr_prompt()
       ├─ Dependensi: get_current_user() — validasi token JWT
       ├─ Batasan Ukuran: safe_read() — memastikan berkas tidak melebihi MAX_UPLOAD_BYTES (default 50MB)
       ├─ main.py: _process_files(files, pages, document_type)
       │    ├─ Validasi format berkas & deteksi MIME type menggunakan signature magic bytes (utils/image.py)
       │    ├─ [PDF]  pdf.py: extract_pages(pdf_bytes, pages_str)
       │    │         ├─ pdf.py: parse_page_filter(pages_str) -> Mengurai seleksi halaman (all, ranges, negative index)
       │    │         └─ pdf.py: _render_pdf_pages() -> PyMuPDF (fitz) merender PDF ke list PageImage (PIL Image + dimensi)
       │    └─ [Gambar] Memuat gambar secara langsung via Pillow dan memasukkannya ke struktur PageImage
       └─ semantic.py: run_semantic(document_type, page_images, fields, custom_prompt)
            ├─ Iterasi per halaman (PageImage):
            │    ├─ ocr_engine.py: run_ocr_on_image()
            │    │         └─ Mengambil engine PaddleOCR -> predict() -> Menghasilkan list OCRFragment (text, bbox, confidence)
            │    ├─ semantic.py: merge_ocr_fragments()
            │    │         └─ Mengelompokkan fragmen OCR yang sejajar secara horizontal & mengurutkannya dari kiri ke kanan
            │    ├─ Memformat layout teks halaman mentah (OCR Context)
            │    ├─ semantic_prompt.py: get_doctype_semantic_prompt() / get_fields_semantic_prompt() / get_custom_semantic_prompt()
            │    │         └─ Membuat prompt semantik yang disesuaikan dengan skema output JSON target
            │    └─ VLM Inference: model.ainvoke(messages)
            │              └─ Mengirimkan PIL Image halaman bersama teks OCR Context ke model VLM via vLLM
            │              └─ parsing.py: clean_json_response() -> json.loads() untuk validasi JSON bersih
            ├─ Konsolidasi Multi-halaman (Jika halaman > 1):
            │    ├─ semantic.py: build_field_tallies()
            │    │         └─ Melakukan kalkulasi voting mayoritas, penentuan nilai halaman terakhir (last-page rule untuk totals),
            │    │            atau pemenang tie-break halaman pertama (earliest page)
            │    ├─ VLM Aggregation: model.ainvoke(agg_messages) menggunakan prompt agregasi semantik
            │    └─ [Fallback] semantic.py: aggregate_programmatic() jika panggilan LLM Agregasi gagal
            ├─ Koordinat & Tingkat Kepercayaan:
            │    └─ semantic.py: resolve_bboxes_for_flat_json()
            │              └─ Menyelusuri JSON hasil ekstraksi secara rekursif, mencocokkan nilainya ke OCRFragment asli
            │                 menggunakan fuzzy matching (find_fuzzy_substring) untuk menyematkan koordinat bbox asli
            │                 dan confidence score PaddleOCR ke JSON output.
            ├─ call_log.py: create_call_log() -> Menyimpan detail pemrosesan (metadata request, images, messages log, output JSON) ke disk
            └─ Mengembalikan output JSON terstruktur yang berisi data ter-resolusi & koordinat bboxes.
```

### Flow 2 — Ekstraksi COO (Consolidated Certificate of Origin)

```
POST /ocr/process/document (document_type=COO)
  └─ main.py: process_ocr_coo_document(files, pages)
       ├─ Memvalidasi jumlah berkas (maksimal 4)
       ├─ Mengklasifikasikan berkas secara otomatis berdasarkan kecocokan nama berkas:
       │    ├─ "bl", "lading", "bill" -> Bill of Lading (BL)
       │    ├─ "peb", "ekspor" -> Pemberitahuan Ekspor Barang (PEB)
       │    ├─ "packing", "pl" -> Packing List (PL)
       │    └─ "invoice", "inv" -> Invoice COO (INV_COO)
       ├─ Memastikan semua 4 komponen dokumen lengkap (BL, PEB, PL, INV_COO)
       ├─ Menjalankan pemrosesan paralel via asyncio.gather() dengan aturan halaman khusus:
       │    ├─ BL: diproses pada halaman 1 (pages_rule="1") -> run_semantic()
       │    ├─ PEB: diproses pada halaman terakhir (pages_rule="-2" / default last 2 pages) -> run_semantic()
       │    ├─ PL: diproses pada halaman 1 (pages_rule="1") -> run_semantic()
       │    └─ INV_COO: diproses pada halaman 1 (pages_rule="1") -> run_semantic()
       ├─ Penggabungan Programatis (Programmatic Merge):
       │    └─ Menyalin field spesifik dari bl_data, peb_data, pl_data, dan inv_data ke dalam skema gabungan COO
       ├─ Menggabungkan berkas gambar halaman, dimensi halaman, serta log pesan dari ke-4 dokumen tersebut
       ├─ call_log.py: create_call_log() -> Menyimpan log komprehensif COO ke disk
       └─ Mengembalikan data COO ter-merge bersama koordinat dan dimensi halaman gabungan
```

### Flow 3 — Autentikasi Pengguna & Sesi CRUD Admin

- **Startup**: Saat server FastAPI dinyalakan, `@app.on_event("startup")` memanggil `init_default_admin()` untuk mengecek apakah ada user di `users.json`. Jika kosong, dibuat user default admin: username `SYSTEM_ADMIN`, password `admin123`, nomor badge `000000`.
- **Autentikasi**: Pengguna mengirimkan kredensial badge number dan password ke `/api/auth/login`. Jika sukses, token JWT Bearer dikembalikan (menyimpan payload username, role, employee/badge).
- **Verifikasi Token**: Dependensi `get_current_user()` mengekstrak dan mendekode token JWT. Mendukung bypass API key statis via `STATIC_API_KEY` (dibaca dari environment variable).
- **Pengaturan CRUD**: Panel CRUD pengguna di `/api/users` dibatasi khusus untuk admin melalui `get_current_admin()`. Admin dapat melihat, menambah, mengubah (termasuk mengganti badge number/role), serta menghapus user lain. Pencegahan demosi admin terakhir diterapkan secara programatis di `update_user()`.

### Flow 4 — Pemrosesan Batch (Frontend)

```
uploadedFiles (multiple) -> BatchExtractor.jsx: handleStartExtraction()
  └─ batchProcessor.js: processBatch({ files, endpoint, concurrencyLimit, token })
       ├─ Inisialisasi antrian pemrosesan dengan batasan concurrencyLimit (default 3)
       ├─ Melakukan panggilan fetch POST paralel ke endpoint backend terpilih dengan Header Authorization Token JWT
       └─ mergeResults(results)
            ├─ Menormalisasi struktur kunci JSON hasil batch agar konsisten
            ├─ Melakukan padding nilai null untuk kolom yang tidak terisi di berkas tertentu
            └─ Menambahkan metadata `_source` berupa nama file asal ke setiap baris data
  └─ setOcrResult(result) -> ResultViewer.jsx
```

### Flow 5 — Ekspor Excel dengan Dukungan Template

```
ResultViewer.jsx: handleDownloadExcel()
  ├─ [Mode COO] excelExporter.js: exportCooToExcelTemplate(ocrResult)
  │    ├─ fetch "/coo_template.xlsx" secara runtime dari public folder frontend
  │    ├─ Membaca berkas template dengan SheetJS (xlsx)
  │    ├─ Mengisi sheet "CREATE COO": memetakan nilai skalar ke sel statis (kolom D25–D57)
  │    ├─ Mengisi sheet "Sheet1": menulis baris tabel item barang secara dinamis (kolom A–I)
  │    └─ Menghasilkan Excel Blob -> Trigger download lokal
  └─ [Mode Predefined/Lainnya] excelExporter.js: exportToExcel(ocrResult, title)
       ├─ Memisahkan field skalar flat ke sheet utama ("Data Ekstraksi")
       ├─ Memisahkan field bertipe array/tabel ke sheet tersendiri per key array
       └─ Menghasilkan Excel Blob -> Trigger download lokal
```

---

## Clean Tree

```
edge-ai-ocr/
├── backend/
│   ├── main.py                        # FastAPI application, route handlers, limiter, and startup configurations
│   ├── requirements.txt               # Backend dependencies (FastAPI, PaddleOCR, PyMuPDF, PyJWT, SlowAPI, etc.)
│   ├── .env.example                   # Example environment configurations
│   ├── users.json                     # Local JSON database storing user roles & hashed passwords
│   │
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py              # Environment variable parser, system logger, and LangChain model initializer
│   │   │   ├── sys_prompt.py          # Base extraction rules, output schemas (KTP, KK, NPWP, etc.), and aggregate prompt
│   │   │   ├── doc_prompt.py          # Predefined document prompts mapping dictionary
│   │   │   ├── coo_prompt.py          # Prompts for COO sub-documents (BL, PEB, PL, INV_COO)
│   │   │   ├── spbb_prompt.py         # Prompt for Invoice SPBB documents
│   │   │   ├── quatation_prompt.py    # Prompt for Quotation documents (with color-based material code extraction)
│   │   │   └── semantic_prompt.py     # Prompt builder helpers per extraction type & prompt injection sanitization
│   │   │
│   │   ├── services/
│   │   │   ├── pdf.py                 # PDF rendering helper using PyMuPDF (fitz) with page range filtering
│   │   │   ├── ocr_engine.py          # PaddleOCR manager (GPU/CPU support, thread locking, fp16 static engine)
│   │   │   ├── semantic.py            # Decoupled VLM + OCR pipeline, coordinate resolution, line merger, and aggregation
│   │   │   ├── validator.py           # Regex format rules and document key overrides for high-precision labeling
│   │   │   └── ocr_grouping.py        # Legacy OCR line grouping helper
│   │   │
│   │   └── utils/
│   │       ├── auth.py                # JWT creation, token decode, and role validation dependencies
│   │       ├── user_db.py             # CRUD utilities managing the local users.json database
│   │       ├── call_log.py            # Disk call logger writing requests/responses & base64 images per request
│   │       ├── errors.py              # Exception mapper converting internal/vLLM errors to HTTPExceptions
│   │       ├── image.py               # Pillow helpers for image resizing, validation, and base64 parsing
│   │       └── parsing.py             # Helpers to clean JSON and markdown code fences from LLM outputs
│   │
│   └── tests/
│       ├── test_main.py               # Authentication, user management, and API endpoints tests
│       ├── test_ocr_engine.py         # PaddleOCR basic validation tests
│       ├── test_ocr_grouping.py       # OCR line grouping utility tests
│       ├── test_semantic.py           # Decoupled pipeline, coordinate resolution, and multi-page aggregation tests
│       └── test_validator.py          # Validation rules and field formatting regex tests
│
└── frontend-edge-ai-ocr/
    ├── index.html                     # Entry HTML template
    ├── package.json                   # Node.js dependencies and run scripts
    ├── tailwind.config.js             # Tailwind CSS custom configurations
    ├── vite.config.js                 # Vite server configurations
    │
    ├── src/
    │   ├── main.jsx                   # React application entrypoint
    │   ├── App.jsx                    # Routing, global states, session handlers, and theme management
    │   ├── index.css                  # CSS file containing Tailwind directives and custom styles
    │   │
    │   ├── components/
    │   │   ├── Login.jsx              # User login card interface with badge & password fields
    │   │   ├── Dashboard.jsx          # Welcome portal with statistics and quick access links
    │   │   ├── Sidebar.jsx            # Left collapsible navigation panel
    │   │   ├── TopBar.jsx             # Upper header showing logged user, badge, role, and theme switcher
    │   │   ├── DokumenExtractor.jsx   # Extractor workspace for KTP, KK, NPWP, SIM, Ijazah, and Invoice SPBB
    │   │   ├── CooExtractor.jsx       # Consolidated workspace to process, merge, and export COO documents
    │   │   ├── BatchExtractor.jsx     # Concurrent multi-file batch workspace
    │   │   ├── CustomPromptExtractor.jsx # Dynamic extractor workspace driven by user-written instructions
    │   │   ├── ConfigPanel.jsx        # Sidebar configuration controls for files selection and OCR parameters
    │   │   ├── DocumentPreviewer.jsx  # Interactive canvas rendering PDF pages via PDF.js with zooming
    │   │   ├── ResultViewer.jsx       # JSON syntax highlighter panel with Excel export actions
    │   │   ├── Settings.jsx           # User management portal for admins (CRUD interface)
    │   │   ├── HealthIndicator.jsx    # Status polling indicator checking `/health` every 30 seconds
    │   │   ├── GuidedTour.jsx         # Interactive onboarding guided tour using driver.js
    │   │   └── Stepper.jsx            # Extraction progress indicator (Upload -> Process -> Result)
    │   │
    │   └── utils/
    │       ├── batchProcessor.js      # Concurrency queue manager (max concurrency 3) and batch consolidator
    │       ├── excelExporter.js       # SheetJS helper mapping extracted JSON payloads to structured sheets (normal/COO)
    │       └── fileSystem.js          # IndexedDB wrapper saving and reading selected folder directory handles
    │
    └── public/
        └── coo_template.xlsx          # Required template Excel sheet utilized runtime for COO sheet filling
```

---

## Module Map (The Chapters)

| Path | Fungsi/Class Publik Utama | Peran |
|---|---|---|
| `backend/main.py` | `process_ocr_document`, `process_ocr_fields`, `process_ocr_prompt`, `process_ocr_coo_document`, `_process_files`, `login`, `get_all_users`, `create_user`, `delete_user_endpoint`, `update_user_endpoint`, `health_check`, `root` | Semua route handler FastAPI, rate limiter, validasi upload file, dan startup user DB check |
| `backend/app/core/config.py` | `model`, `DocumentType`, konstanta `MAX_*`, `PYMUPDF_DPI`, `PADDLE_*` | Inisialisasi model LangChain (`init_chat_model`) dan pembacaan seluruh environment variables |
| `backend/app/core/sys_prompt.py` | `BASE_DIRECTIVES`, `BASE_DIRECTIVES_COO`, skema skalar dokumen, `get_aggregate_prompt()` | Kumpulan direktori sistem dasar, skema keluaran dokumen, dan pembentuk prompt konsolidasi multi-halaman |
| `backend/app/core/doc_prompt.py` | `DOCUMENT_PROMPTS` | Kamus registry prompt sistem per jenis dokumen terstandardisasi |
| `backend/app/core/coo_prompt.py` | `PEB_PROMPT`, `PL_PROMPT`, `BL_PROMPT`, `INV_COO_PROMPT`, `COO_PROMPT` | Prompt ekstraksi khusus berkas shipping pendukung COO |
| `backend/app/core/spbb_prompt.py` | `INVOICE_SPBB_PROMPT` | Prompt ekstraksi dokumen Invoice SPBB internal |
| `backend/app/core/quatation_prompt.py` | `QUOTATION_PROMPT` | Prompt ekstraksi Quotation dengan instruksi material code |
| `backend/app/core/semantic_prompt.py` | `get_doctype_semantic_prompt`, `get_fields_semantic_prompt`, `get_custom_semantic_prompt`, `sanitize_custom_prompt` | Helper pembangunan prompt dinamis per mode ekstraksi serta modul sanitasi penangkal serangan prompt injection |
| `backend/app/services/pdf.py` | `extract_pages()`, `parse_page_filter()`, `_render_pdf_pages()` | Konverter PDF ke list `PageImage` via rendering PyMuPDF (`fitz`) dengan filter rentang halaman |
| `backend/app/services/ocr_engine.py` | `run_ocr_on_image()`, `get_ocr_engine()`, `OCRFragment` | Wrapper inisialisasi thread-safe PaddleOCR dan eksekusi OCR gambar untuk menghasilkan fragmen koordinat |
| `backend/app/services/semantic.py` | `run_semantic()`, `merge_ocr_fragments()`, `build_field_tallies()`, `aggregate_programmatic()`, `resolve_bboxes_for_flat_json()` | Inti pipeline OCR + Semantic: menggabungkan baris fragmen, interaksi model VLM, agregasi halaman, dan pemetaan koordinat (bbox) |
| `backend/app/services/validator.py` | `get_label_candidates()`, `validate_field()`, `FIELD_FORMAT_RULES` | Validasi tipe format data (regex) dan penghasil label display untuk mempermudah pemetaan koordinat |
| `backend/app/utils/auth.py` | `verify_password`, `create_access_token`, `get_current_user`, `get_current_admin` | Skema autentikasi token JWT Bearer, enkripsi password, dan dependensi pembatasan hak akses Admin |
| `backend/app/utils/user_db.py` | `load_users`, `save_users`, `get_user`, `add_user`, `delete_user`, `update_user`, `init_default_admin` | Manajemen CRUD berkas `users.json` penyimpan data pengguna lokal |
| `backend/app/utils/call_log.py` | `create_call_log()` | Pencatat aktivitas request-response (termasuk penyimpanan gambar halaman) ke disk |
| `backend/app/utils/errors.py` | `handle_llm_exception()` | Pemeta error vLLM/OpenAI ke dalam HTTPExceptions yang informatif |
| `backend/app/utils/image.py` | `pil_to_content_item()`, `validate_file_content()`, `bytes_to_content_item()`, `validate_content()` | Utilitas gambar Pillow (base64 parsing, deteksi MIME type signature, proteksi external URL) |
| `backend/app/utils/parsing.py` | `clean_json_response()`, `clean_markdown_response()` | Helper pembersih output model dari syntax markdown block ```json atau tag penutup |
| `frontend-edge-ai-ocr/src/App.jsx` | `App` | Komponen utama pengatur tema, autentikasi, navigasi halaman, dan sinkronisasi state antar-tab |
| `frontend-edge-ai-ocr/src/components/Login.jsx` | `Login` | Halaman form masuk dengan validasi kredensial pengguna |
| `frontend-edge-ai-ocr/src/components/Dashboard.jsx` | `Dashboard` | Portal selamat datang yang menampilkan petunjuk ringkas & tombol cepat |
| `frontend-edge-ai-ocr/src/components/Sidebar.jsx` | `Sidebar` | Navigasi vertikal collapsible untuk berpindah fitur |
| `frontend-edge-ai-ocr/src/components/TopBar.jsx` | `TopBar` | Header horizontal penampil identitas login, peran user, dan toggle tema |
| `frontend-edge-ai-ocr/src/components/DokumenExtractor.jsx` | `DokumenExtractor` | Antarmuka ekstraksi jenis dokumen tunggal predefined |
| `frontend-edge-ai-ocr/src/components/CooExtractor.jsx` | `CooExtractor` | Antarmuka pengunggahan berkas COO (PEB, BL, PL, INV), visualisasi progress, dan ekspor |
| `frontend-edge-ai-ocr/src/components/BatchExtractor.jsx` | `BatchExtractor` | Antarmuka pemrosesan batch banyak berkas sekaligus dengan limit concurrency |
| `frontend-edge-ai-ocr/src/components/CustomPromptExtractor.jsx` | `CustomPromptExtractor` | Antarmuka ekstraksi bebas berorientasi pada input custom prompt pengguna |
| `frontend-edge-ai-ocr/src/components/ConfigPanel.jsx` | `ConfigPanel` | Panel konfigurasi pengunggah berkas, parameter halaman, dan folder ekspor |
| `frontend-edge-ai-ocr/src/components/DocumentPreviewer.jsx` | `DocumentPreviewer` | Viewer PDF interaktif menggunakan canvas pdf.js dengan panel thumbnail |
| `frontend-edge-ai-ocr/src/components/ResultViewer.jsx` | `ResultViewer` | Visualizer JSON hasil OCR dengan tombol download JSON / Excel |
| `frontend-edge-ai-ocr/src/components/Settings.jsx` | `Settings` | Panel administrasi admin untuk mengelola user (buat baru, perbarui password/peran, hapus user) |
| `frontend-edge-ai-ocr/src/components/HealthIndicator.jsx` | `HealthIndicator` | Poller status koneksi backend dan kesiapan vLLM |
| `frontend-edge-ai-ocr/src/components/GuidedTour.jsx` | `startGuidedTour` | Tour panduan interaktif onboarding pengguna (menggunakan driver.js) |
| `frontend-edge-ai-ocr/src/components/Stepper.jsx` | `Stepper` | Visualisasi penanda langkah-langkah alur kerja OCR |
| `frontend-edge-ai-ocr/src/utils/batchProcessor.js` | `processBatch()`, `mergeResults()` | Pelaksana pemrosesan batch paralel dengan pembatas antrian concurrent dan perata data |
| `frontend-edge-ai-ocr/src/utils/excelExporter.js` | `exportToExcel()`, `exportCooToExcelTemplate()` | Generator berkas Excel menggunakan SheetJS (normal & COO template mapping) |
| `frontend-edge-ai-ocr/src/utils/fileSystem.js` | `saveDirectoryHandle()`, `loadDirectoryHandle()`, `saveBlobToDirectory()` | API File System Access untuk menulis berkas hasil langsung ke direktori komputer pengguna |

---

## Data & Config

**Lokasi Konfigurasi & Kredensial**
- `.env` (disalin dari `.env.example`) berada di direktori `backend/` untuk konfigurasi runtime server.
- `.env` berada di `frontend-edge-ai-ocr/` untuk konfigurasi URL endpoint API frontend (`VITE_API_URL`).
- `backend/users.json` bertindak sebagai database lokal penyimpan user credentials.

**Variabel Environment Utama (Backend)**

| Variabel | Default | Keterangan |
|---|---|---|
| `PORT` | `5030` | Port server backend FastAPI |
| `LOG_LEVEL` | `INFO` | Level logger sistem backend |
| `BASE_URL_LLM` | `http://localhost:1234` | URL vLLM server endpoint (OpenAI-compatible) |
| `MODEL_NAME` | `Qwen/Qwen3.0 - VL-2B-Instruct` | Nama model yang digunakan pada vLLM server |
| `PYMUPDF_DPI` | `200` | Target DPI rendering halaman PDF ke gambar |
| `MAX_DOC_PAGES` | `20` | Batas maksimum jumlah halaman per request |
| `MAX_IMAGE_SIZE` | `1024` | Batas dimensi gambar terpanjang (jika di-resize) |
| `PADDLE_USE_GPU` | `true` | Toggle pemanfaatan akselerasi GPU CUDA untuk PaddleOCR |
| `PADDLE_OCR_LANG` | `en` | Bahasa deteksi PaddleOCR |
| `JWT_SECRET` | `supersecretkey123_change_me_in_production` | Kunci tanda tangan algoritma JWT token |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Masa berlaku token akses JWT (default 24 jam) |
| `STATIC_API_KEY` | None | Kunci API statis untuk bypass token user (untuk skrip otomatisasi) |
| `MAX_UPLOAD_BYTES` | `52428800` | Batas maksimum ukuran unggahan berkas (default 50MB) |

**Skema Data Inti**

1. **PageImage** (TypedDict)
   - `page_no` (int)
   - `image` (PIL Image)
   - `width` (int)
   - `height` (int)

2. **OCRFragment** (TypedDict)
   - `text` (str)
   - `bbox` (List[int]) -> `[xmin, ymin, xmax, ymax]` absolute pixels
   - `confidence` (float) -> 0.0 - 1.0 (dari PaddleOCR)
   - `page_no` (int)

3. **Resolved JSON Value** (Struktur koordinat yang ditambahkan ke field JSON)
   - Jika field berhasil dicocokkan dengan OCR fragments, nilainya diubah menjadi format objek:
     - `value` (Any): Nilai teks asli hasil ekstraksi semantik
     - `bbox_2d` (List[int]): Koordinat gabungan `[xmin, ymin, xmax, ymax]` halaman target
     - `confidence` (float): Rata-rata tingkat kepercayaan PaddleOCR untuk teks tercocok
     - `page_no` (int): Halaman tempat teks tersebut ditemukan

4. **User Schema** (dalam `users.json`)
   - `username` (str): Nama unik pengguna
   - `hashed_password` (str): Password yang di-hash dengan bcrypt
   - `employee` (str): Nomor badge pegawai (unik, bertindak sebagai ID)
   - `role` (str): `"admin"` atau `"user"`

---

## Integrasi Eksternal

| Layanan / Modul | Komponen Pemanggil | Keterangan |
|---|---|---|
| **vLLM Server** | `backend/app/core/config.py` (LangChain model) | Inferensi model VLM `Qwen3.0 - VL` lokal via REST endpoint |
| **PaddleOCR Engine** | `backend/app/services/ocr_engine.py` | Modul OCR lokal pemecah gambar menjadi fragmen teks |
| **PDF.js CDN** | `frontend-edge-ai-ocr/src/components/DocumentPreviewer.jsx` | Worker PDF rendering pada canvas browser di-load dari CDN jsDelivr |

---

## Risks / Blind Spots

1. **Akumulasi Disk call_logs**: Aktivitas pemrosesan dokumen menyimpan salinan gambar halaman dan data mentah request-response ke folder `backend/call_logs/` tanpa rotasi otomatis. Pada beban produksi tinggi, ini berisiko menghabiskan kapasitas disk.
2. **Ketergantungan Klasifikasi Berkas COO**: Klasifikasi dokumen BL, PEB, PL, INV_COO pada alur COO bergantung sepenuhnya pada pola string nama berkas. Jika nama berkas tidak menyertakan kata kunci tersebut, sistem akan menolak dokumen dengan error `file_pages_required`.
3. **Penyimpanan Lokal users.json**: Pengelolaan akun user disimpan dalam berkas flat JSON lokal. Tidak ada mekanisme locking berkas (file lock) saat penulisan konkuren, berisiko terjadi inkonsistensi jika beberapa admin melakukan update user secara bersamaan (race condition).
4. **Pembatasan Rate Limit Berbagi IP**: Skema rate limit SlowAPI dikonfigurasi berdasarkan remote IP address. Di lingkungan jaringan lokal perusahaan (LAN) di mana banyak klien keluar melalui satu gateway IP yang sama, rate limit 20 request/menit dapat dengan mudah terlampaui.
5. **Kesesuaian Validasi Prompt Injection**: Pembersih custom prompt pada `sanitize_custom_prompt` menggunakan deteksi regex kata kunci yang cukup ketat (seperti "ignore", "override", "system"). Hal ini berpotensi memblokir instruksi custom yang sah jika kalimatnya mirip dengan pola bypass.
6. **Ketiadaan Fallback untuk coo_template.xlsx**: Jika template `coo_template.xlsx` terhapus dari folder public frontend, fitur ekspor COO Excel akan gagal tanpa pesan error yang informatif bagi pengguna.
7. **Single-Threaded initialization lock**: Inisialisasi instance PaddleOCR dan eksekusi inference dilindungi dengan `threading.Lock` di `ocr_engine.py`. Hal ini membatasi pemrosesan OCR menjadi berurutan (sequential) antar request klien, menurunkan throughput jika ada beban request konkuren yang besar.
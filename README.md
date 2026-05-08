# Edge AI OCR API

High-precision document OCR powered by **Qwen3-VL** via vLLM. This API supports multimodal processing, allowing it to "see" page images, table crops, and extract structured data into JSON format.

## Features
- **Multimodal Pipeline**: Processes full images and table-specific crops for maximum accuracy.
- **LangGraph Integration**: Page-by-page processing with intelligent aggregation for multi-page documents.
- **Docling Support**: Advanced PDF parsing with native table extraction.
- **Dynamic Schemas**: Specify exactly which fields you want to extract.

---

## 🛠 Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd edge-ai-ocr
   ```

2. **Set up a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment**:
   Copy `.env.example` to `.env` and adjust the `BASE_URL_LLM` to point to your vLLM server.
   ```bash
   cp .env.example .env
   ```

---

## 🚀 Usage

### Starting the API
Run the server using the entry point:
```bash
python run.py
```
The API will be available at `http://localhost:5030`.

### Interactive Documentation (Swagger)
Visit `http://localhost:5030/docs` to view the interactive API documentation and test endpoints directly from your browser.

---

## 📡 API Endpoints

### 1. Process Document (Multipart Upload)
**Endpoint:** `POST /ocr/process/upload`

Extract fields from one or more images or a PDF.

**Parameters:**
- `files`: One or more image/PDF files.
- `document_type`: Type of document (e.g., `Invoice`, `KTP`, `Passport`). Default: `General`.
- `fields`: (Optional) List of specific field names to extract.
- `use_docling`: (Optional) Set to `false` to disable Docling PDF parsing.

#### Example using `curl`:
```bash
curl -X 'POST' \
  'http://localhost:5030/ocr/process/upload' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'files=@invoice.pdf;type=application/pdf' \
  -F 'document_type=Invoice' \
  -F 'fields=invoice_number' \
  -F 'fields=total_amount'
```

### 2. Health Check
**Endpoint:** `GET /health`

Checks the status of the API and connectivity to the LLM backend.

---

## 📂 Project Structure
```text
edge-ai-ocr/
├── app/
│   ├── core/           # Configuration and prompts
│   ├── services/       # OCR and Document processing logic
│   ├── utils/          # Helper functions
│   └── main.py         # FastAPI application entry
├── run.py              # Server runner
├── requirements.txt    # Python dependencies
└── README.md           # Project documentation
```

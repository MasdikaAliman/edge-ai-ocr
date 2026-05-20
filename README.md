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

### 1. Predefined Document Extraction
**Endpoint:** `POST /ocr/process/document`

Extract structured fields from one or more images or a single PDF according to a predefined document schema.

**Supported Document Types:**
- `KTP` (Indonesian National ID Card)
- `KK` (Indonesian Family Card)
- `NPWP` (Indonesian Tax ID)
- `Invoice` (Invoices/Receipts with items table)
- `Quotation` (Price quotes, item tables with custom material codes)
- `SIM` (Indonesian Driving License)
- `IJAZAH` (Indonesian Academic Certificates)

**Request Parameters (Multipart Form-Data):**
- `files`: One or more image files (JPEG, PNG, WebP, GIF, TIFF) or a single PDF file.
- `document_type`: Must be one of the supported document types (e.g., `Invoice`).

#### Example using `curl`:
```bash
curl -X 'POST' \
  'http://localhost:5030/ocr/process/document' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'files=@invoice.pdf;type=application/pdf' \
  -F 'document_type=Invoice'
```

#### Example using Python `requests`:
```python
import requests

url = "http://localhost:5030/ocr/process/document"
file_path = "invoice.pdf"

with open(file_path, "rb") as f:
    files = {"files": (file_path, f, "application/pdf")}
    data = {"document_type": "Invoice"}
    response = requests.post(url, files=files, data=data)

print(response.json())
```

---

### 2. Custom Fields Extraction
**Endpoint:** `POST /ocr/process/fields`

Extract only a specific list of user-defined fields from images or a PDF.

**Request Parameters (Multipart Form-Data):**
- `files`: One or more image files or a single PDF file.
- `fields`: Specific snake_case field names to extract. Specify this parameter multiple times to extract multiple fields.

#### Example using `curl`:
```bash
curl -X 'POST' \
  'http://localhost:5030/ocr/process/fields' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'files=@ktp.png;type=image/png' \
  -F 'fields=full_name' \
  -F 'fields=nik' \
  -F 'fields=address'
```

#### Example using Python `requests`:
```python
import requests

url = "http://localhost:5030/ocr/process/fields"
file_path = "ktp.png"

with open(file_path, "rb") as f:
    files = {"files": (file_path, f, "image/png")}
    # Multiple fields are passed as a list of tuples
    data = [
        ("fields", "full_name"),
        ("fields", "nik"),
        ("fields", "address"),
    ]
    response = requests.post(url, files=files, data=data)

print(response.json())
```

---

### 3. Custom Prompt Extraction
**Endpoint:** `POST /ocr/process/prompt`

Extract structured content using a completely custom user instruction/prompt.

**Request Parameters (Multipart Form-Data):**
- `files`: One or more image files or a single PDF file.
- `custom_prompt`: A detailed string describing the extraction rules, logic, and desired JSON structure.

#### Example using `curl`:
```bash
curl -X 'POST' \
  'http://localhost:5030/ocr/process/prompt' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'files=@receipt.jpg;type=image/jpeg' \
  -F 'custom_prompt=Extract the total amount and list all food items purchased.'
```

#### Example using Python `requests`:
```python
import requests

url = "http://localhost:5030/ocr/process/prompt"
file_path = "receipt.jpg"
prompt = "Extract the total amount and list all food items purchased."

with open(file_path, "rb") as f:
    files = {"files": (file_path, f, "image/jpeg")}
    data = {"custom_prompt": prompt}
    response = requests.post(url, files=files, data=data)

print(response.json())
```

---

### 4. Health Check
**Endpoint:** `GET /health`

Check the service health status and check if the backend vLLM server is reachable and ready.

#### Example using `curl`:
```bash
curl -X 'GET' 'http://localhost:5030/health'
```

---

### 5. Root Info
**Endpoint:** `GET /`

Returns API meta details including version info and the supported document types dynamically.

#### Example using `curl`:
```bash
curl -X 'GET' 'http://localhost:5030/'
```
---

## 📂 Project Structure
```text
edge-ai-ocr/
├── app/
│   ├── core/           # Configuration and prompts
│   ├── services/       # OCR and Document processing logic
│   └── utils/          # Helper functions (call logging, etc.)
├── main.py             # FastAPI application entry
├── run.py              # Server runner
├── requirements.txt    # Python dependencies
└── README.md           # Project documentation
```

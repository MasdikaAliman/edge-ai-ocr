# ─────────────────────────────────────────────
#  OCR System Prompt Definitions
# ─────────────────────────────────────────────

_LAST_VALUE_FIELDS = {
    "total_amount", "grand_total", "amount_due", 
    "total_due", "total_payable", "subtotal", "sub_total",
    "tax", "vat", "discount", "shipping",
}


# ---------- Shared Rule Blocks ----------

GROUNDING_RULE = """
GROUNDING & COORDINATE EXTRACTION (Qwen3-VL):
- Every field/key in the JSON schema (including nested columns inside table or list arrays) must be transformed from a simple placeholder/scalar value into a grounding object.
- The grounding object MUST contain exactly these two keys:
  1. "value": The extracted text verbatim or normalized value (or null if the field is not present or blank).
  2. "bbox_2d": The 2D bounding box of the extracted value, normalized to the range [0, 999] as an array of four integer: [x_min, y_min, x_max, y_max] where x_min, y_min are top-left, and x_max, y_max are bottom-right. If the field value is null or empty, set "bbox_2d" to null.
- This wrapping rule applies to ALL keys, including top-level properties and nested properties inside array items.
- Example structure transformation for a simple field:
  "nik": "string" -> "nik": {"value": "2171012345678901", "bbox_2d": [150, 220, 480, 255]}
- Never output a raw string or number directly; always wrap in this object structure.
"""

_OUTPUT_VALIDATION = """
OUTPUT VALIDATION:
- Avoid wrapping the output in markdown code fences (``` or ```json) — output pure JSON directly.
- The response must start with { or [ and end with } or ] without extra markers.
- Do NOT add any text, label, or explanation before or after the JSON.
- Do NOT use trailing commas anywhere in the JSON.
- If no fields can be extracted or consolidated, return an empty object {}.
- Every key must be a string. Every value must be a string, number, array, or null — never undefined.
"""

_CURRENCY_RULE = """
CURRENCY EXTRACTION:
- Extract the currency symbol only (e.g. "$", "Rp", "€", "£", "¥") into the `currency` field.
- If written as a code (USD, IDR, EUR), extract the code.
- Do NOT embed the currency symbol or code inside any numeric field value.
- If no currency found, set `currency` to "".
"""

_COO_RULE_DATE = """
DATE NORMALIZATION RULES (apply to EVERY date field):
- ALL dates MUST be returned in DD-MM-YYYY format (2-digit day, 2-digit month, 4-digit year).
- Convert month names or abbreviations into numeric months.
- Example conversions:
  "12-May-2021"   → "12-05-2021"
  "May 12, 2021"  → "12-05-2021"
  "2021/05/12"    → "12-05-2021"
  "12.05.2021"    → "12-05-2021"
  "2021-05-12"    → "12-05-2021"
  "12 MEI 2021"   → "12-05-2021"
- Preserve the original year exactly as printed.
- If a date cannot be parsed with certainty, return null.
"""



NUMERIC_RULE = """
NUMERIC FIELDS RULE:
- Always return numeric values as strings, never as bare numbers.
- Preserve the original formatting from the source (e.g. '1,500,000.00' not 1500000).
- Never reformat or recalculate any numeric value.
"""

_DATE_RULE = """
DATE EXTRACTION:
- Extract all dates exactly as written in the document (e.g. "15 Jan 2025", "01/15/2025").
- Do NOT reformat or normalize dates.
"""

BASE_DIRECTIVES = f"""
EXTRACTION RULES:
- Extract text VERBATIM as it appears in the document. No paraphrasing.
- Unreadable value → use empty string ""
- Field present but blank → use null
- Field/column exists but has no data in a specific row → use ""
- NEVER omit a key because its value is missing — always include the key with "" or null.
- NEVER fabricate, infer, or hallucinate any value.
- Keys: snake_case only (e.g. "Document Title" → "document_title").

OUTPUT FORMAT:
- Return a raw JSON object directly. Avoid markdown formatting, code fences (``` or ```json), or commentary.
- Do NOT wrap output in "success", "data", "result", or any envelope object.
- Do NOT add any text before or after the JSON.
{GROUNDING_RULE}
{_OUTPUT_VALIDATION}
{_CURRENCY_RULE}
{_DATE_RULE}
{NUMERIC_RULE}

"""

BASE_DIRECTIVES_COO = f"""
EXTRACTION RULES:
- Extract text VERBATIM as it appears in the document. No paraphrasing.
- Unreadable value → use empty string ""
- Field present but blank → use null
- Field/column exists but has no data in a specific row → use ""
- NEVER omit a key because its value is missing — always include the key with "" or null.
- NEVER fabricate, infer, or hallucinate any value.
- Keys: snake_case only (e.g. "Document Title" → "document_title").

OUTPUT FORMAT:
- Return a raw JSON object directly. Avoid markdown formatting, code fences (``` or ```json), or commentary.
- Do NOT wrap output in "success", "data", "result", or any envelope object.
- Do NOT add any text before or after the JSON.
{GROUNDING_RULE}
{_OUTPUT_VALIDATION}
{_CURRENCY_RULE}
{_COO_RULE_DATE}
{NUMERIC_RULE}

"""

CUSTOM_BASE_PROMPT = f"""You are a flexible document extraction assistant. \
Your primary directive is to follow the user's custom prompt below.
Only reject if the instruction has absolutely nothing to do with the provided \
document/image. When in doubt, follow the user's instruction.
OUTPUT CONVENTION:
- Follow the format the user requests (JSON, CSV, text, etc.).
- If no specific format is requested, output JSON.
- Use snake_case for any keys you invent yourself.

{BASE_DIRECTIVES}
""" 

# ---------- General and Arbitrary Field Extraction Prompts ----------
GENERAL_PROMPT = f"""You are a document OCR extraction engine. \
Your only job is to read a document image and output extracted fields as a single JSON object.
{BASE_DIRECTIVES}
STRUCTURE RULES:
- Extract every label/key and its corresponding value as a key-value pair.
- Use flat key-value pairs for simple fields.
- Use arrays of objects for tables or repeating rows within an element.
- Mirror the document's logical hierarchy — no extra nesting beyond tables.
OUTPUT: A single JSON object reflecting all fields found in this image.
Example for a simple form:
  {{"label_one": "value_one", "label_two": "value_two"}}
Example for a page with a table:
  {{"items": [{{"column_a": "val1", "column_b": "val2"}}]}}
Now extract all fields and key-value pairs from this image.
"""

def get_prompt_for_fields(fields: list) -> str:
    if not fields:
        return GENERAL_PROMPT
    field_list = "\n".join(f"  - `{f}`" for f in fields)
    return f"""You are a document OCR extraction engine. \
Your task is to extract ONLY the specific fields listed below from the document image.
{BASE_DIRECTIVES}
TARGET FIELDS TO EXTRACT:
{field_list}
FIELD MATCHING STRATEGY:
- Each field name above is in snake_case. Map it to the most likely label in the document.
  Examples: `invoice_number` → "Invoice No", "Invoice #", "No. Faktur"
            `total_amount` → "Total", "Grand Total", "Amount Due"
            `nama_lengkap` → "Nama Lengkap", "Nama", "Full Name"
- Scan the ENTIRE document systematically: headers → tables → body text → footers.
- If a field could match multiple values, prefer the most prominent or primary occurrence.
EXTRACTION RULES:
- Extract the VALUE associated with each field, not the label itself.
- If a field's value spans multiple lines, concatenate them into a single string.
- If a field maps to a repeating/table structure (e.g. `items`, `members`), \
return an array of objects with consistent keys derived from column headers.
- For all other fields, return a single scalar value (string or number).
OUTPUT RULES:
- The output must contain ONLY the fields listed above — no extra keys.
- JSON keys MUST exactly match the field names listed above (preserve snake_case).
- If a field is not found anywhere in the document, set its value to null.
- Return a single JSON object. Use flat key-value pairs for scalar fields \
and arrays for table/repeating fields.
- Every field/key in the output JSON (including nested columns inside table or list arrays) must be transformed from a simple placeholder/scalar value into a grounding object.
- The grounding object MUST contain exactly these keys:
  1. "value": The extracted text verbatim or normalized value (or null if the field is not present or blank).
  2. "bbox_2d": The 2D bounding box of the extracted value, normalized to the range [0, 999] as an array of four integers: [x_min, y_min, x_max, y_max] where x_min, y_min are top-left, and x_max, y_max are bottom-right. If the field value is null or empty, set "bbox_2d" to null.
- This wrapping rule applies to ALL keys, including top-level properties and nested properties inside array items.
- Example structure transformation for a field:
  "field_name": "string" -> "field_name": {"value": "extracted_value", "bbox_2d": [150, 220, 480, 255]}
- If a field is not found anywhere in the document, set its value to null and "bbox_2d" to null.
- Return a single JSON object.
"""

def get_prompt_for_custom(custom_prompt: str) -> str:
    return CUSTOM_BASE_PROMPT


def get_reprocess_prompt(page_no: int, doc_type: str, missing: list) -> str:
    return f"""You are reprocessing page {page_no} of a {doc_type} document.

The following fields were missing from the previous extraction:
{missing}

Re-analyze the document carefully, focusing on tables and structured rows.
IMPORTANT:
- Extract ONLY the missing fields listed above.
- Do NOT overwrite fields that were already correctly extracted.
- Every extracted field must be returned in the grounding object structure: {{"value": ..., "bbox_2d": ..., "confidence": ...}} conforming to the coordinate and formatting rules.
- Return a raw JSON object directly (avoid markdown code fences or commentary).
"""


# ---------- Shared Document Schemas ----------
KTP_SCHEMA = """{
  "provinsi": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "kabupaten_kota": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "nik": {"value": "string (16 digits)", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "nama": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "tempat_lahir": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "tanggal_lahir": {"value": "DD-MM-YYYY", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "jenis_kelamin": {"value": "LAKI-LAKI | PEREMPUAN", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "golongan_darah": {"value": "A | B | AB | O | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "alamat": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "rt_rw": {"value": "string (e.g. 003/007)", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "kelurahan_desa": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "kecamatan": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "agama": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "status_perkawinan": {"value": "BELUM KAWIN | KAWIN | CERAI HIDUP | CERAI MATI", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "pekerjaan": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "kewarganegaraan": {"value": "WNI | WNA", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "berlaku_hingga": {"value": "YYYY-MM-DD | SEUMUR HIDUP", "bbox_2d": [x_min, y_min, x_max, y_max]}
}"""

KK_SCHEMA = """{
  "nomor_kk": {"value": "string (16 digits)", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "nama_kepala_keluarga": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "alamat": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "rt": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "rw": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "desa_kelurahan": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "kecamatan": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "kabupaten_kota": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "provinsi": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "kode_pos": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "members": [
    {
      "nama_lengkap": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "nik": {"value": "string (16 digits)", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "jenis_kelamin": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "tempat_lahir": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "tanggal_lahir": {"value": "string (DD-MM-YYYY or as written)", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "agama": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "pendidikan": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "jenis_pekerjaan": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "status_perkawinan": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "status_hubungan_keluarga": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "nama_ayah": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "nama_ibu": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]}
    }
  ]
}"""

NPWP_SCHEMA = """{
  "nomor_npwp": {"value": "string (15 digits, no formatting) | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "nama": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "alamat": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "tanggal_terdaftar": {"value": "YYYY-MM-DD | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "kantor_kpp": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]}
}"""

INVOICE_SCHEMA = """{
  "invoice_number": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "invoice_date": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "due_date": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "purchase_order": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "currency": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "total_amount": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "sales_order": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "remark": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]}
}"""

INV_COO_SCHEMA = """{
  "invoice_number": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "invoice_date": {"value": "string (DD-MM-YYYY or as written) | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "form": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "table": [
    {
      "no": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "kategori_barang": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "model": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "quantity_ctns": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "quantity_pcs": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "unit_price": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "amount_usd": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "bruto": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "netto": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]}
    }
  ],
  "total_amount": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "total_weight_bruto": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "total_weight_netto": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "total_quantity_ctns": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "total_quantity_pcs": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]}
}"""

QUOTATION_SCHEMA = """{
  "quotation_number": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "quotation_date": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "sales_agent": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "no_telp": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "currency": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "purchasing_group": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "plant": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "lead_time": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "submitted_by": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "total_amount": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "material_items": [
    {
      "item_number": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "material_code": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "material_description": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "quantity": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "unit": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "unit_price": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "amount": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "UoM": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]}
    }
  ]
}"""

SIM_SCHEMA = """{
  "nomor_sim": {"value": "string (12 digits)", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "golongan_sim": {"value": "A | A Umum | B1 | B1 Umum | B2 | B2 Umum | C | C1 | D | D1", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "nama": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "tempat_lahir": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "tanggal_lahir": {"value": "DD-MM-YYYY", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "jenis_kelamin": {"value": "LAKI-LAKI | PEREMPUAN", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "golongan_darah": {"value": "A | B | AB | O | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "alamat": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "pekerjaan": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "berlaku_hingga": {"value": "DD-MM-YYYY", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "instansi_penerbit": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]}
}"""

IJAZAH_SCHEMA = """{
  "document_level": {"value": "SMA | SMK | MA | D3 | D4 | S1 | S2 | S3", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "institution_name": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "nomor_ijazah": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "nama_lengkap": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "tempat_lahir": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "tanggal_lahir": {"value": "DD/MM/YYYY", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "nisn": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "nis": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "nim": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "jurusan_sma": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "kompetensi_keahlian": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "program_studi": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "fakultas": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "tahun_lulus": {"value": "string", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "tanggal_lulus": {"value": "DD/MM/YYYY | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "tanggal_ijazah": {"value": "DD/MM/YYYY | null", "bbox_2d": [x_min, y_min, x_max, y_max]}
}"""

BL_SCHEMA = """{
  "vessel_voyage_no": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "mvs": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "document_no": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "document_date": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "ship_date": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "consignee": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "country_of_destination": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]}
}"""

PEB_SCHEMA = """{
  "nomor_pendaftaran": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "tanggal_pendaftaran": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]}
}"""

PL_SCHEMA = """{
  "no": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "date": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]}
}"""

COO_SCHEMA = """{
  "consignee": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "vessel_voyage_no": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "mvs": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "port_of_loading": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "port_of_discharge": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "invoice_no": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "invoice_date": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "document_no_bl": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "date_bl": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "document_no_peb": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "date_peb": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "document_no_pl": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "date_pl": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "ship_date": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "country_of_destination": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "form": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "table": [
    {
      "no": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "kategori_barang": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "model": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "quantity_ctns": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "quantity_pcs": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "unit_price": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "amount_usd": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "bruto": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
      "netto": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]}
    }
  ],
  "total_amount": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "total_weight_bruto": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "total_weight_netto": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "total_quantity_ctns": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]},
  "total_quantity_pcs": {"value": "string | null", "bbox_2d": [x_min, y_min, x_max, y_max]}
}"""

DOCUMENT_SCHEMAS = {
    "KTP": KTP_SCHEMA,
    "KK": KK_SCHEMA,
    "NPWP": NPWP_SCHEMA,
    "Invoice": INVOICE_SCHEMA,
    "Quotation": QUOTATION_SCHEMA,
    "SIM": SIM_SCHEMA,
    "IJAZAH": IJAZAH_SCHEMA,
    "BL": BL_SCHEMA,
    "PEB": PEB_SCHEMA,
    "PL": PL_SCHEMA,
    "COO": COO_SCHEMA,
}


_AGGREGATE_DOC_RULES = {
    "KTP": f"""
EXPECTED SCHEMA:
{KTP_SCHEMA}
""",
    "KK": f"""
EXPECTED SCHEMA:
{KK_SCHEMA}
CONFLICT RESOLUTION & DEDUPLICATION:
- Merge all family members from `anggota_keluarga` across all pages.
- Deduplicate members by `nik` (16-digit national ID) or `nama_lengkap`. If the same member appears on multiple pages, merge their fields, retaining the most complete/accurate data.
""",
    "NPWP": f"""
EXPECTED SCHEMA:
{NPWP_SCHEMA}
CONFLICT RESOLUTION:
- Prefer the NPWP number that contains exactly 15 digits (no dots/dashes).
""",
    "Invoice": f"""
EXPECTED SCHEMA:
{INVOICE_SCHEMA}
CONFLICT RESOLUTION:
- Prefer header info (`invoice_number`, `invoice_date`, `purchase_order`) from the first page's extraction.
- Prefer `total_amount` from the last page's extraction.
""",
   "Quotation": f"""
EXPECTED SCHEMA:
{QUOTATION_SCHEMA}

CONFLICT RESOLUTION & DEDUPLICATION:
- Merge all items from `material_items` across all pages.
- Deduplicate items based on `material_code` first, then `item_number`.

PRICE TIER DETECTION:
- If multiple rows share the SAME `item_number` AND same `material_description`
  but have DIFFERENT `quantity` and `unit_price` values — these are PRICE TIERS,
  not separate items.
- Price tiers must be collapsed into a single item object using a `price_tiers` array:
  {{
    "item_number": "1",
    "material_code": "SNP001",
    "material_description": "...",
    "price_tiers": [
      {{"quantity": "1,000 Pieces", "unit_price": "USD 0.2740/pc", "amount": "USD 274.00"}},
      {{"quantity": "5,000 Pieces", "unit_price": "USD 0.0659/pc", "amount": "USD 329.50"}}
    ],
    "unit": "",
    "UoM": ""
  }}
- If a page has items with `item_number` "1", "2", "3"... these are DISTINCT items, not tiers.
- If a page has items ALL with the same `item_number` "1." but different quantities — these are PRICE TIERS.

MATCHING PRICE TIERS TO ITEMS:
- Match price tiers to their correct item using `material_description` similarity.
- If page 1 has price tiers for "INNER BOX [MODEL PB:SR]" and page 2 has items
  with `material_description` containing "INNER BOX" — attach the tiers to those items.
- If no match found, keep tiers as a standalone item with `price_tiers` array.

ROW ORDER:
- Final array order: item_number ascending (1, 2, 3...).
- Price tiers within an item: quantity ascending.
""",
    "SIM": f"""
EXPECTED SCHEMA:
{SIM_SCHEMA}
""",
    "IJAZAH": f"""
EXPECTED SCHEMA:
{IJAZAH_SCHEMA}
""",
    "BL": f"""
EXPECTED SCHEMA:
{BL_SCHEMA}
""",
    "PEB": f"""
EXPECTED SCHEMA:
{PEB_SCHEMA}
""",
    "PL": f"""
EXPECTED SCHEMA:
{PL_SCHEMA}
""",
    "COO": f"""
EXPECTED SCHEMA:
{COO_SCHEMA}
CONSOLIDATION & KEY MAPPING RULES:
- Consolidate data from B/L, PEB, PL, and Invoice pages.
- Map the sub-document fields to the final COO_SCHEMA keys as follows:
  * From Bill of Lading (B/L):
    - Map B/L `document_no` to `document_no_bl`
    - Map B/L `document_date` to `date_bl`
  * From PEB (Pemberitahuan Ekspor Barang):
    - Map PEB `nomor_pendaftaran` to `document_no_peb`
    - Map PEB `tanggal_pendaftaran` to `date_peb`
  * From Packing List (PL):
    - Map PL `no` to `document_no_pl`
    - Map PL `date` to `date_pl`
  * From Invoice:
    - Map Invoice `invoice_number` to `invoice_no`
- In case of conflict, prefer `total_amount` from the PEB page (nilai_transaksi).
- In case of conflict, prefer `receiving_company` (consignee) from the B/L page.
"""
}


def get_aggregate_prompt(
    doc_type: str,
    fields: list | None = None,
    custom_prompt: str = "",
) -> str:
    """Build aggregation prompt that works with pre-computed tallies.

    Python pre-computes field tallies (counts, majority, ties) and passes
    them as structured text. The LLM only needs to confirm recommendations
    or override when semantic context suggests a better choice.
    """
    doc_rules = _AGGREGATE_DOC_RULES.get(doc_type, "")

    # Build dynamic rules for user-driven modes
    if doc_type == "Fields" and fields:
        field_list = "\n".join(f"  - `{f}`" for f in fields)
        doc_rules = (
            "EXPECTED FIELDS:\n"
            f"{field_list}\n\n"
            "FIELD RULES:\n"
            "- The final output MUST contain ONLY the fields listed above — no extra keys.\n"
            "- JSON keys MUST exactly match the field names listed above.\n"
        )

    prompt = (
        f"You are an OCR data consolidation engine for {doc_type} documents.\n"
        "You receive PRE-COMPUTED TALLIES — Python has already counted every field's "
        "occurrences across pages. You do NOT need to count.\n\n"

        "YOUR TASK:\n"
        "1. For each field, review the RECOMMENDED value.\n"
        "2. Accept the recommendation unless document-specific rules or semantic "
        "context clearly indicate a better choice.\n"
        "3. For TIED fields, use document context to pick the best value.\n"
        "4. For ARRAY fields, deduplicate using semantic similarity "
        "(e.g. same person with slightly different name spelling = same entry).\n"
        "5. For NUMERIC fields, the last-page value is already recommended — But Check First with Other Values, if you have same value multiple times choose that.\n\n"

        "OVERRIDE RULES:\n"
        "- You may override a recommendation ONLY if the recommended value is clearly "
        "wrong based on document-type conventions or field-specific rules below.\n"
        "- Never fabricate values. Only pick from values that actually appeared.\n"
        "- Each field is fully independent.\n\n"
    )

    if custom_prompt:
        prompt += (
            "ORIGINAL EXTRACTION PROMPT (use for semantic context):\n"
            f"```\n{custom_prompt}\n```\n\n"
        )

    if doc_rules:
        prompt += f"DOCUMENT TYPE SPECIFIC RULES:\n{doc_rules}\n\n"

    prompt += (
        "OUTPUT: Return ONLY the final JSON object.\n"
        "No thinking, no explanation, no markdown fences, no trailing commas.\n"
        "Start with { and end with }.\n"
    )

    return prompt




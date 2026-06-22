# ─────────────────────────────────────────────
#  OCR System Prompt Definitions (Simplified)
# ─────────────────────────────────────────────

_LAST_VALUE_FIELDS = {
    "total_amount", "grand_total", "amount_due", 
    "total_due", "total_payable", "subtotal", "sub_total",
    "tax", "vat", "discount", "shipping",
}

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
{_OUTPUT_VALIDATION}
{_CURRENCY_RULE}
{_COO_RULE_DATE}
{NUMERIC_RULE}
"""

# ---------- Simplified Schemas (without bbox_2d) ----------

KTP_SCHEMA = """{
  "provinsi": "string",
  "kabupaten_kota": "string",
  "nik": "string (16 digits)",
  "nama": "string",
  "tempat_lahir": "string",
  "tanggal_lahir": "DD-MM-YYYY",
  "jenis_kelamin": "LAKI-LAKI | PEREMPUAN",
  "golongan_darah": "A | B | AB | O | null",
  "alamat": "string",
  "rt_rw": "string (e.g. 003/007)",
  "kelurahan_desa": "string",
  "kecamatan": "string",
  "agama": "string",
  "status_perkawinan": "BELUM KAWIN | KAWIN | CERAI HIDUP | CERAI MATI",
  "pekerjaan": "string",
  "kewarganegaraan": "WNI | WNA",
  "berlaku_hingga": "YYYY-MM-DD | SEUMUR HIDUP"
}"""

KK_SCHEMA = """{
  "nomor_kk": "string (16 digits)",
  "nama_kepala_keluarga": "string",
  "alamat": "string",
  "rt": "string",
  "rw": "string",
  "desa_kelurahan": "string",
  "kecamatan": "string",
  "kabupaten_kota": "string",
  "provinsi": "string",
  "kode_pos": "string",
  "members": [
    {
      "nama_lengkap": "string",
      "nik": "string (16 digits)",
      "jenis_kelamin": "string",
      "tempat_lahir": "string",
      "tanggal_lahir": "string (DD-MM-YYYY or as written)",
      "agama": "string",
      "pendidikan": "string",
      "jenis_pekerjaan": "string",
      "status_perkawinan": "string",
      "status_hubungan_keluarga": "string",
      "nama_ayah": "string",
      "nama_ibu": "string"
    }
  ]
}"""

NPWP_SCHEMA = """{
  "nomor_npwp": "string (15 digits, no formatting) | null",
  "nama": "string",
  "alamat": "string",
  "tanggal_terdaftar": "YYYY-MM-DD | null",
  "kantor_kpp": "string"
}"""

INVOICE_SCHEMA = """{
  "invoice_number": "string",
  "invoice_date": "string",
  "due_date": "string",
  "purchase_order": "string",
  "currency": "string",
  "total_amount": "string",
  "sales_order": "string",
  "remark": "string"
}"""

INV_COO_SCHEMA = """{
  "invoice_number": "string | null",
  "invoice_date": "string (DD-MM-YYYY or as written) | null",
  "form": "string | null",
  "table": [
    {
      "no": "string | null",
      "kategori_barang": "string | null",
      "model": "string | null",
      "quantity_ctns": "string | null",
      "quantity_pcs": "string | null",
      "unit_price": "string | null",
      "amount_usd": "string | null",
      "bruto": "string | null",
      "netto": "string | null"
    }
  ],
  "total_amount": "string | null",
  "total_weight_bruto": "string | null",
  "total_weight_netto": "string | null",
  "total_quantity_ctns": "string | null",
  "total_quantity_pcs": "string | null"
}"""

QUOTATION_SCHEMA = """{
  "quotation_number": "string",
  "quotation_date": "string",
  "sales_agent": "string",
  "no_telp": "string",
  "currency": "string",
  "purchasing_group": "string",
  "plant": "string",
  "lead_time": "string",
  "submitted_by": "string",
  "total_amount": "string",
  "material_items": [
    {
      "item_number": "string",
      "material_code": "string",
      "material_description": "string",
      "quantity": "string",
      "unit": "string",
      "unit_price": "string",
      "amount": "string",
      "UoM": "string"
    }
  ]
}"""

SIM_SCHEMA = """{
  "nomor_sim": "string (12 digits)",
  "golongan_sim": "A | A Umum | B1 | B1 Umum | B2 | B2 Umum | C | C1 | D | D1",
  "nama": "string",
  "tempat_lahir": "string",
  "tanggal_lahir": "DD-MM-YYYY",
  "jenis_kelamin": "LAKI-LAKI | PEREMPUAN",
  "golongan_darah": "A | B | AB | O | null",
  "alamat": "string",
  "pekerjaan": "string | null",
  "berlaku_hingga": "DD-MM-YYYY",
  "instansi_penerbit": "string | null"
}"""

IJAZAH_SCHEMA = """{
  "document_level": "SMA | SMK | MA | D3 | D4 | S1 | S2 | S3",
  "institution_name": "string",
  "nomor_ijazah": "string | null",
  "nama_lengkap": "string",
  "tempat_lahir": "string",
  "tanggal_lahir": "DD/MM/YYYY",
  "nisn": "string | null",
  "nis": "string | null",
  "nim": "string | null",
  "jurusan_sma": "string | null",
  "kompetensi_keahlian": "string | null",
  "program_studi": "string | null",
  "fakultas": "string | null",
  "tahun_lulus": "string",
  "tanggal_lulus": "DD/MM/YYYY | null",
  "tanggal_ijazah": "DD/MM/YYYY | null"
}"""

BL_SCHEMA = """{
  "vessel_voyage_no": "string | null",
  "mvs": "string | null",
  "document_no": "string | null",
  "document_date": "string | null",
  "ship_date": "string | null",
  "consignee": "string | null",
  "country_of_destination": "string | null"
}"""

PEB_SCHEMA = """{
  "nomor_pendaftaran": "string | null",
  "tanggal_pendaftaran": "string | null"
}"""

PL_SCHEMA = """{
  "no": "string | null",
  "date": "string | null"
}"""

COO_SCHEMA = """{
  "consignee": "string | null",
  "vessel_voyage_no": "string | null",
  "mvs": "string | null",
  "port_of_loading": "string | null",
  "port_of_discharge": "string | null",
  "invoice_no": "string | null",
  "invoice_date": "string | null",
  "document_no_bl": "string | null",
  "date_bl": "string | null",
  "document_no_peb": "string | null",
  "date_peb": "string | null",
  "document_no_pl": "string | null",
  "date_pl": "string | null",
  "ship_date": "string | null",
  "country_of_destination": "string | null",
  "form": "string | null",
  "table": [
    {
      "no": "string | null",
      "kategori_barang": "string | null",
      "model": "string | null",
      "quantity_ctns": "string | null",
      "quantity_pcs": "string | null",
      "unit_price": "string | null",
      "amount_usd": "string | null",
      "bruto": "string | null",
      "netto": "string | null"
    }
  ],
  "total_amount": "string | null",
  "total_weight_bruto": "string | null",
  "total_weight_netto": "string | null",
  "total_quantity_ctns": "string | null",
  "total_quantity_pcs": "string | null"
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

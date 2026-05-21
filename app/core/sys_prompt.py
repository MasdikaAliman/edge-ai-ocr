# ─────────────────────────────────────────────
#  OCR System Prompt Definitions
# ─────────────────────────────────────────────

# ---------- Shared Rule Blocks ----------

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
{_DATE_RULE}"""

CUSTOM_BASE_PROMPT = """You are a flexible document extraction assistant. \
Your primary directive is to follow the user's custom prompt below.

Only reject if the instruction has absolutely nothing to do with the provided \
document/image. When in doubt, follow the user's instruction.

OUTPUT CONVENTION:
- Follow the format the user requests (JSON, CSV, text, etc.).
- If no specific format is requested, output JSON.
- Use snake_case for any keys you invent yourself."""


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
- Return a raw JSON object directly (avoid markdown code fences or commentary).
"""


# ---------- Shared Document Schemas ----------
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
  "invoice_number": "",
  "invoice_date": "",
  "due_date": "",
  "purchase_order": "",
  "currency": "",
  "total_amount": "",
  "sales_order": "",
  "remark": ""
}"""

QUOTATION_SCHEMA = """{
  "quotation_number": "",
  "quotation_date": "",
  "sales_agent": "",
  "no_telp": "",
  "currency": "",
  "purchasing_group": "",
  "plant": "",
  "lead_time": "",
  "submitted_by": "",
  "material_items": [
    {
      "item_number": "",
      "material_code": "",
      "material_description": "",
      "quantity": "",
      "unit": "",
      "unit_price": "",
      "amount": "",
      "UoM": ""
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

DOCUMENT_SCHEMAS = {
    "KTP": KTP_SCHEMA,
    "KK": KK_SCHEMA,
    "NPWP": NPWP_SCHEMA,
    "Invoice": INVOICE_SCHEMA,
    "Quotation": QUOTATION_SCHEMA,
    "SIM": SIM_SCHEMA,
    "IJAZAH": IJAZAH_SCHEMA,
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
- Deduplicate items based on `item_number` and `material_code`. If the same item number/code appears across multiple pages with the exact same price and qty, keep only one.
- If they have different details (like a continuation row or correction), keep both or merge them if it represents a single multi-page row.
""",
    "SIM": f"""
EXPECTED SCHEMA:
{SIM_SCHEMA}
""",
    "IJAZAH": f"""
EXPECTED SCHEMA:
{IJAZAH_SCHEMA}
"""
}


def get_aggregate_prompt(
    doc_type: str,
    fields: list | None = None,
    custom_prompt: str = "",
) -> str:
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
            "- For each field, pick the most complete value across all pages.\n"
            "- If a field is not found on any page, set its value to null.\n"
            "- The output must be a single flat JSON object.\n"
        )
    elif doc_type == "Custom" and custom_prompt:
        doc_rules = (
            "ORIGINAL USER PROMPT (for context on expected output structure):\n"
            f"```\n{custom_prompt}\n```\n\n"
            "CUSTOM AGGREGATION & RECONCILIATION RULES:\n"
              "1. FORMAT PRESERVATION: Strictly preserve the exact output structure, schema, and format (e.g., JSON, CSV, text) requested in the ORIGINAL USER PROMPT above.\n"
              "2. FIELD RESOLUTION (Conflict Handling): If the same field appears on multiple pages with DIFFERENT values, choose the single most reliable and complete value. Prioritize in this order:\n"
              "   a) Any non-empty, non-null value over `null`, `\"\"`, or `\"N/A\"`. Under no circumstances should a valid value found on one page be overridden by an empty/null value from other pages (DO NOT use majority voting/frequency count to select empty values).\n"
              "   b) The value without obvious OCR artifacts (e.g., prefer '100' over 'l00' or 'IOO'; prefer 'INV-502' over '1NV-502').\n"
              "   c) The value that is most complete and detailed (e.g., prefer 'PT Indonesia Sejahtera' over 'PT Indonesia' or 'Indonesia Sejahtera').\n"
              "   d) The value from the page where that field structurally belongs (e.g., header info on the first page, totals on the last page).\n"
              "3. ARRAY/TABLE MERGING (Fuzzy Deduplication): For list or array fields across pages, MERGE them sequentially. Overlapping pages often cause the same row to be scanned twice with slight variations. Identify these duplicates logically based on primary identifiers (like ID, Name, or Item Code) rather than looking for identical strings, and merge them into a single clean row.\n"
              "4. MISSING VALUES: If a field is missing, unreadable, or empty across ALL pages, output the standard 'empty' representation appropriate for the requested format (e.g., `null`, `\"\"`, or left blank). Do not fabricate or hallucinate data.\n"
        )

    prompt = (
        f"You are an expert data arbitration engine for {doc_type} documents.\n"
        "Multiple pages from the same document were OCR'd independently. "
        "Produce ONE final JSON object.\n"
        "RULES:\n"
        "- NO MAJORITY VOTING FOR NULLS/EMPTIES: If a field is null, empty, or absent on most pages but has a valid, non-empty value on at least one page, ALWAYS choose the non-empty value. Never overwrite a valid value with null or empty.\n"
        "- For each field, choose the single most complete, detailed, and credible value across all pages.\n"
        "- If the same field appears on multiple pages with DIFFERENT values, prefer:\n"
        "    1. The value that is non-empty and non-null.\n"
        "    2. The value that is more complete (not truncated or partial, e.g. 'INV-12345' over '12345').\n"
        "    3. The value that is clean of OCR noise (e.g. correct digit vs character substitution).\n"
        "    4. The value from the page where that field would naturally appear (e.g. totals from the last page, header info from the first page).\n"
        "- For array fields (e.g. line items, members), MERGE arrays from all pages and deduplicate identical rows.\n"
        "- If a field is empty (\"\") or null on ALL pages, output null for that field.\n"
        "- NEVER fabricate or infer values not present in any page result.\n"
    )

    if doc_rules:
        prompt += f"\nDOCUMENT TYPE SPECIFIC RULES:\n{doc_rules}\n"

    prompt += f"\n{_OUTPUT_VALIDATION}"
    return prompt



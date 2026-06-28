# ─────────────────────────────────────────────
#  OCR System Prompt Definitions (Simplified)
# ─────────────────────────────────────────────
from app.core.grounded_prompt import get_grounded_output_instruction

_GROUNDED_RULES = get_grounded_output_instruction()

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
{_GROUNDED_RULES}
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
{_GROUNDED_RULES}
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
  "golongan_darah": " - | A | B | AB | O",
  "alamat": "string",
  "rt_rw": "string (e.g. 003/007)",
  "kelurahan_desa": "string",
  "kecamatan": "string",
  "agama": "string",
  "status_perkawinan": "BELUM KAWIN | KAWIN | CERAI HIDUP | CERAI MATI",
  "pekerjaan": "string",
  "kewarganegaraan": "WNI | WNA",
  "berlaku_hingga": "SEUMUR HIDUP | DD-MM-YYYY"
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
  "nomor_npwp": "string (15 digits, with formatting: XX.XXX.XXX.X-XXX.XXX) | null",
  "nama": "string",
  "alamat": "string",
  "tanggal_terdaftar": "DD-MM-YYYY | null",
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
  "document_level": "D3 | D4 | S1 | S2 | S3",
  "institution_name": "string",
  "nomor_ijazah": "string | null",
  "nama_lengkap": "string",
  "tempat_lahir": "string",
  "tanggal_lahir": "DD/MM/YYYY",
  "nim": "string | null",
  "program_studi": "string | null",
  "fakultas": "string | null",
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

